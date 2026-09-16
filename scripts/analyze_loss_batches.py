#!/usr/bin/env python3

import csv
import math
import re
import statistics
from pathlib import Path


ROOT = Path("/mnt/c/Research/pqc-tls-lab")
DATA_DIR = ROOT / "results" / "loss-batches"

THRESHOLDS_MS = [75, 100, 150, 200, 250]

GROUPS = [
    "X25519",
    "X25519MLKEM768",
]

SHORT_NAMES = {
    "X25519": "x25519",
    "X25519MLKEM768": "x25519mlkem768",
}

# Actual execution order from run_loss_batches.sh.
RUN_ORDER = [
    (1, "X25519"),
    (1, "X25519MLKEM768"),
    (2, "X25519MLKEM768"),
    (2, "X25519"),
    (3, "X25519"),
    (3, "X25519MLKEM768"),
    (4, "X25519MLKEM768"),
    (4, "X25519"),
    (5, "X25519"),
    (5, "X25519MLKEM768"),
]


def percentile(values, p):
    values = sorted(values)

    if not values:
        raise ValueError("Empty dataset.")

    if len(values) == 1:
        return values[0]

    index = (len(values) - 1) * (p / 100.0)

    lower = math.floor(index)
    upper = math.ceil(index)

    if lower == upper:
        return values[lower]

    fraction = index - lower

    return (
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )


def load_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_values(values):
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "sd": (
            statistics.stdev(values)
            if len(values) > 1
            else 0.0
        ),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "min": min(values),
        "max": max(values),
    }


def analyze_file(batch, group):
    short = SHORT_NAMES[group]

    path = DATA_DIR / f"batch-{batch}-{short}.csv"

    if not path.exists():
        raise FileNotFoundError(path)

    rows = load_csv(path)

    successes = [
        row for row in rows
        if row["status"] == "ok"
    ]

    failures = [
        row for row in rows
        if row["status"] != "ok"
    ]

    tls = [
        float(row["tls_handshake_ms"])
        for row in successes
    ]

    tcp = [
        float(row["tcp_connect_ms"])
        for row in successes
    ]

    total = [
        float(row["total_ms"])
        for row in successes
    ]

    thresholds = {}

    for threshold in THRESHOLDS_MS:
        count = sum(
            1 for value in tls
            if value > threshold
        )

        thresholds[threshold] = {
            "count": count,
            "pct": (
                count / len(tls) * 100.0
                if tls
                else 0.0
            ),
        }

    return {
        "batch": batch,
        "group": group,
        "rows": len(rows),
        "successes": len(successes),
        "failures": len(failures),
        "tls_values": tls,
        "tcp_values": tcp,
        "total_values": total,
        "tls": summarize_values(tls),
        "tcp": summarize_values(tcp),
        "total": summarize_values(total),
        "thresholds": thresholds,
    }


def parse_netem(path):
    """
    Parse a tc -s qdisc snapshot.

    Example:
      Sent 100257 bytes 1041 pkt
      (dropped 10, overlimits 0 requeues 0)
    """

    text = path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    match = re.search(
        r"Sent\s+\d+\s+bytes\s+(\d+)\s+pkt"
        r"\s+\(dropped\s+(\d+),",
        text,
        re.MULTILINE
    )

    if not match:
        raise RuntimeError(
            f"Could not parse netem stats: {path}"
        )

    sent = int(match.group(1))
    dropped = int(match.group(2))

    return {
        "sent": sent,
        "dropped": dropped,
    }


def load_netem_snapshots():
    """
    tc qdisc replace preserved cumulative counters in this run.

    Recover per-batch values by differencing snapshots in actual
    execution order.
    """

    previous = {
        "client": {
            "sent": 0,
            "dropped": 0,
        },
        "server": {
            "sent": 0,
            "dropped": 0,
        },
    }

    recovered = {}

    for batch, group in RUN_ORDER:
        short = SHORT_NAMES[group]

        client_path = (
            DATA_DIR
            / f"batch-{batch}-{short}-netem-client.txt"
        )

        server_path = (
            DATA_DIR
            / f"batch-{batch}-{short}-netem-server.txt"
        )

        current_client = parse_netem(client_path)
        current_server = parse_netem(server_path)

        client_delta = {
            "sent":
                current_client["sent"]
                - previous["client"]["sent"],

            "dropped":
                current_client["dropped"]
                - previous["client"]["dropped"],
        }

        server_delta = {
            "sent":
                current_server["sent"]
                - previous["server"]["sent"],

            "dropped":
                current_server["dropped"]
                - previous["server"]["dropped"],
        }

        attempted = (
            client_delta["sent"]
            + client_delta["dropped"]
            + server_delta["sent"]
            + server_delta["dropped"]
        )

        dropped = (
            client_delta["dropped"]
            + server_delta["dropped"]
        )

        drop_pct = (
            dropped / attempted * 100.0
            if attempted > 0
            else 0.0
        )

        recovered[(batch, group)] = {
            "client_sent":
                client_delta["sent"],

            "client_dropped":
                client_delta["dropped"],

            "server_sent":
                server_delta["sent"],

            "server_dropped":
                server_delta["dropped"],

            "combined_dropped":
                dropped,

            "combined_attempted":
                attempted,

            "combined_drop_pct":
                drop_pct,
        }

        previous["client"] = current_client
        previous["server"] = current_server

    return recovered


def pct_delta(new, old):
    return ((new / old) - 1.0) * 100.0


def print_batch(result, netem):
    tls = result["tls"]

    print(
        f"Batch {result['batch']} "
        f"{result['group']}"
    )

    print(
        f"  successes: "
        f"{result['successes']}/"
        f"{result['rows']}"
    )

    print(
        f"  TLS median: "
        f"{tls['median']:.3f} ms"
    )

    print(
        f"  TLS mean:   "
        f"{tls['mean']:.3f} ms"
    )

    print(
        f"  TLS SD:     "
        f"{tls['sd']:.3f} ms"
    )

    print(
        f"  TLS p95:    "
        f"{tls['p95']:.3f} ms"
    )

    print(
        f"  TLS p99:    "
        f"{tls['p99']:.3f} ms"
    )

    print(
        f"  TLS max:    "
        f"{tls['max']:.3f} ms"
    )

    for threshold in THRESHOLDS_MS:
        data = result["thresholds"][threshold]

        print(
            f"  > {threshold:3} ms: "
            f"{data['count']:3} "
            f"({data['pct']:.1f}%)"
        )

    print(
        "  recovered drop rate: "
        f"{netem['combined_drop_pct']:.2f}% "
        f"({netem['combined_dropped']} drops)"
    )

    print()


def pooled_summary(results, group):
    group_results = [
        result
        for result in results
        if result["group"] == group
    ]

    tls = []

    for result in group_results:
        tls.extend(
            result["tls_values"]
        )

    stats = summarize_values(tls)

    thresholds = {}

    for threshold in THRESHOLDS_MS:
        count = sum(
            1 for value in tls
            if value > threshold
        )

        thresholds[threshold] = {
            "count": count,
            "pct": count / len(tls) * 100.0,
        }

    return {
        "group": group,
        "samples": len(tls),
        "stats": stats,
        "thresholds": thresholds,
    }


def main():
    results = []

    for batch in range(1, 6):
        for group in GROUPS:
            results.append(
                analyze_file(
                    batch,
                    group
                )
            )

    netem = load_netem_snapshots()

    print()
    print(
        "=== Independent Loss Batches ==="
    )
    print()

    for batch, group in RUN_ORDER:
        result = next(
            r for r in results
            if (
                r["batch"] == batch
                and r["group"] == group
            )
        )

        print_batch(
            result,
            netem[(batch, group)]
        )

    print(
        "=== Paired Batch Comparison ==="
    )
    print()

    for batch in range(1, 6):

        classical = next(
            r for r in results
            if (
                r["batch"] == batch
                and r["group"] == "X25519"
            )
        )

        hybrid = next(
            r for r in results
            if (
                r["batch"] == batch
                and
                r["group"] == "X25519MLKEM768"
            )
        )

        median_delta_ms = (
            hybrid["tls"]["median"]
            - classical["tls"]["median"]
        )

        median_delta_pct = pct_delta(
            hybrid["tls"]["median"],
            classical["tls"]["median"],
        )

        p99_delta_ms = (
            hybrid["tls"]["p99"]
            - classical["tls"]["p99"]
        )

        print(
            f"Batch {batch}:"
        )

        print(
            "  median hybrid delta: "
            f"{median_delta_pct:+.2f}% "
            f"({median_delta_ms:+.3f} ms)"
        )

        print(
            "  p99 absolute delta:  "
            f"{p99_delta_ms:+.3f} ms"
        )

        print()

    classical_pool = pooled_summary(
        results,
        "X25519"
    )

    hybrid_pool = pooled_summary(
        results,
        "X25519MLKEM768"
    )

    print(
        "=== Pooled 500-Handshake Results ==="
    )
    print()

    for pooled in [
        classical_pool,
        hybrid_pool,
    ]:

        stats = pooled["stats"]

        print(
            pooled["group"]
        )

        print(
            f"  samples: {pooled['samples']}"
        )

        print(
            f"  mean:    {stats['mean']:.3f} ms"
        )

        print(
            f"  median:  {stats['median']:.3f} ms"
        )

        print(
            f"  SD:      {stats['sd']:.3f} ms"
        )

        print(
            f"  p95:     {stats['p95']:.3f} ms"
        )

        print(
            f"  p99:     {stats['p99']:.3f} ms"
        )

        print(
            f"  max:     {stats['max']:.3f} ms"
        )

        for threshold in THRESHOLDS_MS:
            data = pooled["thresholds"][threshold]

            print(
                f"  > {threshold:3} ms: "
                f"{data['count']:3} "
                f"({data['pct']:.2f}%)"
            )

        print()

    print(
        "=== Pooled Hybrid Delta ==="
    )
    print()

    median_delta = (
        hybrid_pool["stats"]["median"]
        - classical_pool["stats"]["median"]
    )

    median_pct = pct_delta(
        hybrid_pool["stats"]["median"],
        classical_pool["stats"]["median"],
    )

    mean_delta = (
        hybrid_pool["stats"]["mean"]
        - classical_pool["stats"]["mean"]
    )

    mean_pct = pct_delta(
        hybrid_pool["stats"]["mean"],
        classical_pool["stats"]["mean"],
    )

    print(
        "Median TLS delta: "
        f"{median_pct:+.2f}% "
        f"({median_delta:+.3f} ms)"
    )

    print(
        "Mean TLS delta:   "
        f"{mean_pct:+.2f}% "
        f"({mean_delta:+.3f} ms)"
    )

    print()

    print(
        "Threshold comparison:"
    )

    for threshold in THRESHOLDS_MS:

        classical = (
            classical_pool["thresholds"][threshold]
        )

        hybrid = (
            hybrid_pool["thresholds"][threshold]
        )

        print(
            f"  > {threshold:3} ms: "
            f"X25519 "
            f"{classical['count']}/500 "
            f"({classical['pct']:.2f}%) | "
            f"Hybrid "
            f"{hybrid['count']}/500 "
            f"({hybrid['pct']:.2f}%)"
        )


if __name__ == "__main__":
    main()
