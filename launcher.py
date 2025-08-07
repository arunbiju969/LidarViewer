#!/usr/bin/env python3
"""
LiDAR Viewer Launcher with PROJ Database Fix
============================================

This launcher script sets up the proper environment variables to fix PROJ database
warnings before starting the main LiDAR Viewer application.

Usage:
    python launcher.py
"""

import os
import sys
import subprocess

def setup_proj_environment():
    """Set up PROJ environment variables to avoid database warnings"""
    
    print("[LAUNCHER] Setting up PROJ environment...")
    
    # Get conda environment path
    conda_env = os.environ.get('CONDA_PREFIX', '')
    if not conda_env:
        # Try to detect conda environment from Python executable path
        python_path = sys.executable
        if 'envs' in python_path and 'lidarviewer' in python_path:
            conda_env = os.path.dirname(os.path.dirname(python_path))
    
    if conda_env:
        # Set PROJ_LIB to conda environment's PROJ data directory
        proj_data_dir = os.path.join(conda_env, 'Library', 'share', 'proj')
        if os.path.exists(proj_data_dir):
            os.environ['PROJ_LIB'] = proj_data_dir
            print(f"[LAUNCHER] Set PROJ_LIB to: {proj_data_dir}")
        
        # Prioritize conda environment binaries in PATH
        conda_bin = os.path.join(conda_env, 'Library', 'bin')
        if os.path.exists(conda_bin):
            current_path = os.environ.get('PATH', '')
            if conda_bin not in current_path.split(os.pathsep):
                os.environ['PATH'] = conda_bin + os.pathsep + current_path
                print(f"[LAUNCHER] Prioritized conda binaries: {conda_bin}")
    
    # Set additional environment variables to suppress PROJ warnings
    os.environ['PROJ_DEBUG'] = 'OFF'
    os.environ['PROJ_NETWORK'] = 'OFF'
    os.environ['CPL_DEBUG'] = 'OFF'
    os.environ['GDAL_DISABLE_READDIR_ON_OPEN'] = 'TRUE'
    
    print("[LAUNCHER] PROJ environment configured")

def main():
    """Main launcher function"""
    print("LiDAR Viewer Launcher")
    print("====================")
    
    # Set up PROJ environment
    setup_proj_environment()
    
    # Get the directory containing this launcher script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the main LiDAR viewer script
    main_script = os.path.join(script_dir, 'lidar_viewer.py')
    
    if not os.path.exists(main_script):
        print(f"[ERROR] Main script not found: {main_script}")
        sys.exit(1)
    
    print(f"[LAUNCHER] Starting LiDAR Viewer: {main_script}")
    
    try:
        # Launch the main application
        # Use exec to replace the current process (no subprocess overhead)
        import runpy
        sys.argv[0] = main_script  # Set the script name for the main app
        runpy.run_path(main_script, run_name='__main__')
        
    except Exception as e:
        print(f"[ERROR] Failed to start LiDAR Viewer: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
