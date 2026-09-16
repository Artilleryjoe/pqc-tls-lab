# Hybrid Post-Quantum TLS Lab

A reproducible experiment comparing classical X25519 TLS 1.3 key establishment with hybrid X25519MLKEM768.

## Research Question

What changes operationally when a TLS 1.3 connection moves from X25519 to X25519MLKEM768?

This lab examines:

- TLS handshake size
- key-share size
- connection-establishment throughput
- per-handshake latency
- simulated WAN latency
- packet loss behavior

## Environment

- Windows 11
- WSL2 / Ubuntu
- OpenSSL 3.5.x
- Wireshark / tshark 4.6.8
- TLS 1.3
- Linux network namespaces
- `tc netem`
- TCP port 8443

## Protocol Size Results

| Metric | X25519 | X25519MLKEM768 |
|---|---:|---:|
| ClientHello | 226 B | 1,402 B |
| ServerHello | 118 B | 1,206 B |
| Combined | 344 B | 2,608 B |
| Client key exchange | 32 B | 1,216 B |
| Server key exchange | 32 B | 1,120 B |

The combined ClientHello and ServerHello increased by 2,264 bytes, approximately 658% relative to the X25519 baseline.

## Initial Throughput Results

Five 30-second trials were performed for each group using fresh TLS 1.3 connections.

| Group | Mean conn/s | Median conn/s | SD |
|---|---:|---:|---:|
| X25519 | 318.73 | 315.52 | 10.41 |
| X25519MLKEM768 | 290.62 | 290.71 | 6.03 |

Observed hybrid throughput delta:

- Mean: -8.82%
- Median: -7.86%

## Per-Handshake Latency

A custom OpenSSL 3.5.8 benchmark client measured individual TLS handshakes after five warm-up connections.

| Condition | X25519 Median TLS | X25519MLKEM768 Median TLS | Hybrid Delta |
|---|---:|---:|---:|
| Baseline | 1.083 ms | 1.200 ms | +10.81% |
| ~50 ms RTT | 51.473 ms | 51.744 ms | +0.53% |
| ~50 ms RTT + 1% loss | 51.445 ms | 51.669 ms | +0.44% |

Under near-zero latency, the hybrid group showed a measurable computational cost of about 0.117 ms at the median.

Once ~50 ms RTT was introduced, network latency dominated the connection and the median hybrid difference fell to a fraction of a millisecond.

## Packet-Loss Validation

An initial 100-handshake loss test suggested that the larger hybrid handshake might suffer worse tail latency under packet loss.

Rather than treating that first result as conclusive, the experiment was expanded to five independent 100-handshake batches per group under approximately 50 ms RTT and 1% stochastic packet loss.

The validation set contained:

- 500 X25519 handshakes
- 500 X25519MLKEM768 handshakes
- 1,000 total recorded handshakes
- 0 handshake failures

### Pooled Results

| Metric | X25519 | X25519MLKEM768 |
|---|---:|---:|
| Median TLS | 51.469 ms | 51.660 ms |
| Mean TLS | 57.231 ms | 57.198 ms |
| p95 | 52.811 ms | 52.752 ms |
| p99 | 310.367 ms | 210.596 ms |
| Maximum | 334.011 ms | 311.149 ms |
| TLS > 100 ms | 2.00% | 2.80% |
| TLS > 200 ms | 2.00% | 2.80% |

The larger hybrid handshake did not produce a consistent hybrid-specific tail-latency penalty across repeated loss trials. Tail behavior varied between batches, indicating that stochastic packet loss dominated the isolated outliers observed in the initial test.

## Key Observation

X25519MLKEM768 substantially increased the amount of TLS key-establishment data transmitted, but the performance effect was not proportional to the increase in handshake size.

In this controlled environment:

- Combined ClientHello and ServerHello size increased by approximately 658%.
- Median TLS latency increased by about 0.117 ms on the near-zero-latency path.
- At approximately 50 ms RTT, the median hybrid penalty fell below 1%.
- Under 1% random packet loss, both groups developed retransmission-driven outliers, but repeated testing did not establish a consistently worse hybrid tail.

The results suggest that evaluating post-quantum TLS deployment cost requires separating cryptographic computation, wire size, and network behavior rather than treating "PQC overhead" as a single metric.

## Limitations

These results should not be generalized directly to production environments.

Current limitations include:

- one host
- one CPU
- one OpenSSL implementation
- one operating-system environment
- simulated network conditions
- no constrained-MTU testing yet
- no mobile or embedded devices
- no production TLS termination infrastructure
- no alternative PQC implementations

## Repository Structure

- `captures/` — packet captures
- `notes/` — experiment notes
- `results/` — raw and summarized benchmark data
- `scripts/` — capture, benchmark, network, and analysis automation

## Next Experiment

Evaluate how the larger hybrid TLS handshake behaves under constrained MTU and fragmentation conditions.
