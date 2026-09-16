#!/usr/bin/env python3

import csv
import math
import statistics
from pathlib import Path


ROOT = Path("/mnt/c/Research/pqc-tls-lab")

FILES = {
    "X25519":
        ROOT / "results" / "wsl-baseline-x25519.csv",

    "X25519MLKEM768":
        ROOT / "results" / "wsl-baseline-x25519mlkem768.csv",
}

SUMMARY_FILE = (
    ROOT / "results" / "wsl-baseline-handshake-summary.csv"
)


def percentile(values, p):
    """
    Linear-interpolated percentile.
    p should be between 0 and 100.
    """

    values = sorted(values)

    if not values:
        raise ValueError("Cannot calculate percentile of empty data.")

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


def load_results(path):
    rows = []

    with path.open(newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    return rows


def analyze_group(group, path):
    rows = load_results(path)

    successful = [
        row for row in rows
        if row["status"] == "ok"
    ]

    failed = [
        row for row in rows
        if row["status"] != "ok"
    ]

    tls_values = [
        float(row["tls_handshake_ms"])
        for row in successful
    ]

    tcp_values = [
        float(row["tcp_connect_ms"])
        for row in successful
    ]

    total_values = [
        float(row["total_ms"])
        for row in successful
    ]

    negotiated_groups = {
        row["negotiated_group"]
        for row in successful
    }

    if not tls_values:
        raise RuntimeError(
            f"No successful TLS handshakes found for {group}"
        )

    return {
        "group": group,
        "samples": len(rows),
        "successes": len(successful),
        "failures": len(failed),
        "negotiated_groups": ",".join(
            sorted(negotiated_groups)
        ),
        "tls_mean_ms":
            statistics.mean(tls_values),
        "tls_median_ms":
            statistics.median(tls_values),
        "tls_sd_ms":
            statistics.stdev(tls_values)
            if len(tls_values) > 1
            else 0.0,
        "tls_min_ms":
            min(tls_values),
        "tls_max_ms":
            max(tls_values),
        "tls_p95_ms":
            percentile(tls_values, 95),
        "tls_p99_ms":
            percentile(tls_values, 99),
        "tcp_median_ms":
            statistics.median(tcp_values),
        "total_median_ms":
            statistics.median(total_values),
    }


def main():
    results = []

    for group, path in FILES.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Missing dataset: {path}"
            )

        results.append(
            analyze_group(group, path)
        )

    classical = next(
        r for r in results
        if r["group"] == "X25519"
    )

    hybrid = next(
        r for r in results
        if r["group"] == "X25519MLKEM768"
    )

    median_delta = (
        (
            hybrid["tls_median_ms"]
            / classical["tls_median_ms"]
        )
        - 1
    ) * 100

    mean_delta = (
        (
            hybrid["tls_mean_ms"]
            / classical["tls_mean_ms"]
        )
        - 1
    ) * 100

    print()
    print("=== TLS Handshake Benchmark ===")
    print()

    for result in results:

        print(result["group"])
        print(
            f"  Samples:   {result['samples']}"
        )
        print(
            f"  Successes: {result['successes']}"
        )
        print(
            f"  Failures:  {result['failures']}"
        )
        print(
            "  Negotiated: "
            f"{result['negotiated_groups']}"
        )
        print(
            "  TLS mean:   "
            f"{result['tls_mean_ms']:.3f} ms"
        )
        print(
            "  TLS median: "
            f"{result['tls_median_ms']:.3f} ms"
        )
        print(
            "  TLS SD:     "
            f"{result['tls_sd_ms']:.3f} ms"
        )
        print(
            "  TLS p95:    "
            f"{result['tls_p95_ms']:.3f} ms"
        )
        print(
            "  TLS p99:    "
            f"{result['tls_p99_ms']:.3f} ms"
        )
        print(
            "  TLS range:  "
            f"{result['tls_min_ms']:.3f}"
            " - "
            f"{result['tls_max_ms']:.3f} ms"
        )
        print(
            "  TCP median: "
            f"{result['tcp_median_ms']:.3f} ms"
        )
        print(
            "  Total median: "
            f"{result['total_median_ms']:.3f} ms"
        )
        print()

    print(
        "Hybrid median TLS latency delta: "
        f"{median_delta:+.2f}%"
    )

    print(
        "Hybrid mean TLS latency delta:   "
        f"{mean_delta:+.2f}%"
    )

    fields = [
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
        "tcp_median_ms",
        "total_median_ms",
    ]

    with SUMMARY_FILE.open(
        "w",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        for result in results:

            output = result.copy()

            for key, value in output.items():

                if isinstance(value, float):
                    output[key] = round(value, 4)

            writer.writerow(output)

    print()
    print(f"Saved summary: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
