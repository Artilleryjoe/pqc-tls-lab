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
    {
        "condition": "50ms-1pct",
        "group": "X25519",
        "file": RESULTS / "wsl-50ms-1pct-x25519.csv",
    },
    {
        "condition": "50ms-1pct",
        "group": "X25519MLKEM768",
        "file": RESULTS / "wsl-50ms-1pct-x25519mlkem768.csv",
    },
]

SUMMARY_FILE = (
    RESULTS / "wsl-handshake-matrix-summary.csv"
)


def percentile(values, p):
    """
    Calculate a linear-interpolated percentile.
    """

    values = sorted(values)

    if not values:
        raise ValueError(
            "Cannot calculate percentile of empty dataset."
        )

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
        + (
            values[upper]
            - values[lower]
        ) * fraction
    )


def pct_delta(new, baseline):
    """
    Percentage change from baseline to new.
    """

    return (
        (new / baseline) - 1.0
    ) * 100.0


def load_rows(path):
    """
    Load one benchmark CSV.
    """

    with path.open(
        newline="",
        encoding="utf-8"
    ) as f:

        return list(
            csv.DictReader(f)
        )


def analyze_dataset(dataset):
    """
    Calculate summary statistics for one
    condition/group combination.
    """

    rows = load_rows(
        dataset["file"]
    )

    successful = [
        row
        for row in rows
        if row["status"] == "ok"
    ]

    failed = [
        row
        for row in rows
        if row["status"] != "ok"
    ]

    if not successful:
        raise RuntimeError(
            f"No successful samples in "
            f"{dataset['file']}"
        )

    tls_values = [
        float(
            row["tls_handshake_ms"]
        )
        for row in successful
    ]

    tcp_values = [
        float(
            row["tcp_connect_ms"]
        )
        for row in successful
    ]

    total_values = [
        float(
            row["total_ms"]
        )
        for row in successful
    ]

    negotiated_groups = sorted({
        row["negotiated_group"]
        for row in successful
    })

    return {
        "condition":
            dataset["condition"],

        "group":
            dataset["group"],

        "samples":
            len(rows),

        "successes":
            len(successful),

        "failures":
            len(failed),

        "negotiated_groups":
            ",".join(
                negotiated_groups
            ),

        "tls_mean_ms":
            statistics.mean(
                tls_values
            ),

        "tls_median_ms":
            statistics.median(
                tls_values
            ),

        "tls_sd_ms":
            (
                statistics.stdev(
                    tls_values
                )
                if len(tls_values) > 1
                else 0.0
            ),

        "tls_min_ms":
            min(
                tls_values
            ),

        "tls_max_ms":
            max(
                tls_values
            ),

        "tls_p95_ms":
            percentile(
                tls_values,
                95
            ),

        "tls_p99_ms":
            percentile(
                tls_values,
                99
            ),

        "tcp_mean_ms":
            statistics.mean(
                tcp_values
            ),

        "tcp_median_ms":
            statistics.median(
                tcp_values
            ),

        "total_mean_ms":
            statistics.mean(
                total_values
            ),

        "total_median_ms":
            statistics.median(
                total_values
            ),

        "total_p95_ms":
            percentile(
                total_values,
                95
            ),

        "total_p99_ms":
            percentile(
                total_values,
                99
            ),

        "total_max_ms":
            max(
                total_values
            ),
    }


def find_result(
    results,
    condition,
    group
):
    """
    Find one summary result.
    """

    return next(
        result
        for result in results
        if (
            result["condition"]
            == condition
            and
            result["group"]
            == group
        )
    )


def print_dataset(result):
    """
    Print one dataset summary.
    """

    print(
        f"{result['condition']:10} "
        f"{result['group']}"
    )

    print(
        f"  samples:        "
        f"{result['samples']}"
    )

    print(
        f"  successes:      "
        f"{result['successes']}"
    )

    print(
        f"  failures:       "
        f"{result['failures']}"
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
        f"  TLS range:      "
        f"{result['tls_min_ms']:.3f}"
        f" - "
        f"{result['tls_max_ms']:.3f} ms"
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

    print(
        f"  Total p99:      "
        f"{result['total_p99_ms']:.3f} ms"
    )

    print(
        f"  Total max:      "
        f"{result['total_max_ms']:.3f} ms"
    )

    print()


def print_comparison(
    label,
    classical,
    hybrid
):
    """
    Compare X25519MLKEM768 against X25519
    for one network condition.
    """

    tls_median_abs = (
        hybrid["tls_median_ms"]
        - classical["tls_median_ms"]
    )

    tls_median_pct = pct_delta(
        hybrid["tls_median_ms"],
        classical["tls_median_ms"],
    )

    tls_mean_abs = (
        hybrid["tls_mean_ms"]
        - classical["tls_mean_ms"]
    )

    tls_mean_pct = pct_delta(
        hybrid["tls_mean_ms"],
        classical["tls_mean_ms"],
    )

    total_median_abs = (
        hybrid["total_median_ms"]
        - classical["total_median_ms"]
    )

    total_median_pct = pct_delta(
        hybrid["total_median_ms"],
        classical["total_median_ms"],
    )

    print(label)

    print(
        "  TLS median delta:   "
        f"{tls_median_pct:+.2f}% "
        f"({tls_median_abs:+.3f} ms)"
    )

    print(
        "  TLS mean delta:     "
        f"{tls_mean_pct:+.2f}% "
        f"({tls_mean_abs:+.3f} ms)"
    )

    print(
        "  Total median delta: "
        f"{total_median_pct:+.2f}% "
        f"({total_median_abs:+.3f} ms)"
    )

    print()


def main():
    results = []

    for dataset in DATASETS:

        if not dataset["file"].exists():
            raise FileNotFoundError(
                f"Missing dataset: "
                f"{dataset['file']}"
            )

        results.append(
            analyze_dataset(
                dataset
            )
        )

    print()
    print(
        "=== TLS Handshake Matrix ==="
    )
    print()

    for result in results:
        print_dataset(
            result
        )

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

    loss_classical = find_result(
        results,
        "50ms-1pct",
        "X25519",
    )

    loss_hybrid = find_result(
        results,
        "50ms-1pct",
        "X25519MLKEM768",
    )

    print(
        "=== Hybrid vs Classical ==="
    )
    print()

    print_comparison(
        "Baseline",
        baseline_classical,
        baseline_hybrid,
    )

    print_comparison(
        "~50 ms RTT",
        latency_classical,
        latency_hybrid,
    )

    print_comparison(
        "~50 ms RTT + 1% loss",
        loss_classical,
        loss_hybrid,
    )

    print(
        "=== Effect of Network Conditions ==="
    )
    print()

    print("X25519")

    print(
        f"  baseline total median: "
        f"{baseline_classical['total_median_ms']:.3f} ms"
    )

    print(
        f"  50ms total median:     "
        f"{latency_classical['total_median_ms']:.3f} ms"
    )

    print(
        f"  loss total median:     "
        f"{loss_classical['total_median_ms']:.3f} ms"
    )

    print()

    print("X25519MLKEM768")

    print(
        f"  baseline total median: "
        f"{baseline_hybrid['total_median_ms']:.3f} ms"
    )

    print(
        f"  50ms total median:     "
        f"{latency_hybrid['total_median_ms']:.3f} ms"
    )

    print(
        f"  loss total median:     "
        f"{loss_hybrid['total_median_ms']:.3f} ms"
    )

    print()
    print(
        "=== Loss-Condition TLS Tails ==="
    )
    print()

    print("X25519")

    print(
        f"  median: "
        f"{loss_classical['tls_median_ms']:.3f} ms"
    )

    print(
        f"  SD:     "
        f"{loss_classical['tls_sd_ms']:.3f} ms"
    )

    print(
        f"  p95:    "
        f"{loss_classical['tls_p95_ms']:.3f} ms"
    )

    print(
        f"  p99:    "
        f"{loss_classical['tls_p99_ms']:.3f} ms"
    )

    print(
        f"  max:    "
        f"{loss_classical['tls_max_ms']:.3f} ms"
    )

    print()

    print("X25519MLKEM768")

    print(
        f"  median: "
        f"{loss_hybrid['tls_median_ms']:.3f} ms"
    )

    print(
        f"  SD:     "
        f"{loss_hybrid['tls_sd_ms']:.3f} ms"
    )

    print(
        f"  p95:    "
        f"{loss_hybrid['tls_p95_ms']:.3f} ms"
    )

    print(
        f"  p99:    "
        f"{loss_hybrid['tls_p99_ms']:.3f} ms"
    )

    print(
        f"  max:    "
        f"{loss_hybrid['tls_max_ms']:.3f} ms"
    )

    print()

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
        "total_p99_ms",
        "total_max_ms",
    ]

    with SUMMARY_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for result in results:

            output = result.copy()

            for key, value in output.items():

                if isinstance(
                    value,
                    float
                ):

                    output[key] = round(
                        value,
                        4
                    )

            writer.writerow(
                output
            )

    print(
        f"Saved summary: "
        f"{SUMMARY_FILE}"
    )


if __name__ == "__main__":
    main()
