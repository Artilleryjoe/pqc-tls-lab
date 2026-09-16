$ErrorActionPreference = "Stop"

$Root    = Split-Path $PSScriptRoot -Parent
$CsvPath = Join-Path $Root "results\tls-benchmark.csv"
$OutPath = Join-Path $Root "results\tls-benchmark-summary.csv"
$NotePath = Join-Path $Root "notes\benchmark-summary.md"

$data = Import-Csv $CsvPath

function Get-Stats {
    param(
        [array]$Rows,
        [string]$Group
    )

    $values = @(
        $Rows |
        Where-Object { $_.Group -eq $Group } |
        ForEach-Object { [double]$_.ConnectionsPerSecond }
    )

    if ($values.Count -lt 2) {
        throw "Not enough samples for $Group"
    }

    $sorted = $values | Sort-Object
    $mean = ($values | Measure-Object -Average).Average

    if ($sorted.Count % 2 -eq 1) {
        $median = $sorted[[math]::Floor($sorted.Count / 2)]
    }
    else {
        $middle = $sorted.Count / 2
        $median = ($sorted[$middle - 1] + $sorted[$middle]) / 2
    }

    $sumSq = 0
    foreach ($value in $values) {
        $sumSq += [math]::Pow(($value - $mean), 2)
    }

    $sampleSD = [math]::Sqrt($sumSq / ($values.Count - 1))

    [PSCustomObject]@{
        Group       = $Group
        Samples     = $values.Count
        MeanCPS     = [math]::Round($mean, 2)
        MedianCPS   = [math]::Round($median, 2)
        SampleSD    = [math]::Round($sampleSD, 2)
        MinCPS      = [math]::Round(($values | Measure-Object -Minimum).Minimum, 2)
        MaxCPS      = [math]::Round(($values | Measure-Object -Maximum).Maximum, 2)
    }
}

$x25519 = Get-Stats -Rows $data -Group "X25519"
$hybrid = Get-Stats -Rows $data -Group "X25519MLKEM768"

$meanDelta = (($hybrid.MeanCPS / $x25519.MeanCPS) - 1) * 100
$medianDelta = (($hybrid.MedianCPS / $x25519.MedianCPS) - 1) * 100

$summary = @($x25519, $hybrid)

$summary | Export-Csv $OutPath -NoTypeInformation

Write-Host "`n=== Statistical Summary ==="
$summary | Format-Table -AutoSize

Write-Host "`nHybrid mean throughput delta: $([math]::Round($meanDelta,2))%"
Write-Host "Hybrid median throughput delta: $([math]::Round($medianDelta,2))%"

$markdown = @"
# TLS Benchmark Summary

Date: $(Get-Date -Format "yyyy-MM-dd")

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
| X25519 | $($x25519.Samples) | $($x25519.MeanCPS) | $($x25519.MedianCPS) | $($x25519.SampleSD) | $($x25519.MinCPS) | $($x25519.MaxCPS) |
| X25519MLKEM768 | $($hybrid.Samples) | $($hybrid.MeanCPS) | $($hybrid.MedianCPS) | $($hybrid.SampleSD) | $($hybrid.MinCPS) | $($hybrid.MaxCPS) |

Hybrid mean throughput delta: $([math]::Round($meanDelta,2))%

Hybrid median throughput delta: $([math]::Round($medianDelta,2))%

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
"@

$markdown | Set-Content $NotePath

Write-Host "`nSaved:"
Write-Host $OutPath
Write-Host $NotePath