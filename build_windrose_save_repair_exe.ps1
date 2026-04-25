param(
    [string]$PythonExe = "python",
    [string]$EntryScript = "windrose_save_repair_tool.py",
    [string]$OutputName = "WindroseSaveRepairTool",
    [switch]$Console
)

$ErrorActionPreference = "Stop"

# This script installs the minimal build dependencies, normalizes PATH so
# PyInstaller finds the correct VC++ runtime DLLs, and then produces the
# packaged Windows executable from the spec file when available.
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$entryPath = Join-Path $scriptDir $EntryScript
$specPath = Join-Path $scriptDir "$OutputName.spec"
$system32 = Join-Path $env:WINDIR "System32"

if (-not (Test-Path $entryPath)) {
    throw "Entry script not found: $entryPath"
}

Write-Host "Installing or updating build dependencies..."
& $PythonExe -m pip install --upgrade pyinstaller rocksdict

# Keep Windows system DLLs ahead of any JDK bin directory so PyInstaller
# does not pick an outdated MSVCP140.dll during dependency analysis.
$pathEntries = @($system32)
foreach ($entry in ($env:PATH -split ';')) {
    if ([string]::IsNullOrWhiteSpace($entry)) {
        continue
    }
    if ($entry -ieq $system32) {
        continue
    }
    if ($entry -match '[\\/]Microsoft[\\/]jdk-[^\\/]+[\\/]bin$') {
        continue
    }
    $pathEntries += $entry
}
$env:PATH = ($pathEntries -join ';')

$pyiArgs = @("-m", "PyInstaller", "--noconfirm", "--clean")

if ((-not $Console) -and (Test-Path $specPath)) {
    Write-Host "Using spec file build to override bundled VC++ runtime DLLs..."
    $pyiArgs += $specPath
}
else {
    $pyiArgs += @(
        "--onefile",
        "--name", $OutputName
    )

    if (-not $Console) {
        $pyiArgs += "--windowed"
    }

    $pyiArgs += @(
        "--collect-all", "rocksdict",
        "--paths", $scriptDir,
        $entryPath
    )
}

Write-Host "Building EXE..."
Push-Location $scriptDir
try {
    & $PythonExe $pyiArgs
}
finally {
    Pop-Location
}

$distPath = Join-Path $scriptDir "dist\$OutputName.exe"
Write-Host "Build complete: $distPath"
