def load_point_cloud_data(file_path, chunk_size=100000):
    """
    Loads a LAS/LAZ file and returns a dict with:
      - las: dict of arrays for all dimensions
      - points: Nx3 numpy array of XYZ
      - cloud: pyvista.PolyData object
      - dims: list of dimension names
    """
    import pyvista as pv
    import numpy as np
    las, dims = load_las_file(file_path, chunk_size=chunk_size)
    points = np.vstack((las["X"], las["Y"], las["Z"])) .transpose()
    cloud = pv.PolyData(points)
    return {
        "las": las,
        "points": points,
        "cloud": cloud,
        "dims": dims
    }
def get_normalized_scalars(las_data, dim_name):
    """
    Given a LAS data dict and a dimension name, return a normalized array for color mapping.
    If the dimension is not numeric or normalization is not possible, return the raw array.
    """
    import numpy as np
    if las_data is None or dim_name not in las_data:
        return None
    scalars = las_data[dim_name]
    if np.issubdtype(scalars.dtype, np.number):
        min_val = np.min(scalars)
        max_val = np.max(scalars)
        if max_val > min_val:
            return (scalars - min_val) / (max_val - min_val)
        else:
            return scalars
    else:
        return scalars
def load_default_las_with_progress(settings_path, progress_bar):
    las_data = None
    default_file = None
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
            default_file = settings.get("last_file", None)
            if default_file and os.path.exists(default_file):
                import json as _json
                chunk_size = 100000
                pipeline = {
                    "pipeline": [
                        {"type": "readers.las", "filename": default_file},
                        {"type": "filters.chipper", "capacity": chunk_size}
                    ]
                }
                p = pdal.Pipeline(_json.dumps(pipeline))
                p.execute()
                arrays = p.arrays
                total_points = sum(arr.shape[0] for arr in arrays)
                loaded = 0
                # Concatenate all arrays for each dimension
                if arrays:
                    dims = arrays[0].dtype.names
                    las_data = {d: np.concatenate([arr[d] for arr in arrays]) for d in dims}
                    for arr in arrays:
                        loaded += arr.shape[0]
                        progress = int(loaded / total_points * 100)
                        progress_bar.setValue(progress)
                    print(f"[LOADER] Available dimensions in '{default_file}': {list(dims)}")
                    progress_bar.setValue(100)
                    return (las_data, list(dims)), default_file
                else:
                    print(f"[LOADER] No arrays found in file: {default_file}")
                    return (None, []), default_file
        except Exception as e:
            print(f"[LOADER] Error loading default LAS: {e}")
            las_data = None
    return (las_data, []), default_file
import os
import json
import numpy as np
import pdal

def load_las_file(file_path, chunk_size=100000):
    import json as _json
    pipeline = {
        "pipeline": [
            {"type": "readers.las", "filename": file_path},
            {"type": "filters.chipper", "capacity": chunk_size}
        ]
    }
    p = pdal.Pipeline(_json.dumps(pipeline))
    p.execute()
    arrays = p.arrays
    # Collect all field names from all arrays (should be the same for all)
    all_fields = set()
    for arr in arrays:
        all_fields.update(arr.dtype.names)
    all_fields = sorted(all_fields)
    # Prepare storage for each field
    field_data = {field: [] for field in all_fields}
    for arr in arrays:
        for field in all_fields:
            if field in arr.dtype.names:
                # Convert to float if needed for compatibility
                field_data[field].append(arr[field] * arr[field].dtype.type(1.0))
    # Concatenate arrays for each field
    for field in all_fields:
        field_data[field] = np.concatenate(field_data[field])
    print(f"[LOADER] Available dimensions in '{file_path}': {list(all_fields)}")
    return field_data, list(all_fields)

def save_last_file(settings_file, file_path):
    try:
        with open(settings_file, "w") as f:
            json.dump({"last_file": file_path}, f)
    except Exception:
        pass

def load_last_file(settings_file):
    try:
        if os.path.exists(settings_file):
            with open(settings_file, "r") as f:
                data = json.load(f)
                return data.get("last_file", None)
    except Exception:
        pass
    return None

def print_las_dimensions(file_path, chunk_size=100000):
    import json as _json
    pipeline = {
        "pipeline": [
            {"type": "readers.las", "filename": file_path},
            {"type": "filters.chipper", "capacity": chunk_size}
        ]
    }
    p = pdal.Pipeline(_json.dumps(pipeline))
    p.execute()
    arrays = p.arrays
    if not arrays:
        print(f"[LOADER] No data arrays returned for '{file_path}'.")
        return []
    # Use dtype.names from the first array (should be the same for all)
    dims = arrays[0].dtype.names
    print(f"[LOADER] Available dimensions in '{file_path}': {list(dims)}")
    return list(dims)

def get_las_metadata_summary(file_path):
    import pdal
    import json
    pipeline_json = {
        "pipeline": [
            {
                "type": "readers.las",
                "filename": file_path
            }
        ]
    }
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()
    metadata = pipeline.metadata  # Already a dict in recent pdal
    log = pipeline.log
    # Access schema information robustly
    readers_las = metadata.get('metadata', {}).get('readers.las', {})
    schema = readers_las.get('schema')
    lines = []
    schema_found = False
    if schema and 'dimensions' in schema:
        lines.append("[PDAL] LAS Schema Dimensions:")
        for dim in schema['dimensions']:
            lines.append(f"  Name: {dim.get('name')}, Type: {dim.get('type')}, Size: {dim.get('size')}")
        schema_found = True
    else:
        lines.append("[PDAL] No schema/dimensions found in metadata.")

    # Access statistics robustly
    stats_found = False
    stats = readers_las.get('stats')
    if stats:
        if 'statistic' in stats:
            lines.append("[PDAL] LAS Dimension Statistics:")
            for stat in stats['statistic']:
                lines.append(f"  Dimension: {stat.get('name')}, Min: {stat.get('minimum')}, Max: {stat.get('maximum')}, Average: {stat.get('average')}")
            stats_found = True
        if 'bbox' in stats and 'native' in stats['bbox']:
            bbox = stats['bbox']['native']
            lines.append(f"[PDAL] Bounding Box: MinX={bbox.get('minx')}, MinY={bbox.get('miny')}, MinZ={bbox.get('minz')}, MaxX={bbox.get('maxx')}, MaxY={bbox.get('maxy')}, MaxZ={bbox.get('maxz')}")
            stats_found = True
        else:
            lines.append("[PDAL] No bounding box found in statistics.")
    else:
        lines.append("[PDAL] No statistics found in metadata.")

    # If neither schema nor stats found, print the full metadata for user inspection
    if not schema_found and not stats_found:
        lines.append("[PDAL] Full available metadata:")
        lines.append(json.dumps(metadata, indent=2))
    return "\n".join(lines)

def main():
    import sys
    if len(sys.argv) > 1:
        print_las_dimensions(sys.argv[1])
    else:
        print("Usage: python las_loader.py <path-to-las-file>")

if __name__ == "__main__":
    main()
