\# Initial TLS PQC Results



Date: 2026-09-16



\## Environment

\- Windows 11

\- Wireshark 4.6.8

\- OpenSSL 3.5.x

\- TLS 1.3

\- localhost

\- TCP/8443



\## X25519



ClientHello handshake: 226 bytes

ServerHello handshake: 118 bytes



Client key exchange: 32 bytes

Server key exchange: 32 bytes



\## X25519MLKEM768



ClientHello handshake: 1402 bytes

ServerHello handshake: 1206 bytes



Client key exchange: 1216 bytes

Server key exchange: 1120 bytes



\## Initial observation



Moving from X25519 to X25519MLKEM768 substantially increased

TLS key-establishment data.



Client key exchange:

32 -> 1216 bytes



Server key exchange:

32 -> 1120 bytes



This is expected because the hybrid group carries both classical

X25519 material and ML-KEM-768 material.



Further testing needed:

\- repeated trials

\- packet segmentation

\- latency

\- CPU cost

\- behavior under realistic network conditions

