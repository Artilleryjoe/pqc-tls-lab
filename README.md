# Hybrid Post-Quantum TLS Lab



A reproducible experiment comparing classical X25519 TLS 1.3

key establishment with hybrid X25519MLKEM768.



## Research Question



What changes operationally when a TLS 1.3 connection moves from

X25519 to X25519MLKEM768?



This lab initially examines:



- TLS handshake size

- key-share size

- connection-establishment throughput



Later tests will examine network conditions such as latency,

packet loss, and MTU constraints.



## Environment



- Windows 11

- OpenSSL 3.5.x

- Wireshark / tshark 4.6.8

- TLS 1.3

- localhost

- TCP port 8443



## Protocol Size Results



| Metric | X25519 | X25519MLKEM768 |

|---|---:|---:|

| ClientHello | 226 B | 1,402 B |

| ServerHello | 118 B | 1,206 B |

| Combined | 344 B | 2,608 B |

| Client key exchange | 32 B | 1,216 B |

| Server key exchange | 32 B | 1,120 B |



The combined ClientHello and ServerHello increased by 2,264 bytes,

approximately 658% relative to the X25519 baseline.



## Throughput Results



Five 30-second trials were performed for each group using fresh

TLS 1.3 connections.



| Group | Mean conn/s | Median conn/s | SD |

|---|---:|---:|---:|

| X25519 | 318.73 | 315.52 | 10.41 |

| X25519MLKEM768 | 290.62 | 290.71 | 6.03 |



Observed hybrid throughput delta:



- Mean: -8.82%

- Median: -7.86%



## Initial Observation



The hybrid TLS handshake substantially increased the amount of

key-establishment data transmitted, while the observed localhost

connection-establishment throughput reduction remained in the

single-digit percentage range.



This suggests that network behavior may become an important part

of evaluating hybrid post-quantum TLS deployment costs.



## Limitations



These results should not be generalized directly to production

environments.



Current limitations include:



- one host

- one CPU

- one OpenSSL implementation

- localhost networking

- five trials per configuration

- no packet loss

- no WAN latency

- no constrained MTU



## Repository Structure



- `captures/` — packet captures

- `notes/` — experiment notes

- `results/` — raw and summarized benchmark data

- `scripts/` — capture, benchmark, and analysis automation



## Next Experiment



Evaluate how the larger hybrid TLS handshake behaves under

simulated network latency, packet loss, and MTU constraints.

