import os
import numpy as np
import pdal
import tempfile
import json

def export_points_to_laz(points, output_path, original_las_data=None, point_indices=None, preserve_all_dimensions=True):
    """
    Export a subset of points to a LAZ file using PDAL.
    - If original_las_data is provided and contains a LAS/LAZ file path, use readers.las for full metadata/CRS preservation.
    - Otherwise, use basic export with just XYZ coordinates.
    """
    # Try to get the original LAS file path for metadata preservation
    las_file = None
    if original_las_data is not None:
        las = original_las_data.get('las', None)
        if las and hasattr(las, 'filename'):
            las_file = las.filename
        elif 'file_path' in original_las_data:
            las_file = original_las_data['file_path']
    
    if las_file and os.path.exists(las_file) and point_indices is not None:
        return _export_with_las_source(las_file, output_path, point_indices)
    else:
        return _export_from_points_array(points, output_path)

def _export_with_las_source(las_file, output_path, point_indices):
    """Export using original LAS file as source with point filtering"""
    try:
        # Convert point indices to a range filter format
        if len(point_indices) == 0:
            return False
            
        # For large number of indices, create a temporary text file with point indices
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as idx_file:
            for idx in point_indices:
                idx_file.write(f"{idx}\n")
            idx_file_path = idx_file.name
        
        try:
            # Create PDAL pipeline with filters.range using the index file
            pipeline_config = [
                {
                    "type": "readers.las",
                    "filename": las_file
                },
                {
                    "type": "filters.range",
                    "limits": f"Index[{':'.join(map(str, [min(point_indices), max(point_indices)]))}]"
                },
                {
                    "type": "writers.las",
                    "filename": output_path,
                    "forward": "all",
                    "compression": "true"
                }
            ]
            
            pipeline = pdal.Pipeline(json.dumps(pipeline_config))
            count = pipeline.execute()
            
            print(f"[INFO] Exported {count} points with metadata preservation")
            print(f"[INFO] Temporary file kept: {output_path}")
            return True
            
        finally:
            # Keep index file for debugging - don't clean up
            print(f"[INFO] Index file kept: {idx_file_path}")
            # try:
            #     os.remove(idx_file_path)
            # except:
            #     pass
                
    except Exception as e:
        print(f"[ERROR] LAS source export failed: {e}")
        return False

def _export_from_points_array(points, output_path):
    """Export from numpy points array (basic XYZ only)"""
    try:
        # Create temporary text file with points in CSV format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
            # Write header
            txt_file.write("X,Y,Z\n")
            # Write points
            for point in points:
                txt_file.write(f"{point[0]:.6f},{point[1]:.6f},{point[2]:.6f}\n")
            txt_file_path = txt_file.name
        
        try:
            # Create PDAL pipeline to read text and write LAZ
            pipeline_config = [
                {
                    "type": "readers.text",
                    "filename": txt_file_path,
                    "header": "X,Y,Z"
                },
                {
                    "type": "writers.las",
                    "filename": output_path,
                    "compression": "true"
                }
            ]
            
            pipeline = pdal.Pipeline(json.dumps(pipeline_config))
            count = pipeline.execute()
            
            print(f"[INFO] Exported {count} points (XYZ only)")
            print(f"[INFO] Temporary text file kept: {txt_file_path}")
            return True
            
        finally:
            # Keep text file for debugging - don't clean up
            print(f"[INFO] Text file kept: {txt_file_path}")
            # try:
            #     os.remove(txt_file_path)
            # except:
            #     pass
                
    except Exception as e:
        print(f"[ERROR] Points array export failed: {e}")
        return False

def create_temp_laz_file(points, original_las_data=None, point_indices=None, prefix="temp"):
    """Create a temporary LAZ file with the given points"""
    try:
        temp_dir = tempfile.gettempdir()
        temp_filename = f"{prefix}_{int(np.random.rand() * 1000000)}.laz"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        success = export_points_to_laz(points, temp_path, original_las_data, point_indices)
        
        if success:
            return temp_path
        else:
            return None
            
    except Exception as e:
        print(f"[ERROR] Failed to create temporary LAZ file: {e}")
        return None

def find_original_point_indices(subset_points, original_points, tolerance=1e-6):
    """Find indices of subset points in the original point cloud"""
    try:
        indices = []
        for subset_point in subset_points:
            # Find closest point in original data
            distances = np.sqrt(np.sum((original_points - subset_point) ** 2, axis=1))
            closest_idx = np.argmin(distances)
            
            if distances[closest_idx] < tolerance:
                indices.append(closest_idx)
        
        return np.array(indices, dtype=int)
        
    except Exception as e:
        print(f"[ERROR] Failed to find point indices: {e}")
        return np.array([], dtype=int)
