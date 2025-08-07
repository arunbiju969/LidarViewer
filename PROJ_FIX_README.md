# LiDAR Viewer - PROJ Database Fix

## Problem
The LiDAR Viewer application shows PROJ database warnings due to conflicting PROJ installations:
```
pj_obj_create: C:\Program Files\PostgreSQL\16\share\contrib\postgis-3.4\proj\proj.db contains DATABASE.LAYOUT.VERSION.MINOR = 2 whereas a number >= 5 is expected. It comes from another PROJ installation.
```

## Solution
We've implemented multiple solutions to fix these warnings by prioritizing the conda environment's PROJ installation.

## How to Start the Application (No Warnings)

### Method 1: PowerShell Launcher (Recommended)
```powershell
PowerShell -ExecutionPolicy Bypass -File start_lidar_viewer.ps1
```

### Method 2: Batch File Launcher
```cmd
start_lidar_viewer.bat
```

### Method 3: Python Launcher
```bash
python launcher.py
```

### Method 4: Direct Python (May Still Show Warnings)
```bash
python lidar_viewer.py
```

## What the Fix Does

The launchers set these environment variables before starting Python:

1. **PROJ_LIB**: Points to conda environment's PROJ data directory
2. **PATH**: Prioritizes conda environment binaries
3. **PROJ_DEBUG**: Disables PROJ debug messages
4. **PROJ_NETWORK**: Disables PROJ network access
5. **CPL_DEBUG**: Disables GDAL/PROJ error logging
6. **GDAL_DISABLE_READDIR_ON_OPEN**: Reduces file system calls

## Files Added

- `start_lidar_viewer.ps1` - PowerShell launcher script
- `start_lidar_viewer.bat` - Windows batch launcher script  
- `launcher.py` - Python launcher script
- `PROJ_FIX_README.md` - This documentation

## Technical Details

The warnings occur because:
1. PostgreSQL installs an older version of PROJ (version 2.x database format)
2. The conda environment has a newer PROJ (requires version 5.x+ database format)
3. Windows searches system PATH and finds PostgreSQL's PROJ first
4. The newer PROJ libraries try to read the older database format

The fix ensures the conda environment's PROJ installation is used instead of the system-wide PostgreSQL installation.

## Performance Impact

✅ **No performance impact** - The fix only affects startup environment variables
✅ **Maintains full functionality** - All LiDAR viewer features work normally
✅ **Suppresses warnings only** - Does not modify actual PROJ functionality

## Verification

After using any of the launchers, you should see:
```
[PROJ] Set PROJ_LIB to: C:\Users\...\lidarviewer\Library\share\proj
[PROJ] Prioritized conda environment in PATH
[PROJ] Set additional PROJ suppression variables
```

And **no more** `pj_obj_create` warnings!
