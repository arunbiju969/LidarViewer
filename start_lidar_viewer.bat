@echo off
REM Batch file to start LiDAR Viewer with proper PROJ environment
REM This fixes PROJ database warnings by setting environment variables before Python starts

echo Starting LiDAR Viewer with PROJ database fix...

REM Get the conda environment path
set CONDA_ENV_PATH=C:\Users\W0491597\.conda\envs\lidarviewer

REM Set PROJ_LIB to conda environment's PROJ data directory
set PROJ_LIB=%CONDA_ENV_PATH%\Library\share\proj
echo [PROJ] Set PROJ_LIB to: %PROJ_LIB%

REM Add conda environment binaries to PATH (prioritize over system PATH)
set PATH=%CONDA_ENV_PATH%\Library\bin;%CONDA_ENV_PATH%\Scripts;%PATH%
echo [PROJ] Prioritized conda environment in PATH

REM Set additional PROJ environment variables to suppress warnings
set PROJ_DEBUG=OFF
set PROJ_NETWORK=OFF

REM Launch the LiDAR Viewer
echo [PROJ] Starting LiDAR Viewer...
"%CONDA_ENV_PATH%\python.exe" "%~dp0lidar_viewer.py"

REM Keep window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo [ERROR] LiDAR Viewer exited with error code %ERRORLEVEL%
    pause
)
