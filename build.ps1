<#
.SYNOPSIS
    REETA — Complete Desktop Application Build Pipeline
    Builds frontend (React/Vite), freezes backend (PyInstaller sidecar), and compiles native Tauri shell (Rust/MSVC).

.PARAMETER Mode
    Build mode: "release" (default, optimized) or "debug" (faster compile).

.PARAMETER SkipFrontend
    Skip building the Vite frontend bundle.

.PARAMETER SkipBackend
    Skip freezing the FastAPI backend sidecar.

.PARAMETER SkipShell
    Skip compiling the Tauri Rust desktop shell.
#>

[CmdletBinding()]
param(
    [ValidateSet("release", "debug")]
    [string]$Mode = "release",
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipShell
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "      REETA — Standalone Windows Desktop Application Build       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Build Mode: $Mode" -ForegroundColor Yellow
Write-Host "Root Directory: $ScriptDir" -ForegroundColor Gray
Write-Host ""

# -----------------------------------------------------------------------------
# 0. Environment Setup (MSVC & Windows SDK)
# -----------------------------------------------------------------------------
Write-Host "[0/3] Configuring MSVC and Windows SDK environment..." -ForegroundColor Green

$xwinUnpack = Join-Path $ScriptDir ".xwin-cache\unpack"
if (Test-Path $xwinUnpack) {
    $incUm = Join-Path $xwinUnpack "Win11SDK_10.0.26100_store_headers.msi\include\um"
    $incShared = Join-Path $xwinUnpack "Win11SDK_10.0.26100_store_headers_onecoreuap.msi\include\shared"
    $incUcrt = Join-Path $xwinUnpack "ucrt.msi\include\ucrt"
    $incMsvc = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\include"

    $env:INCLUDE = "$incUm;$incShared;$incUcrt;$incMsvc;$env:INCLUDE"
    $vsBin = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64"
    if (Test-Path $vsBin) {
        $env:PATH = "$vsBin;$env:USERPROFILE\.cargo\bin;$env:PATH"
    }
    Write-Host "  -> Configured Windows 11 SDK headers and Visual Studio MSVC tools." -ForegroundColor Gray
}

$cargoBin = "$env:USERPROFILE\.cargo\bin\cargo.exe"
if (-not (Test-Path $cargoBin)) {
    $cargoBin = "cargo.exe"
}

$pythonExe = Join-Path $ScriptDir "backend\venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python.exe"
}

# -----------------------------------------------------------------------------
# 1. Frontend Web App Build (React + TypeScript + Vite + Tailwind)
# -----------------------------------------------------------------------------
if (-not $SkipFrontend) {
    Write-Host "`n[1/3] Building React Frontend UI (Vite)..." -ForegroundColor Green
    Push-Location (Join-Path $ScriptDir "desktop")
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed with exit code $LASTEXITCODE"
        }
        $distHtml = Join-Path $ScriptDir "desktop\dist\index.html"
        if (-not (Test-Path $distHtml)) {
            throw "Frontend build did not generate desktop\dist\index.html"
        }
        Write-Host "  -> Frontend build successful: $distHtml" -ForegroundColor Gray
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "`n[1/3] Skipping frontend build (-SkipFrontend specified)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 2. Backend Sidecar Freeze (PyInstaller)
# -----------------------------------------------------------------------------
if (-not $SkipBackend) {
    Write-Host "`n[2/3] Freezing FastAPI Backend Sidecar (PyInstaller)..." -ForegroundColor Green
    $specPath = Join-Path $ScriptDir "backend\reeta_backend.spec"
    if (-not (Test-Path $specPath)) {
        throw "Backend spec file not found: $specPath"
    }

    & $pythonExe -m PyInstaller --noconfirm --clean $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller backend freeze failed with exit code $LASTEXITCODE"
    }

    $frozenExe = Join-Path $ScriptDir "desktop\src-tauri\binaries\reeta-backend\reeta-backend.exe"
    if (-not (Test-Path $frozenExe)) {
        throw "Expected frozen binary not found: $frozenExe"
    }
    $sidecarSizeMb = [math]::Round((Get-Item $frozenExe).Length / 1MB, 2)
    Write-Host "  -> Backend sidecar frozen successfully ($sidecarSizeMb MB): $frozenExe" -ForegroundColor Gray
} else {
    Write-Host "`n[2/3] Skipping backend freeze (-SkipBackend specified)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# 3. Native Tauri Desktop Shell Build (Rust)
# -----------------------------------------------------------------------------
if (-not $SkipShell) {
    Write-Host "`n[3/3] Compiling Tauri Desktop Executable ($Mode)..." -ForegroundColor Green
    $tauriManifest = Join-Path $ScriptDir "desktop\src-tauri\Cargo.toml"

    $cargoArgs = @("build", "--manifest-path", $tauriManifest)
    if ($Mode -eq "release") {
        $cargoArgs += "--release"
    }

    & $cargoBin @cargoArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Cargo build failed with exit code $LASTEXITCODE"
    }

    $targetDir = Join-Path $ScriptDir "desktop\src-tauri\target\$Mode"
    $reetaExe = Join-Path $targetDir "REETA.exe"
    if (-not (Test-Path $reetaExe)) {
        throw "Compiled executable not found at: $reetaExe"
    }

    # Copy sidecar folder next to executable for direct portable launch
    $targetSidecarDir = Join-Path $targetDir "reeta-backend"
    $sourceSidecarDir = Join-Path $ScriptDir "desktop\src-tauri\binaries\reeta-backend"
    if (Test-Path $sourceSidecarDir) {
        Copy-Item -Path $sourceSidecarDir -Destination $targetDir -Recurse -Force
        Write-Host "  -> Bundled sidecar distribution into: $targetSidecarDir" -ForegroundColor Gray
    }

    $exeSizeMb = [math]::Round((Get-Item $reetaExe).Length / 1MB, 2)
    Write-Host "  -> Desktop binary compiled successfully ($exeSizeMb MB): $reetaExe" -ForegroundColor Gray
} else {
    Write-Host "`n[3/3] Skipping desktop shell compilation (-SkipShell specified)." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "                        BUILD COMPLETE                           " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
$finalExe = Join-Path $ScriptDir "desktop\src-tauri\target\$Mode\REETA.exe"
if (Test-Path $finalExe) {
    Write-Host "Executable: $finalExe" -ForegroundColor White
    Write-Host ""
    Write-Host "To launch REETA standalone:" -ForegroundColor Yellow
    Write-Host "  & `"$finalExe`"" -ForegroundColor White
}
Write-Host "=================================================================" -ForegroundColor Cyan

