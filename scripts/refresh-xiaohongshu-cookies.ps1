param(
  [string]$Url = "https://www.xiaohongshu.com/explore",
  [string]$OutputPath = (Join-Path $env:APPDATA "video-bundle-agent\xiaohongshu.cookies.txt"),
  [int]$Port = 9226,
  [string]$ChromePath = "",
  [switch]$UseDefaultChromeProfile,
  [string]$UserDataDir = (Join-Path $env:APPDATA "video-bundle-agent\chrome-xiaohongshu-profile"),
  [switch]$KeepBrowserOpen,
  [switch]$OpenOnly,
  [switch]$NoPrompt,
  [string]$NodePath = ""
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
  if (${env:ProgramFiles(x86)}) {
    $chromeCandidates += (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe")
  }
  $ChromePath = Resolve-FirstExistingPath $chromeCandidates
}
if (-not $ChromePath) {
  throw "Chrome or Edge was not found. Pass -ChromePath <path-to-browser.exe>."
}

if (-not $NodePath) {
  $toolRoot = $env:VIDEO_BUNDLE_AGENT_TOOL_ROOT
  if (-not $toolRoot) {
    $toolRoot = $env:VIDEO_REPORT_AGENT_TOOL_ROOT
  }
  $nodeCandidates = @()
  if ($toolRoot) {
    $nodeCandidates += (Join-Path $toolRoot "NodeJS\node.exe")
  }
  $nodeCandidates += "D:\Workshop\NodeJS\node.exe"
  $NodePath = Resolve-FirstExistingPath $nodeCandidates
}
if (-not $NodePath) {
  $NodePath = "node"
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

Write-Host "Opening browser for Xiaohongshu cookie refresh."
if ($UseDefaultChromeProfile) {
  Write-Host "Mode: default browser profile. Close normal browser windows first if DevTools cannot attach."
} else {
  Write-Host "Mode: dedicated profile: $UserDataDir"
}
Write-Host "Cookie output: $OutputPath"

$chromeProcess = Start-Process -FilePath $ChromePath -ArgumentList $chromeArgs -PassThru

if ($OpenOnly) {
  Write-Host "Browser is open for Xiaohongshu login. Return here after signing in, then run this script again without -OpenOnly."
  return
}

if (-not $NoPrompt) {
  Write-Host ""
  Write-Host "Open Xiaohongshu in the browser window and sign in if needed."
  Write-Host "After the page is loaded, return here and press Enter."
  Read-Host | Out-Null
} else {
  Start-Sleep -Seconds 5
}

& $NodePath $exporter --port $Port --output $OutputPath --domains xiaohongshu.com,xhslink.com
$code = $LASTEXITCODE
if ($code -ne 0) {
  throw "Cookie export failed with exit code $code."
}

Write-Host "Cookies exported for Xiaohongshu."
Write-Host "Run video-bundle-agent with --cookies `"$OutputPath`"."

if (-not $KeepBrowserOpen) {
  try {
    Stop-Process -Id $chromeProcess.Id -ErrorAction SilentlyContinue
  } catch {
    # ignore cleanup failure
  }
}
