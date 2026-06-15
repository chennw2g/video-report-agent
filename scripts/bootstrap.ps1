param(
    [switch]$InstallUv,
    [switch]$InstallWindowsTools,
    [switch]$WithFunASR,
    [switch]$WithWhisperCpp,
    [ValidateSet("cpu", "blas", "cuda118", "cuda124")]
    [string]$WhisperBackend = "cpu",
    [string]$WhisperModel = "large-v3-turbo",
    [string]$WhisperLanguageModel = "base",
    [switch]$WithPlaywright,
    [switch]$WithMediaCrawler,
    [switch]$InstallPlugin,
    [string]$ToolRoot = "",
    [string]$MediaCrawlerPath = "",
    [switch]$SkipDoctor
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $MediaCrawlerPath) {
    $MediaCrawlerPath = Join-Path $ProjectRoot "external\MediaCrawler"
}

function Get-CommandPath {
    param([string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\$Name.exe"),
        (Join-Path $env:USERPROFILE "AppData\Roaming\Python\Python312\Scripts\$Name.exe"),
        (Join-Path $env:USERPROFILE "AppData\Local\Programs\Python\Python312\Scripts\$Name.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    return $null
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $ProjectRoot
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath failed with exit code $LASTEXITCODE"
        }
    } finally {
        Pop-Location
    }
}

function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$DisplayName
    )

    $winget = Get-CommandPath "winget"
    if (-not $winget) {
        Write-Warning "winget was not found; install $DisplayName manually."
        return
    }

    Write-Host "Installing or updating $DisplayName with winget..."
    Invoke-Native -FilePath $winget -Arguments @(
        "install",
        "--id",
        $PackageId,
        "-e",
        "--source",
        "winget",
        "--accept-package-agreements",
        "--accept-source-agreements"
    )
}

if ($ToolRoot) {
    $env:VIDEO_BUNDLE_AGENT_TOOL_ROOT = $ToolRoot
}
$env:XHS_MEDIACRAWLER_PATH = $MediaCrawlerPath

if ($InstallWindowsTools) {
    if (-not (Get-CommandPath "python")) {
        Install-WingetPackage "Python.Python.3.12" "Python 3.12"
    }
    if (-not (Get-CommandPath "git")) {
        Install-WingetPackage "Git.Git" "Git"
    }
    if (-not (Get-CommandPath "node")) {
        Install-WingetPackage "OpenJS.NodeJS.LTS" "Node.js LTS"
    }
    if (-not (Get-CommandPath "ffmpeg")) {
        Install-WingetPackage "Gyan.FFmpeg" "FFmpeg"
    }
    Write-Warning "If a newly installed tool is still not found, open a new PowerShell session and rerun bootstrap."
}

$uv = Get-CommandPath "uv"
if (-not $uv -and $InstallUv) {
    Write-Host "Installing uv with the official Astral installer..."
    Invoke-RestMethod "https://astral.sh/uv/install.ps1" | Invoke-Expression
    $env:Path = (Join-Path $env:USERPROFILE ".local\bin") + [IO.Path]::PathSeparator + $env:Path
    $uv = Get-CommandPath "uv"
}
if (-not $uv) {
    throw "uv was not found. Install uv first or rerun with -InstallUv."
}

$syncArgs = @("sync")
if ($WithFunASR) {
    $syncArgs += @("--extra", "funasr")
}
Invoke-Native -FilePath $uv -Arguments $syncArgs

if ($WithPlaywright) {
    Invoke-Native -FilePath $uv -Arguments @("run", "playwright", "install", "chromium")
}

if ($WithWhisperCpp) {
    $whisperArgs = @(
        "-Backend",
        $WhisperBackend,
        "-Model",
        $WhisperModel,
        "-LanguageModel",
        $WhisperLanguageModel
    )
    if ($ToolRoot) {
        $whisperArgs += @("-InstallRoot", $ToolRoot)
    }
    & (Join-Path $ProjectRoot "scripts\install-whisper-cpp.ps1") @whisperArgs
}

if ($WithMediaCrawler) {
    $git = Get-CommandPath "git"
    if (-not $git) {
        throw "Git was not found. Install Git or rerun with -InstallWindowsTools."
    }

    if (-not (Test-Path (Join-Path $MediaCrawlerPath "main.py"))) {
        $parent = Split-Path -Parent $MediaCrawlerPath
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
        Invoke-Native -FilePath $git -Arguments @(
            "clone",
            "https://github.com/NanmiCoder/MediaCrawler.git",
            $MediaCrawlerPath
        )
    }

    Invoke-Native -FilePath $uv -Arguments @("sync") -WorkingDirectory $MediaCrawlerPath
    Invoke-Native -FilePath $uv -Arguments @("run", "playwright", "install", "chromium") -WorkingDirectory $MediaCrawlerPath
}

if ($InstallPlugin) {
    & (Join-Path $ProjectRoot "scripts\install-plugin.ps1") -ProjectRoot $ProjectRoot
}

if (-not $SkipDoctor) {
    Invoke-Native -FilePath $uv -Arguments @("run", "video-bundle-agent", "doctor")
}

Write-Host ""
Write-Host "Bootstrap completed."
Write-Host "Project root: $ProjectRoot"
Write-Host "MediaCrawler path: $MediaCrawlerPath"
if ($ToolRoot) {
    Write-Host "Tool root: $ToolRoot"
}
