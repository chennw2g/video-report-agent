param(
  [string]$Url = "https://www.bilibili.com/",
  [string]$OutputPath = (Join-Path $env:APPDATA "video-bundle-agent\bilibili.cookies.txt"),
  [int]$Port = 9224,
  [string]$ChromePath = "",
  [switch]$UseDefaultChromeProfile,
  [string]$UserDataDir = (Join-Path $env:APPDATA "video-bundle-agent\chrome-bilibili-profile"),
  [switch]$KeepBrowserOpen,
  [switch]$OpenOnly,
  [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Resolve-FirstExistingPath {
  param([string[]]$Candidates)
  foreach ($candidate in $Candidates) {
    if ($candidate -and (Test-Path -LiteralPath $candidate)) {
      return $candidate
    }
  }
  return $null
}

if (-not $ChromePath) {
  $chromeCandidates = @()
  if ($env:ProgramFiles) {
    $chromeCandidates += (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe")
  }
  if (${env:ProgramFiles(x86)}) {
    $chromeCandidates += (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe")
  }
  if ($env:LocalAppData) {
    $chromeCandidates += (Join-Path $env:LocalAppData "Google\Chrome\Application\chrome.exe")
  }
  $ChromePath = Resolve-FirstExistingPath $chromeCandidates
}
if (-not $ChromePath) {
  throw "Chrome was not found. Pass -ChromePath <path-to-chrome.exe>."
}

$node = "D:\Workshop\NodeJS\node.exe"
if (-not (Test-Path -LiteralPath $node)) {
  $node = "node"
}

$exporter = Join-Path $PSScriptRoot "export-youtube-cookies-cdp.mjs"
if (-not (Test-Path -LiteralPath $exporter)) {
  throw "Missing exporter script: $exporter"
}

$chromeArgs = @(
  "--remote-debugging-address=127.0.0.1",
  "--remote-debugging-port=$Port",
  "--new-window",
  $Url
)

if (-not $UseDefaultChromeProfile) {
  New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null
  $chromeArgs = @("--user-data-dir=$UserDataDir") + $chromeArgs
}

Write-Host "Opening browser for Bilibili cookie refresh."
if ($UseDefaultChromeProfile) {
  Write-Host "Mode: default browser profile. Close normal browser windows first if DevTools cannot attach."
} else {
  Write-Host "Mode: dedicated profile: $UserDataDir"
}
Write-Host "Cookie output: $OutputPath"

$chromeProcess = Start-Process -FilePath $ChromePath -ArgumentList $chromeArgs -PassThru

if ($OpenOnly) {
  Write-Host "Browser is open for Bilibili login. Return here after signing in, then run this script again without -OpenOnly."
  return
}

if (-not $NoPrompt) {
  Write-Host ""
  Write-Host "Sign in to Bilibili in the opened Chrome window."
  Write-Host "After the Bilibili page is loaded as a signed-in user, return here and press Enter."
  Read-Host | Out-Null
} else {
  Start-Sleep -Seconds 5
}

& $node $exporter --port $Port --output $OutputPath --domains bilibili.com
$code = $LASTEXITCODE
if ($code -ne 0) {
  throw "Cookie export failed with exit code $code."
}

Write-Host "Cookies exported for Bilibili API and yt-dlp fallback."
Write-Host "Run video-bundle-agent with --cookies `"$OutputPath`"."

if (-not $KeepBrowserOpen) {
  try {
    Stop-Process -Id $chromeProcess.Id -ErrorAction SilentlyContinue
  } catch {
    # ignore cleanup failure
  }
}
