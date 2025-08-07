# PowerShell script to start LiDAR Viewer with proper PROJ environment
# This fixes PROJ database warnings by setting environment variables before Python starts

Write-Host "Starting LiDAR Viewer with PROJ database fix..." -ForegroundColor Green

# Get the conda environment path
$condaEnvPath = "C:\Users\W0491597\.conda\envs\lidarviewer"

# Set PROJ_LIB to conda environment's PROJ data directory
$projLib = Join-Path $condaEnvPath "Library\share\proj"
$env:PROJ_LIB = $projLib
Write-Host "[PROJ] Set PROJ_LIB to: $projLib" -ForegroundColor Yellow

# Add conda environment binaries to PATH (prioritize over system PATH)
$condaBin = Join-Path $condaEnvPath "Library\bin"
$condaScripts = Join-Path $condaEnvPath "Scripts"
$env:PATH = "$condaBin;$condaScripts;$env:PATH"
Write-Host "[PROJ] Prioritized conda environment in PATH" -ForegroundColor Yellow

# Set additional PROJ environment variables to suppress warnings
$env:PROJ_DEBUG = "OFF"
$env:PROJ_NETWORK = "OFF"
$env:CPL_DEBUG = "OFF"
$env:GDAL_DISABLE_READDIR_ON_OPEN = "TRUE"

# Launch the LiDAR Viewer
Write-Host "[PROJ] Starting LiDAR Viewer..." -ForegroundColor Green
$pythonExe = Join-Path $condaEnvPath "python.exe"
$scriptPath = Join-Path $PSScriptRoot "lidar_viewer.py"

try {
    & $pythonExe $scriptPath
} catch {
    Write-Host "[ERROR] LiDAR Viewer failed to start: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
