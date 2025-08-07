import os
import subprocess

def main():
    import time
    print(f'[DEBUG] Current working directory: {os.getcwd()}')
    # Adjust base_dir to point to the project root (Fusion), not Data/python
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    normalized_dir = os.path.join(base_dir, 'Data', 'LLY', 'Output', 'normalized')
    gridmetrics_dir = os.path.join(normalized_dir, 'gridmetrics')
    os.makedirs(gridmetrics_dir, exist_ok=True)
    gridmetrics_exe = os.path.join(base_dir, 'GridMetrics.exe')
    ground_model = '*'
    height_break = '0.0'
    cell_size = '15.0'

    las_files = [f for f in os.listdir(normalized_dir) if f.lower().endswith('.las')]
    if not las_files:
        print('No LAS files found in normalized directory.')
        return

    for las_file in las_files:
        time.sleep(1)
        stand_file_full_name = os.path.join(normalized_dir, las_file)
        stand_file_no_ext = os.path.splitext(las_file)[0]
        output_base_name = os.path.join(gridmetrics_dir, f'{stand_file_no_ext}_gridmetrics')
        # Use relative paths for all files
    # Use relative paths for all files (relative to the working directory)
    rel_gridmetrics_exe = os.path.relpath(gridmetrics_exe, start=os.getcwd())
    # If the executable is in the current working directory, prefix with .\ for PowerShell
    if not os.path.dirname(rel_gridmetrics_exe):
        rel_gridmetrics_exe = f'.\\{rel_gridmetrics_exe}'
    rel_output_base_name = os.path.relpath(output_base_name, start=os.getcwd())
    rel_stand_file_full_name = os.path.relpath(stand_file_full_name, start=os.getcwd())
    cmd_str = (
        f'& "{rel_gridmetrics_exe}" /raster:mean,cover,p90 /ascii /minht:0.0 /verbose {ground_model} {height_break} {cell_size} '
        f'"{rel_output_base_name}" "{rel_stand_file_full_name}"'
    )
    print('\n' + '=' * 60)
    print(f'[DEBUG] Preparing to run GridMetrics for: {las_file}')
    print(f'[DEBUG] GridMetrics executable: {rel_gridmetrics_exe}')
    print(f'[DEBUG] Ground model: {ground_model}')
    print(f'[DEBUG] Height break: {height_break}')
    print(f'[DEBUG] Cell size: {cell_size}')
    print(f'[DEBUG] Output base name: {rel_output_base_name}')
    print(f'[DEBUG] LAS file: {rel_stand_file_full_name}')
    print('-' * 60)
    print('[DEBUG] PowerShell command to be executed:')
    print(cmd_str)
    print('-' * 60)
    result = subprocess.run([
        'powershell',
        '-Command',
        cmd_str
    ], shell=True, capture_output=True, text=True)
    print('[DEBUG] STDOUT:')
    print(result.stdout[:500])
    print('[DEBUG] STDERR:')
    print(result.stderr)
    print('[DEBUG] Return code:', result.returncode)
    print('-' * 60)
    if result.returncode != 0:
        print(f'[ERROR] GridMetrics failed for {stand_file_full_name} with error code {result.returncode}')
    else:
        print(f'[SUCCESS] GridMetrics completed successfully for {stand_file_full_name}')
    print('=' * 60 + '\n')
    input('Press Enter to continue to the next file...')

if __name__ == '__main__':
    main()
