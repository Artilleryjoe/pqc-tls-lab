$ErrorActionPreference = "Stop"

$OpenSSL = (Get-Command openssl).Source
$Root    = Split-Path $PSScriptRoot -Parent
$Cert    = Join-Path $Root "certs\server.crt"
$Key     = Join-Path $Root "certs\server.key"
$Results = Join-Path $Root "results"

$Port = 8443
$Duration = 30

New-Item -ItemType Directory -Force -Path $Results | Out-Null

$sequence = @(
    "X25519",
    "X25519MLKEM768",
    "X25519MLKEM768",
    "X25519",
    "X25519",
    "X25519MLKEM768",
    "X25519MLKEM768",
    "X25519",
    "X25519",
    "X25519MLKEM768"
)

$data = @()

for ($i = 0; $i -lt $sequence.Count; $i++) {

    $group = $sequence[$i]

    Write-Host "`n=== Run $($i + 1): $group ==="

    $serverOut = Join-Path $Results "server-$($i + 1).txt"
    $serverErr = Join-Path $Results "server-$($i + 1)-error.txt"

    $server = Start-Process `
        -FilePath $OpenSSL `
        -ArgumentList @(
            "s_server",
            "-accept", $Port,
            "-cert", "`"$Cert`"",
            "-key", "`"$Key`"",
            "-tls1_3",
            "-groups", $group,
            "-quiet"
        ) `
        -RedirectStandardOutput $serverOut `
        -RedirectStandardError $serverErr `
        -PassThru `
        -NoNewWindow

    Start-Sleep -Seconds 1

    $output = & $OpenSSL s_time `
        -connect "localhost:$Port" `
        -tls1_3 `
        -new `
        -time $Duration 2>&1 | Out-String

    if (!$server.HasExited) {
        Stop-Process -Id $server.Id
    }

    $match = [regex]::Match(
        $output,
        '(\d+) connections in (\d+) real seconds'
    )

    if (!$match.Success) {
        Write-Warning "Could not parse run $($i + 1)"
        Write-Host $output
        continue
    }

    $connections = [int]$match.Groups[1].Value
    $seconds     = [int]$match.Groups[2].Value
    $rate        = $connections / $seconds

    $data += [PSCustomObject]@{
        Run                  = $i + 1
        Group                = $group
        Connections          = $connections
        RealSeconds          = $seconds
        ConnectionsPerSecond = [math]::Round($rate, 2)
    }

    Write-Host "$connections connections / $seconds sec"
    Write-Host "$([math]::Round($rate,2)) connections/sec"

    Start-Sleep -Seconds 2
}

$csv = Join-Path $Results "tls-benchmark.csv"

$data | Export-Csv $csv -NoTypeInformation

Write-Host "`n=== Results ==="
$data | Format-Table -AutoSize

Write-Host "`nSaved to: $csv"