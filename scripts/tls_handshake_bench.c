#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <time.h>
#include <unistd.h>
#include <netdb.h>
#include <sys/socket.h>

#include <openssl/ssl.h>
#include <openssl/err.h>

/*
 * TLS Handshake Benchmark v2
 *
 * Usage:
 *
 *   tls_handshake_bench HOST PORT GROUP WARMUPS ITERATIONS CONDITION
 *
 * Example:
 *
 *   ./tls_handshake_bench \
 *       10.200.0.2 \
 *       8443 \
 *       X25519MLKEM768 \
 *       5 \
 *       100 \
 *       baseline
 *
 * Output:
 *
 *   CSV rows containing:
 *   - TCP connection time
 *   - TLS handshake time
 *   - total TCP + TLS time
 *   - negotiated TLS group
 *   - status
 *
 * Notes:
 *
 *   - TLS 1.3 only
 *   - session caching disabled
 *   - certificate verification disabled because this is a
 *     controlled lab using a self-signed certificate
 *   - warm-up handshakes are performed but not recorded
 */


static double elapsed_ms(
    const struct timespec *start,
    const struct timespec *end
)
{
    double seconds;
    double nanoseconds;

    seconds =
        (double)(end->tv_sec - start->tv_sec);

    nanoseconds =
        (double)(end->tv_nsec - start->tv_nsec);

    return
        (seconds * 1000.0) +
        (nanoseconds / 1000000.0);
}


static int connect_tcp(
    const char *host,
    const char *port
)
{
    struct addrinfo hints;
    struct addrinfo *result = NULL;
    struct addrinfo *rp;

    int sock = -1;
    int rc;

    memset(&hints, 0, sizeof(hints));

    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    rc = getaddrinfo(
        host,
        port,
        &hints,
        &result
    );

    if (rc != 0) {
        fprintf(
            stderr,
            "getaddrinfo failed for %s:%s: %s\n",
            host,
            port,
            gai_strerror(rc)
        );

        return -1;
    }

    for (
        rp = result;
        rp != NULL;
        rp = rp->ai_next
    ) {

        sock = socket(
            rp->ai_family,
            rp->ai_socktype,
            rp->ai_protocol
        );

        if (sock == -1) {
            continue;
        }

        if (
            connect(
                sock,
                rp->ai_addr,
                rp->ai_addrlen
            ) == 0
        ) {
            break;
        }

        close(sock);
        sock = -1;
    }

    freeaddrinfo(result);

    return sock;
}


static int perform_warmup(
    SSL_CTX *ctx,
    const char *host,
    const char *port
)
{
    int sock;
    SSL *ssl;
    int rc;

    sock = connect_tcp(host, port);

    if (sock < 0) {
        return 0;
    }

    ssl = SSL_new(ctx);

    if (ssl == NULL) {
        close(sock);
        return 0;
    }

    if (SSL_set_fd(ssl, sock) != 1) {
        SSL_free(ssl);
        close(sock);
        return 0;
    }

    SSL_set_tlsext_host_name(
        ssl,
        "localhost"
    );

    rc = SSL_connect(ssl);

    if (rc != 1) {
        SSL_free(ssl);
        close(sock);
        return 0;
    }

    /*
     * Shutdown occurs outside any measured region.
     */
    SSL_shutdown(ssl);

    SSL_free(ssl);
    close(sock);

    return 1;
}


static void run_measurement(
    SSL_CTX *ctx,
    const char *host,
    const char *port,
    const char *expected_group,
    const char *condition,
    int run
)
{
    struct timespec total_start;
    struct timespec connect_start;
    struct timespec connect_end;
    struct timespec tls_start;
    struct timespec tls_end;

    int sock;
    SSL *ssl;
    int rc;

    double tcp_ms;
    double tls_ms;
    double total_ms;

    const char *negotiated_group;

    /*
     * Begin total timer before TCP establishment.
     */
    clock_gettime(
        CLOCK_MONOTONIC,
        &total_start
    );

    clock_gettime(
        CLOCK_MONOTONIC,
        &connect_start
    );

    sock = connect_tcp(
        host,
        port
    );

    clock_gettime(
        CLOCK_MONOTONIC,
        &connect_end
    );

    tcp_ms = elapsed_ms(
        &connect_start,
        &connect_end
    );

    if (sock < 0) {

        printf(
            "%d,%s,,%s,%.3f,0.000,%.3f,tcp_error\n",
            run,
            expected_group,
            condition,
            tcp_ms,
            tcp_ms
        );

        fflush(stdout);

        return;
    }

    ssl = SSL_new(ctx);

    if (ssl == NULL) {

        fprintf(
            stderr,
            "Run %d: SSL_new failed.\n",
            run
        );

        printf(
            "%d,%s,,%s,%.3f,0.000,%.3f,ssl_new_error\n",
            run,
            expected_group,
            condition,
            tcp_ms,
            tcp_ms
        );

        close(sock);

        fflush(stdout);

        return;
    }

    if (SSL_set_fd(ssl, sock) != 1) {

        fprintf(
            stderr,
            "Run %d: SSL_set_fd failed.\n",
            run
        );

        printf(
            "%d,%s,,%s,%.3f,0.000,%.3f,ssl_fd_error\n",
            run,
            expected_group,
            condition,
            tcp_ms,
            tcp_ms
        );

        SSL_free(ssl);
        close(sock);

        fflush(stdout);

        return;
    }

    /*
     * SNI is not required by the current lab server,
     * but keeping it makes the client configuration
     * closer to a normal TLS client.
     */
    if (
        SSL_set_tlsext_host_name(
            ssl,
            "localhost"
        ) != 1
    ) {

        fprintf(
            stderr,
            "Run %d: failed to set SNI.\n",
            run
        );
    }

    /*
     * Measure only SSL_connect(), not TCP establishment.
     */
    clock_gettime(
        CLOCK_MONOTONIC,
        &tls_start
    );

    rc = SSL_connect(ssl);

    clock_gettime(
        CLOCK_MONOTONIC,
        &tls_end
    );

    tls_ms = elapsed_ms(
        &tls_start,
        &tls_end
    );

    total_ms = elapsed_ms(
        &total_start,
        &tls_end
    );

    if (rc != 1) {

        int ssl_error =
            SSL_get_error(
                ssl,
                rc
            );

        fprintf(
            stderr,
            "Run %d: TLS handshake failed "
            "(SSL error %d).\n",
            run,
            ssl_error
        );

        ERR_print_errors_fp(stderr);

        printf(
            "%d,%s,,%s,%.3f,%.3f,%.3f,tls_error\n",
            run,
            expected_group,
            condition,
            tcp_ms,
            tls_ms,
            total_ms
        );

        SSL_free(ssl);
        close(sock);

        fflush(stdout);

        return;
    }

    /*
     * OpenSSL 3.2+ exposes the actual group used
     * for the successful TLS key agreement.
     */
    negotiated_group =
        SSL_get0_group_name(ssl);

    if (negotiated_group == NULL) {

        printf(
            "%d,%s,unknown,%s,%.3f,%.3f,%.3f,group_unknown\n",
            run,
            expected_group,
            condition,
            tcp_ms,
            tls_ms,
            total_ms
        );

    } else if (
        strcasecmp(
            negotiated_group,
            expected_group
        ) != 0
    ) {

        printf(
            "%d,%s,%s,%s,%.3f,%.3f,%.3f,group_mismatch\n",
            run,
            expected_group,
            negotiated_group,
            condition,
            tcp_ms,
            tls_ms,
            total_ms
        );

    } else {

        printf(
            "%d,%s,%s,%s,%.3f,%.3f,%.3f,ok\n",
            run,
            expected_group,
            negotiated_group,
            condition,
            tcp_ms,
            tls_ms,
            total_ms
        );
    }

    /*
     * Shutdown is intentionally outside the
     * measured handshake interval.
     */
    SSL_shutdown(ssl);

    SSL_free(ssl);
    close(sock);

    fflush(stdout);
}


int main(
    int argc,
    char **argv
)
{
    const char *host;
    const char *port;
    const char *group;
    const char *condition;

    int warmups;
    int iterations;

    SSL_CTX *ctx;

    /*
     * Program name + six arguments = argc 7
     */
    if (argc != 7) {

        fprintf(
            stderr,
            "Usage:\n"
            "  %s HOST PORT GROUP "
            "WARMUPS ITERATIONS CONDITION\n\n",
            argv[0]
        );

        fprintf(
            stderr,
            "Example:\n"
            "  %s 10.200.0.2 8443 "
            "X25519MLKEM768 5 100 baseline\n",
            argv[0]
        );

        return EXIT_FAILURE;
    }

    host = argv[1];
    port = argv[2];
    group = argv[3];

    warmups = atoi(argv[4]);
    iterations = atoi(argv[5]);

    condition = argv[6];

    if (warmups < 0) {

        fprintf(
            stderr,
            "WARMUPS cannot be negative.\n"
        );

        return EXIT_FAILURE;
    }

    if (iterations <= 0) {

        fprintf(
            stderr,
            "ITERATIONS must be greater than zero.\n"
        );

        return EXIT_FAILURE;
    }

    /*
     * OpenSSL initializes automatically on modern
     * releases, but explicit initialization makes
     * the intent clear.
     */
    if (
        OPENSSL_init_ssl(
            OPENSSL_INIT_LOAD_SSL_STRINGS |
            OPENSSL_INIT_LOAD_CRYPTO_STRINGS,
            NULL
        ) != 1
    ) {

        fprintf(
            stderr,
            "OpenSSL initialization failed.\n"
        );

        return EXIT_FAILURE;
    }

    ctx = SSL_CTX_new(
        TLS_client_method()
    );

    if (ctx == NULL) {

        fprintf(
            stderr,
            "Unable to create SSL_CTX.\n"
        );

        ERR_print_errors_fp(stderr);

        return EXIT_FAILURE;
    }

    /*
     * Controlled lab:
     * the server certificate is intentionally
     * self-signed.
     */
    SSL_CTX_set_verify(
        ctx,
        SSL_VERIFY_NONE,
        NULL
    );

    /*
     * Prevent session caching from contaminating
     * repeated full-handshake measurements.
     */
    SSL_CTX_set_session_cache_mode(
        ctx,
        SSL_SESS_CACHE_OFF
    );

    /*
     * Force TLS 1.3 only.
     */
    if (
        SSL_CTX_set_min_proto_version(
            ctx,
            TLS1_3_VERSION
        ) != 1 ||
        SSL_CTX_set_max_proto_version(
            ctx,
            TLS1_3_VERSION
        ) != 1
    ) {

        fprintf(
            stderr,
            "Unable to force TLS 1.3.\n"
        );

        ERR_print_errors_fp(stderr);

        SSL_CTX_free(ctx);

        return EXIT_FAILURE;
    }

    /*
     * Restrict the client to exactly the group
     * specified on the command line.
     */
    if (
        SSL_CTX_set1_groups_list(
            ctx,
            group
        ) != 1
    ) {

        fprintf(
            stderr,
            "Unable to configure TLS group: %s\n",
            group
        );

        ERR_print_errors_fp(stderr);

        SSL_CTX_free(ctx);

        return EXIT_FAILURE;
    }

    /*
     * Warm-up phase.
     *
     * These handshakes are intentionally excluded
     * from the CSV results.
     */
    for (
        int i = 1;
        i <= warmups;
        i++
    ) {

        if (
            perform_warmup(
                ctx,
                host,
                port
            ) != 1
        ) {

            fprintf(
                stderr,
                "Warm-up %d/%d failed.\n",
                i,
                warmups
            );

            SSL_CTX_free(ctx);

            return EXIT_FAILURE;
        }
    }

    /*
     * CSV header.
     */
    printf(
        "run,"
        "group,"
        "negotiated_group,"
        "condition,"
        "tcp_connect_ms,"
        "tls_handshake_ms,"
        "total_ms,"
        "status\n"
    );

    fflush(stdout);

    /*
     * Recorded benchmark phase.
     */
    for (
        int run = 1;
        run <= iterations;
        run++
    ) {

        run_measurement(
            ctx,
            host,
            port,
            group,
            condition,
            run
        );
    }

    SSL_CTX_free(ctx);

    return EXIT_SUCCESS;
}
