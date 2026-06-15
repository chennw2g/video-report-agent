param(
    [string]$Version = "v1.8.6",
    [ValidateSet("cpu", "blas", "cuda118", "cuda124")]
    [string]$Backend = "cpu",
    [string]$InstallRoot = "",
    [string]$Model = "large-v3-turbo",
    [string]$LanguageModel = "base",
    [switch]$SkipRuntime,
    [switch]$SkipModel,
    [switch]$SkipLanguageModel,
    [switch]$Force,
    [switch]$SetUserEnv
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Resolve-InstallRoot {
    if ($InstallRoot) {
        return $InstallRoot
    }
    if ($env:VIDEO_BUNDLE_AGENT_TOOL_ROOT) {
        return $env:VIDEO_BUNDLE_AGENT_TOOL_ROOT
    }
    if ($env:VIDEO_REPORT_AGENT_TOOL_ROOT) {
        return $env:VIDEO_REPORT_AGENT_TOOL_ROOT
    }
    return "D:\Workshop"
}

function Resolve-AssetName {
    switch ($Backend) {
        "cpu" { return "whisper-bin-x64.zip" }
        "blas" { return "whisper-blas-bin-x64.zip" }
        "cuda118" { return "whisper-cublas-11.8.0-bin-x64.zip" }
        "cuda124" { return "whisper-cublas-12.4.0-bin-x64.zip" }
        default { throw "Unsupported whisper.cpp backend: $Backend" }
    }
}

function Resolve-RuntimeName {
    switch ($Backend) {
        "cpu" { return $Version }
        "blas" { return "$Version-blas" }
        "cuda118" { return "$Version-cuda" }
        "cuda124" { return "$Version-cuda" }
        default { throw "Unsupported whisper.cpp backend: $Backend" }
    }
}

function Resolve-ModelFileName {
    param([string]$Name)

    if ($Name.ToLowerInvariant().EndsWith(".bin")) {
        return $Name
    }
    if ($Name.ToLowerInvariant().StartsWith("ggml-")) {
        return "$Name.bin"
    }
    return "ggml-$Name.bin"
}

function Download-File {
    param(
        [string]$Url,
        [string]$Destination
    )

    if ((Test-Path -LiteralPath $Destination) -and -not $Force) {
        Write-Host "Already exists: $Destination"
        return
    }

    $parent = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Write-Host "Downloading: $Url"
    Write-Host "To: $Destination"
    Invoke-WebRequest -Uri $Url -OutFile $Destination
}

function Assert-ChildPath {
    param(
        [string]$Parent,
        [string]$Child
    )

    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')
    $childFull = [System.IO.Path]::GetFullPath($Child).TrimEnd('\', '/')
    if (-not $childFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside install root: $Child"
    }
}

$resolvedInstallRoot = Resolve-InstallRoot
$assetName = Resolve-AssetName
$runtimeName = Resolve-RuntimeName
$runtimeDir = Join-Path $resolvedInstallRoot "whisper.cpp\$runtimeName\Release"
$runtimeExe = Join-Path $runtimeDir "whisper-cli.exe"
$modelsDir = Join-Path $resolvedInstallRoot "whisper.cpp\models"
$modelFile = Resolve-ModelFileName $Model
$languageModelFile = Resolve-ModelFileName $LanguageModel
$modelPath = Join-Path $modelsDir $modelFile
$languageModelPath = Join-Path $modelsDir $languageModelFile

if (-not $SkipRuntime) {
    if ((Test-Path -LiteralPath $runtimeExe) -and -not $Force) {
        Write-Host "whisper.cpp runtime already exists: $runtimeExe"
    } else {
        $downloadUrl = "https://github.com/ggml-org/whisper.cpp/releases/download/$Version/$assetName"
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "video-bundle-agent-whisper-$([System.Guid]::NewGuid())"
        $zipPath = Join-Path $tempRoot $assetName
        $extractDir = Join-Path $tempRoot "extract"
        New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
        try {
            Download-File -Url $downloadUrl -Destination $zipPath
            Expand-Archive -LiteralPath $zipPath -DestinationPath $extractDir -Force
            $exe = Get-ChildItem -LiteralPath $extractDir -Recurse -Filter "whisper-cli.exe" |
                Select-Object -First 1
            if (-not $exe) {
                throw "Downloaded whisper.cpp archive did not contain whisper-cli.exe."
            }

            if ((Test-Path -LiteralPath $runtimeDir) -and $Force) {
                Assert-ChildPath -Parent $resolvedInstallRoot -Child $runtimeDir
                Remove-Item -LiteralPath $runtimeDir -Recurse -Force
            }

            New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
            Copy-Item -Path (Join-Path $exe.Directory.FullName "*") -Destination $runtimeDir -Recurse -Force
            Write-Host "Installed whisper.cpp runtime: $runtimeExe"
        } finally {
            if (Test-Path -LiteralPath $tempRoot) {
                Remove-Item -LiteralPath $tempRoot -Recurse -Force
            }
        }
    }
}

if (-not $SkipModel) {
    $modelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$modelFile"
    Download-File -Url $modelUrl -Destination $modelPath
}

if (-not $SkipLanguageModel -and $languageModelFile -ne $modelFile) {
    $languageModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$languageModelFile"
    Download-File -Url $languageModelUrl -Destination $languageModelPath
}

if ($SetUserEnv) {
    [System.Environment]::SetEnvironmentVariable(
        "VIDEO_BUNDLE_AGENT_WHISPER_MODEL",
        $modelPath,
        "User"
    )
    [System.Environment]::SetEnvironmentVariable(
        "VIDEO_BUNDLE_AGENT_WHISPER_LANGUAGE_MODEL",
        $languageModelPath,
        "User"
    )
    Write-Host "Updated user environment variables for whisper.cpp model paths."
    Write-Host "Open a new PowerShell session before relying on these user environment values."
}

Write-Host ""
Write-Host "whisper.cpp install summary"
Write-Host "Install root: $resolvedInstallRoot"
Write-Host "Backend: $Backend"
Write-Host "Runtime: $runtimeExe"
Write-Host "Model: $modelPath"
Write-Host "Language model: $languageModelPath"
Write-Host ""
Write-Host "Verify with:"
Write-Host "uv run video-bundle-agent doctor"
