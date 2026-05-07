param(
    [string]$Version = "0.1.1"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
$PortableRoot = Join-Path $Dist "Echoes-Windows"
$AppDir = Join-Path $PortableRoot "Echoes"
$ZipPath = Join-Path $Dist "Echoes-Windows-v$Version.zip"

Set-Location $Root

function Assert-UnderRoot {
    param([string]$Path)

    $RootPath = [System.IO.Path]::GetFullPath($Root)
    $TargetPath = [System.IO.Path]::GetFullPath($Path)
    if (-not $TargetPath.StartsWith($RootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside project root: $TargetPath"
    }
}

Assert-UnderRoot $Build
Assert-UnderRoot $PortableRoot
Assert-UnderRoot $ZipPath

if (Test-Path $Build) {
    Remove-Item -LiteralPath $Build -Recurse -Force
}
if (Test-Path $PortableRoot) {
    Remove-Item -LiteralPath $PortableRoot -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

uv run pyinstaller --noconfirm .\echoes.spec --distpath $PortableRoot --workpath $Build

$BuiltApp = Join-Path $PortableRoot "Echoes"
if (-not (Test-Path (Join-Path $BuiltApp "echoes.exe"))) {
    throw "PyInstaller did not create echoes.exe"
}

Copy-Item -LiteralPath ".\packaging\windows\start.cmd" -Destination $BuiltApp -Force
Copy-Item -LiteralPath ".\packaging\windows\import.cmd" -Destination $BuiltApp -Force
Copy-Item -LiteralPath ".\packaging\windows\doctor.cmd" -Destination $BuiltApp -Force
Copy-Item -LiteralPath ".\packaging\windows\items.csv.template" -Destination $BuiltApp -Force
Copy-Item -LiteralPath ".\packaging\windows\README-quick.md" -Destination $BuiltApp -Force
New-Item -ItemType Directory -Path (Join-Path $BuiltApp "data") -Force | Out-Null

Compress-Archive -Path $AppDir -DestinationPath $ZipPath -Force

Write-Host "Built $AppDir"
Write-Host "Built $ZipPath"
