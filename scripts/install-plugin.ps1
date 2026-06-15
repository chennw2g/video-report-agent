param(
    [string]$PluginName = "video-report-agent",
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$UserProfileRoot = $env:USERPROFILE
)

$ErrorActionPreference = "Stop"

$source = Join-Path $ProjectRoot "plugins\$PluginName"
$destinationRoot = Join-Path $UserProfileRoot "plugins"
$destination = Join-Path $destinationRoot $PluginName
$marketplaceDir = Join-Path $UserProfileRoot ".agents\plugins"
$marketplacePath = Join-Path $marketplaceDir "marketplace.json"

if (-not (Test-Path (Join-Path $source ".codex-plugin\plugin.json"))) {
    throw "Plugin source is missing .codex-plugin\plugin.json: $source"
}

New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null
New-Item -ItemType Directory -Force -Path $marketplaceDir | Out-Null

if (Test-Path $destination) {
    Remove-Item -LiteralPath $destination -Recurse -Force
}
Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force

if (Test-Path $marketplacePath) {
    $marketplace = Get-Content -LiteralPath $marketplacePath -Raw | ConvertFrom-Json
    if (-not $marketplace.name) {
        $marketplace | Add-Member -NotePropertyName name -NotePropertyValue "personal"
    }
    if (-not $marketplace.interface) {
        $marketplace | Add-Member -NotePropertyName interface -NotePropertyValue ([pscustomobject]@{
            displayName = "Personal"
        })
    }
    if (-not $marketplace.plugins) {
        $marketplace | Add-Member -NotePropertyName plugins -NotePropertyValue @()
    }
} else {
    $marketplace = [pscustomobject]@{
        name = "personal"
        interface = [pscustomobject]@{
            displayName = "Personal"
        }
        plugins = @()
    }
}

$entry = [pscustomobject]@{
    name = $PluginName
    source = [pscustomobject]@{
        source = "local"
        path = "./plugins/$PluginName"
    }
    policy = [pscustomobject]@{
        installation = "AVAILABLE"
        authentication = "ON_INSTALL"
    }
    category = "Productivity"
}

$plugins = @($marketplace.plugins | Where-Object { $_.name -ne $PluginName })
$plugins += $entry
$marketplace.plugins = $plugins

$marketplaceJson = $marketplace | ConvertTo-Json -Depth 20
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $marketplacePath,
    $marketplaceJson + [System.Environment]::NewLine,
    $utf8NoBom
)

Write-Host "Installed plugin source: $destination"
Write-Host "Updated personal marketplace: $marketplacePath"
Write-Host "Next: install or refresh Video Report Agent from the Codex app plugin UI."
