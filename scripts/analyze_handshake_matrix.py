#!/usr/bin/env python3

import csv
import math
import statistics
from pathlib import Path


ROOT = Path("/mnt/c/Research/pqc-tls-lab")
RESULTS = ROOT / "results"

DATASETS = [
    {
        "condition": "baseline",
        "group": "X25519",
        "file": RESULTS / "wsl-baseline-x25519.csv",
    },
    {
        "condition": "baseline",
        "group": "X25519MLKEM768",
        "file": RESULTS / "wsl-baseline-x25519mlkem768.csv",
    },
    {
        "condition": "50ms",
        "group": "X25519",
        "file": RESULTS / "wsl-50ms-x25519.csv",
    },
    {
        "condition": "50ms",
        "group": "X25519MLKEM768",
        "file": RESULTS / "wsl-50ms-x25519mlkem768.csv",
    },
]

SUMMARY_FILE = RESULTS / "wsl-handshake-matrix-summary.csv"


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


def load_rows(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def analyze_dataset(dataset):
    rows = load_rows(dataset["file"])

    successful = [
        row for row in rows
        if row["status"] == "ok"
    ]

    failed = [
        row for row in rows
        if row["status"] != "ok"
    ]

    tls = [
        float(row["tls_handshake_ms"])
        for row in successful
    ]

    tcp = [
        float(row["tcp_connect_ms"])
        for row in successful
    ]

    total = [
        float(row["total_ms"])
        for row in successful
    ]

    negotiated = sorted({
        row["negotiated_group"]
        for row in successful
    })

    if not tls:
        raise RuntimeError(
            f"No successful samples in {dataset['file']}"
        )

    return {
        "condition": dataset["condition"],
        "group": dataset["group"],
        "samples": len(rows),
        "successes": len(successful),
        "failures": len(failed),
        "negotiated_groups": ",".join(negotiated),

        "tls_mean_ms": statistics.mean(tls),
        "tls_median_ms": statistics.median(tls),
        "tls_sd_ms": (
            statistics.stdev(tls)
            if len(tls) > 1
            else 0.0
        ),
        "tls_min_ms": min(tls),
        "tls_max_ms": max(tls),
        "tls_p95_ms": percentile(tls, 95),
        "tls_p99_ms": percentile(tls, 99),

        "tcp_mean_ms": statistics.mean(tcp),
        "tcp_median_ms": statistics.median(tcp),

        "total_mean_ms": statistics.mean(total),
        "total_median_ms": statistics.median(total),
        "total_p95_ms": percentile(total, 95),
    }


def pct_delta(new, baseline):
    return ((new / baseline) - 1.0) * 100.0


def find_result(results, condition, group):
    return next(
        r for r in results
        if r["condition"] == condition
        and r["group"] == group
    )


def print_dataset(result):
    print(
        f"{result['condition']:8} "
        f"{result['group']}"
    )

    print(
        f"  samples:        {result['samples']}"
    )
    print(
        f"  successes:      {result['successes']}"
    )
    print(
        f"  failures:       {result['failures']}"
    )
    print(
        f"  negotiated:     "
        f"{result['negotiated_groups']}"
    )

    print(
        f"  TLS mean:       "
        f"{result['tls_mean_ms']:.3f} ms"
    )
    print(
        f"  TLS median:     "
        f"{result['tls_median_ms']:.3f} ms"
    )
    print(
        f"  TLS SD:         "
        f"{result['tls_sd_ms']:.3f} ms"
    )
    print(
        f"  TLS p95:        "
        f"{result['tls_p95_ms']:.3f} ms"
    )
    print(
        f"  TLS p99:        "
        f"{result['tls_p99_ms']:.3f} ms"
    )

    print(
        f"  TCP median:     "
        f"{result['tcp_median_ms']:.3f} ms"
    )
    print(
        f"  Total median:   "
        f"{result['total_median_ms']:.3f} ms"
    )
    print(
        f"  Total p95:      "
        f"{result['total_p95_ms']:.3f} ms"
    )

    print()


def main():
    results = []

    for dataset in DATASETS:
        if not dataset["file"].exists():
            raise FileNotFoundError(
                dataset["file"]
            )

        results.append(
            analyze_dataset(dataset)
        )

    print()
    print("=== TLS Handshake Matrix ===")
    print()

    for result in results:
        print_dataset(result)

    baseline_classical = find_result(
        results,
        "baseline",
        "X25519",
    )

    baseline_hybrid = find_result(
        results,
        "baseline",
        "X25519MLKEM768",
    )

    latency_classical = find_result(
        results,
        "50ms",
        "X25519",
    )

    latency_hybrid = find_result(
        results,
        "50ms",
        "X25519MLKEM768",
    )

    baseline_tls_delta = pct_delta(
        baseline_hybrid["tls_median_ms"],
        baseline_classical["tls_median_ms"],
    )

    latency_tls_delta = pct_delta(
        latency_hybrid["tls_median_ms"],
        latency_classical["tls_median_ms"],
    )

    baseline_total_delta = pct_delta(
        baseline_hybrid["total_median_ms"],
        baseline_classical["total_median_ms"],
    )

    latency_total_delta = pct_delta(
        latency_hybrid["total_median_ms"],
        latency_classical["total_median_ms"],
    )

    baseline_abs_tls = (
        baseline_hybrid["tls_median_ms"]
        - baseline_classical["tls_median_ms"]
    )

    latency_abs_tls = (
        latency_hybrid["tls_median_ms"]
        - latency_classical["tls_median_ms"]
    )

    print("=== Hybrid vs Classical ===")
    print()

    print(
        "Baseline TLS median delta:   "
        f"{baseline_tls_delta:+.2f}% "
        f"({baseline_abs_tls:+.3f} ms)"
    )

    print(
        "50ms TLS median delta:       "
        f"{latency_tls_delta:+.2f}% "
        f"({latency_abs_tls:+.3f} ms)"
    )

    print()

    print(
        "Baseline total median delta: "
        f"{baseline_total_delta:+.2f}%"
    )

    print(
        "50ms total median delta:     "
        f"{latency_total_delta:+.2f}%"
    )

    print()

    print("=== Effect of Network Delay ===")
    print()

    print(
        "X25519 total median:"
    )
    print(
        f"  baseline: "
        f"{baseline_classical['total_median_ms']:.3f} ms"
    )
    print(
        f"  50ms:     "
        f"{latency_classical['total_median_ms']:.3f} ms"
    )

    print()

    print(
        "X25519MLKEM768 total median:"
    )
    print(
        f"  baseline: "
        f"{baseline_hybrid['total_median_ms']:.3f} ms"
    )
    print(
        f"  50ms:     "
        f"{latency_hybrid['total_median_ms']:.3f} ms"
    )

    fields = [
        "condition",
        "group",
        "samples",
        "successes",
        "failures",
        "negotiated_groups",
        "tls_mean_ms",
        "tls_median_ms",
        "tls_sd_ms",
        "tls_min_ms",
        "tls_max_ms",
        "tls_p95_ms",
        "tls_p99_ms",
        "tcp_mean_ms",
        "tcp_median_ms",
        "total_mean_ms",
        "total_median_ms",
        "total_p95_ms",
    ]

    with SUMMARY_FILE.open(
        "w",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for result in results:
            output = result.copy()

            for key, value in output.items():
                if isinstance(value, float):
                    output[key] = round(value, 4)

            writer.writerow(output)

    print()
    print(
        f"Saved summary: {SUMMARY_FILE}"
    )


if __name__ == "__main__":
    main()
