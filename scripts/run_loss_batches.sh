#!/usr/bin/env bash

set -euo pipefail

ROOT="/mnt/c/Research/pqc-tls-lab"
BENCH="$ROOT/scripts/tls_handshake_bench"

OPENSSL35="/home/artilleryjoe/bin/openssl35"

CERT="$ROOT/certs/server.crt"
KEY="$ROOT/certs/server.key"

OUT="$ROOT/results/loss-batches"

PORT="8443"
HOST="10.200.0.2"

WARMUPS=5
RUNS=100

mkdir -p "$OUT"


cleanup() {
    echo
    echo "Removing netem impairment..."

    sudo ip netns exec pqc-client \
        tc qdisc del dev veth-client root \
        2>/dev/null || true

    sudo ip netns exec pqc-server \
        tc qdisc del dev veth-server root \
        2>/dev/null || true
}

trap cleanup EXIT


apply_netem() {

    sudo ip netns exec pqc-client \
        tc qdisc replace dev veth-client root \
        netem delay 25ms loss 1%

    sudo ip netns exec pqc-server \
        tc qdisc replace dev veth-server root \
        netem delay 25ms loss 1%
}


run_batch() {

    GROUP="$1"
    BATCH="$2"

    if [[ "$GROUP" == "X25519" ]]; then
        SHORT="x25519"
    else
        SHORT="x25519mlkem768"
    fi

    PREFIX="$OUT/batch-${BATCH}-${SHORT}"

    CSV="${PREFIX}.csv"
    SERVER_LOG="${PREFIX}-server.log"

    CLIENT_NETEM="${PREFIX}-netem-client.txt"
    SERVER_NETEM="${PREFIX}-netem-server.txt"

    echo
    echo "=========================================="
    echo "Batch $BATCH - $GROUP"
    echo "=========================================="

    #
    # Reset netem before every individual batch.
    # This also resets qdisc statistics.
    #
    apply_netem

    #
    # Five warmups + 100 recorded connections.
    #
    ACCEPTS=$((WARMUPS + RUNS))

    sudo ip netns exec pqc-server \
        "$OPENSSL35" s_server \
        -accept "$PORT" \
        -cert "$CERT" \
        -key "$KEY" \
        -tls1_3 \
        -groups "$GROUP" \
        -quiet \
        -naccept "$ACCEPTS" \
        > "$SERVER_LOG" 2>&1 &

    SERVER_PID=$!

    sleep 0.5

    sudo ip netns exec pqc-client \
        "$BENCH" \
        "$HOST" \
        "$PORT" \
        "$GROUP" \
        "$WARMUPS" \
        "$RUNS" \
        "50ms-1pct-batch${BATCH}" \
        > "$CSV"

    #
    # The server should terminate itself after
    # accepting the expected number of connections.
    #
    wait "$SERVER_PID" || true

    #
    # Preserve actual netem counters for this batch.
    #
    sudo ip netns exec pqc-client \
        tc -s qdisc show dev veth-client \
        > "$CLIENT_NETEM"

    sudo ip netns exec pqc-server \
        tc -s qdisc show dev veth-server \
        > "$SERVER_NETEM"

    LINES=$(wc -l < "$CSV")

    FAILURES=$(
        awk -F, '
            NR > 1 && $8 != "ok" {
                failures++
            }
            END {
                print failures + 0
            }
        ' "$CSV"
    )

    echo "CSV rows: $LINES"
    echo "Failed recorded handshakes: $FAILURES"

    echo
    echo "Client netem:"
    grep -E "Sent|dropped" "$CLIENT_NETEM" || true

    echo "Server netem:"
    grep -E "Sent|dropped" "$SERVER_NETEM" || true
}


echo
echo "PQC TLS loss-validation experiment"
echo "5 batches per group"
echo "100 recorded handshakes per batch"
echo "~50 ms RTT + 1% loss"
echo


#
# Alternate run order to reduce systematic
# warm-up / drift / scheduling bias.
#

run_batch "X25519" 1
run_batch "X25519MLKEM768" 1

run_batch "X25519MLKEM768" 2
run_batch "X25519" 2

run_batch "X25519" 3
run_batch "X25519MLKEM768" 3

run_batch "X25519MLKEM768" 4
run_batch "X25519" 4

run_batch "X25519" 5
run_batch "X25519MLKEM768" 5


echo
echo "=========================================="
echo "Experiment complete"
echo "=========================================="

echo
echo "Datasets:"
ls -1 "$OUT"/*.csv

echo
echo "Total recorded rows:"

awk '
    FNR > 1 {
        rows++
    }

    END {
        print rows
    }
' "$OUT"/*.csv
