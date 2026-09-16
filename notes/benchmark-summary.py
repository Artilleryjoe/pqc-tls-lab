## WSL Network-Latency Experiment

A dedicated OpenSSL 3.5.8 benchmark client was used to measure
individual TLS 1.3 handshakes.

Each configuration used:

- 5 warm-up handshakes
- 100 recorded handshakes
- fresh TLS sessions
- verified negotiated group
- separate TCP and TLS timing
- isolated Linux network namespaces

### Baseline

X25519:
- Median TLS handshake: 1.083 ms
- Mean: 1.124 ms
- p95: 1.330 ms
- 100/100 successful

X25519MLKEM768:
- Median TLS handshake: 1.200 ms
- Mean: 1.254 ms
- p95: 1.685 ms
- 100/100 successful

Hybrid median delta:
+10.81% / +0.117 ms

### ~50 ms RTT

X25519:
- Median TLS handshake: 51.473 ms
- Median total connection: 101.691 ms
- 100/100 successful

X25519MLKEM768:
- Median TLS handshake: 51.744 ms
- Median total connection: 102.019 ms
- 100/100 successful

Hybrid median TLS delta:
+0.53% / +0.271 ms

Hybrid total connection delta:
+0.32%

### Observation

The hybrid group's computational overhead was measurable under
near-zero network latency, but ordinary network latency dominated
the end-to-end connection time.

Despite a ~658% increase in combined ClientHello and ServerHello
size, X25519MLKEM768 added only ~0.3 ms to median total connection
establishment under the clean ~50 ms RTT condition tested here.

The next experiment will examine whether packet loss and
retransmission make the larger hybrid handshake more operationally
significant.
