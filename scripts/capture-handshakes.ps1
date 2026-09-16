param(
    [int]$Interface = 9,
    [int]$Port = 8443
)

$ErrorActionPreference = "Stop"

$OpenSSL = (Get-Command openssl).Source
$Tshark  = (Get-Command tshark).Source

$Root     = Split-Path $PSScriptRoot -Parent
$Cert     = Join-Path $Root "certs\server.crt"
$Key      = Join-Path $Root "certs\server.key"
$Captures = Join-Path $Root "captures"
$Results  = Join-Path $Root "results"

New-Item -ItemType Directory -Force -Path $Captures, $Results | Out-Null

$requestFile = Join-Path $Results "request.txt"
"GET / HTTP/1.0`r`nHost: localhost`r`n`r`n" |
    Set-Content -NoNewline $requestFile

function Invoke-TLSCapture {
    param(
        [string]$Group,
        [string]$Name
    )

    Write-Host "`n=== Testing $Group ==="

    $captureFile = Join-Path $Captures "$Name.pcapng"
    $clientOut   = Join-Path $Results "$Name-client.txt"
    $clientErr   = Join-Path $Results "$Name-client-error.txt"
    $serverOut   = Join-Path $Results "$Name-server.txt"
    $serverErr   = Join-Path $Results "$Name-server-error.txt"

    Remove-Item $captureFile,$clientOut,$clientErr,$serverOut,$serverErr `
        -ErrorAction SilentlyContinue

    $listener = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue

    if ($listener) {
        throw "Port $Port is already in use."
    }

    $capture = Start-Process `
        -FilePath $Tshark `
        -ArgumentList @(
            "-i", $Interface,
            "-f", "`"tcp port $Port`"",
            "-a", "duration:3",
            "-w", "`"$captureFile`""
        ) `
        -PassThru `
        -NoNewWindow

    Start-Sleep -Seconds 2

    $server = Start-Process `
        -FilePath $OpenSSL `
        -ArgumentList @(
            "s_server",
            "-accept", $Port,
            "-cert", "`"$Cert`"",
            "-key", "`"$Key`"",
            "-tls1_3",
            "-groups", $Group,
            "-www"
        ) `
        -RedirectStandardOutput $serverOut `
        -RedirectStandardError $serverErr `
        -PassThru `
        -NoNewWindow

    Start-Sleep -Milliseconds 500

    $client = Start-Process `
        -FilePath $OpenSSL `
        -ArgumentList @(
            "s_client",
            "-connect", "localhost:$Port",
            "-servername", "localhost",
            "-tls1_3",
            "-groups", $Group,
            "-brief"
        ) `
        -RedirectStandardInput $requestFile `
        -RedirectStandardOutput $clientOut `
        -RedirectStandardError $clientErr `
        -PassThru `
        -NoNewWindow `
        -Wait

    Start-Sleep -Milliseconds 250

    if (!$server.HasExited) {
        Stop-Process -Id $server.Id
    }

    $capture.WaitForExit()

    Write-Host "Saved: $captureFile"
}

Invoke-TLSCapture -Group "X25519" -Name "auto-x25519"

Invoke-TLSCapture `
    -Group "X25519MLKEM768" `
    -Name "auto-x25519mlkem768"

Write-Host "`n=== Capture summary ==="

capinfos `
    "$Captures\auto-x25519.pcapng" `
    "$Captures\auto-x25519mlkem768.pcapng"