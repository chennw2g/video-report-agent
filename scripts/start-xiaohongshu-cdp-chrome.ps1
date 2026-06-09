param(
    [int]$Port = 9231,
    [string]$ProfileDir = "$env:APPDATA\video-bundle-agent\chrome-xiaohongshu-profile",
    [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$StartUrl = "https://www.xiaohongshu.com/"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ChromePath)) {
    throw "Chrome was not found at: $ChromePath"
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Output "CDP port $Port is already listening. Reusing existing browser."
    Write-Output "Profile: $ProfileDir"
    Write-Output "Open or verify: $StartUrl"
    try {
        $encodedUrl = [System.Uri]::EscapeDataString($StartUrl)
        Invoke-WebRequest -UseBasicParsing -Method Put -Uri "http://127.0.0.1:$Port/json/new?$encodedUrl" | Out-Null
    } catch {
        Write-Warning "Could not open a new CDP tab automatically: $($_.Exception.Message)"
    }
    return
}

$args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--no-default-browser-check",
    $StartUrl
)

Start-Process -FilePath $ChromePath -ArgumentList $args

Write-Output "Started Xiaohongshu CDP Chrome."
Write-Output "CDP endpoint: http://127.0.0.1:$Port"
Write-Output "Profile: $ProfileDir"
Write-Output "Login/verify in this browser before running Xiaohongshu comment collection."
