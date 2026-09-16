# TLS Benchmark Summary

Date: 2026-09-16

## Test

TLS 1.3 connection-establishment throughput comparison:

- X25519
- X25519MLKEM768
- OpenSSL 3.5.x
- Windows 11
- localhost
- five 30-second trials per group
- fresh TLS sessions
- no application payload included in the benchmark

## Results

| Group | Samples | Mean conn/s | Median conn/s | Sample SD | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| X25519 | 5 | 318.73 | 315.52 | 10.41 | 311.84 | 337.1 |
| X25519MLKEM768 | 5 | 290.62 | 290.71 | 6.03 | 281.35 | 297.84 |

Hybrid mean throughput delta: -8.82%

Hybrid median throughput delta: -7.86%

## Protocol-size results

X25519:

- ClientHello: 226 bytes
- ServerHello: 118 bytes
- Combined: 344 bytes
- Client key exchange: 32 bytes
- Server key exchange: 32 bytes

X25519MLKEM768:

- ClientHello: 1402 bytes
- ServerHello: 1206 bytes
- Combined: 2608 bytes
- Client key exchange: 1216 bytes
- Server key exchange: 1120 bytes

Combined hello-message increase:

2608 - 344 = 2264 bytes

Approximately 658% larger than the X25519 baseline.

## Initial interpretation

In this localhost test, X25519MLKEM768 substantially increased the
amount of TLS key-establishment data placed on the wire.

The observed connection-establishment throughput penalty was much
smaller than the increase in handshake-message size.

This suggests that, for this implementation and hardware, network
behavior may be at least as important as raw cryptographic computation
when evaluating hybrid post-quantum TLS deployment costs.

## Limitations

- Single Windows 11 host
- Single CPU
- Single OpenSSL implementation/build
- localhost only
- five trials per group
- no WAN latency
- no packet loss
- no constrained MTU
- throughput is not equivalent to per-handshake latency
- results should not be generalized to production environments without
  additional testing
