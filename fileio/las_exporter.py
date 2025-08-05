"""
LAZ/LAS file export functionality with CRS and dimension preservation.
"""

import numpy as np
import os
import tempfile
from typing import Optional, Dict, Any

try:
    import laspy
    LASPY_AVAILABLE = True
except ImportError:
    LASPY_AVAILABLE = False


def export_points_to_laz(points: np.ndarray, 
                        output_path: str,
                        original_las: Optional[Any] = None,
                        point_indices: Optional[np.ndarray] = None,
                        preserve_all_dimensions: bool = True) -> bool:
    """
    Export points to LAZ file with full dimension and CRS preservation.
    
    Args:
        points: Nx3 numpy array of points (x, y, z)
        output_path: Output file path
        original_las: Original LAS data for copying dimensions and CRS
        point_indices: Indices of original points (for dimension copying)
        preserve_all_dimensions: Whether to preserve all original dimensions
        
    Returns:
        bool: Success status
    """
    if not LASPY_AVAILABLE:
        print("[ERROR] laspy not available for LAZ export")
        return False
        
    try:
        # Handle case where original_las might be a dict (from layer manager)
        if original_las is not None and isinstance(original_las, dict):
            print("[INFO] Converting dict format LAS data to laspy object")
            # Try to get the actual laspy object from the dict
            if 'las' in original_las:
                original_las = original_las['las']
            else:
                print("[WARN] Dict format LAS data doesn't contain 'las' key, using basic export")
                original_las = None
        
        if original_las and hasattr(original_las, 'header') and preserve_all_dimensions:
            # Create new LAS file based on original header
            header = laspy.LasHeader(
                point_format=original_las.header.point_format,
                version=original_las.header.version
            )
            
            # Copy header properties
            header.offsets = original_las.header.offsets
            header.scales = original_las.header.scales
            
            # Copy CRS information if available
            if hasattr(original_las.header, 'crs') and original_las.header.crs:
                header.crs = original_las.header.crs
                print(f"[INFO] Preserved CRS: {original_las.header.crs}")
            
            # Copy other header attributes
            if hasattr(original_las.header, 'global_encoding'):
                header.global_encoding = original_las.header.global_encoding
            if hasattr(original_las.header, 'creation_date'):
                header.creation_date = original_las.header.creation_date
            if hasattr(original_las.header, 'generating_software'):
                header.generating_software = original_las.header.generating_software
            
            las_file = laspy.LasData(header)
            
            # Set coordinates
            las_file.x = points[:, 0]
            las_file.y = points[:, 1]
            las_file.z = points[:, 2]
            
            # Copy all other dimensions if point_indices provided
            if point_indices is not None:
                dimensions_copied = []
                for dim_name in original_las.point_format.dimension_names:
                    if dim_name not in ['X', 'Y', 'Z']:
                        try:
                            original_data = getattr(original_las, dim_name.lower())
                            if len(original_data) > max(point_indices):
                                setattr(las_file, dim_name.lower(), original_data[point_indices])
                                dimensions_copied.append(dim_name)
                            else:
                                print(f"[WARN] Dimension {dim_name} index out of range")
                        except Exception as e:
                            print(f"[WARN] Could not copy dimension {dim_name}: {e}")
                
                print(f"[INFO] Copied dimensions: {dimensions_copied}")
            
            # Set point count
            header.point_count = len(points)
            
        else:
            # Create basic LAS file
            print("[INFO] Creating basic LAS file (no original header available)")
            header = laspy.LasHeader(point_format=3, version="1.2")
            las_file = laspy.LasData(header)
            las_file.x = points[:, 0]
            las_file.y = points[:, 1]
            las_file.z = points[:, 2]
            
            # Set basic intensity if we have enough dimensions
            if points.shape[1] > 3:
                las_file.intensity = np.ones(len(points), dtype=np.uint16) * 1000
            
        # Update header bounds
        header.min = [float(np.min(points[:, i])) for i in range(3)]
        header.max = [float(np.max(points[:, i])) for i in range(3)]
        
        # Write the file
        las_file.write(output_path)
        print(f"[INFO] LAZ file exported: {output_path} ({len(points)} points)")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to export LAZ file: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_temp_laz_file(points: np.ndarray, 
                        original_las: Optional[Any] = None,
                        point_indices: Optional[np.ndarray] = None,
                        prefix: str = "temp_export") -> Optional[str]:
    """
    Create temporary LAZ file for cross-section or filtered data.
    
    Args:
        points: Nx3 numpy array of points
        original_las: Original LAS data for copying metadata
        point_indices: Indices of original points
        prefix: Filename prefix
        
    Returns:
        str: Temporary file path or None if failed
    """
    try:
        # Create temporary file
        temp_dir = tempfile.gettempdir()
        temp_filename = f"{prefix}_{int(np.random.rand() * 1000000)}.laz"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        success = export_points_to_laz(
            points, temp_path, original_las, point_indices, preserve_all_dimensions=True
        )
        
        return temp_path if success else None
        
    except Exception as e:
        print(f"[ERROR] Failed to create temporary LAZ file: {e}")
        return None


def find_original_point_indices(subset_points: np.ndarray, 
                               original_points: np.ndarray,
                               tolerance: float = 0.001) -> np.ndarray:
    """
    Find indices of subset points in original point cloud.
    
    Args:
        subset_points: Subset of points to match
        original_points: Original full point cloud
        tolerance: Distance tolerance for matching
        
    Returns:
        np.ndarray: Array of indices in original_points
    """
    from scipy.spatial import cKDTree
    
    # Build spatial index for original points
    tree = cKDTree(original_points)
    
    indices = []
    for point in subset_points:
        distances, idx = tree.query(point, k=1)
        if distances <= tolerance:
            indices.append(idx)
        else:
            # Use closest point if no exact match
            indices.append(idx)
            
    return np.array(indices)


def get_las_metadata_for_export(original_las: Any) -> Dict[str, Any]:
    """
    Extract metadata from original LAS file for export preservation.
    
    Args:
        original_las: Original LAS data
        
    Returns:
        dict: Metadata dictionary
    """
    metadata = {}
    
    if hasattr(original_las, 'header'):
        header = original_las.header
        
        metadata['point_format'] = header.point_format
        metadata['version'] = header.version
        metadata['offsets'] = header.offsets
        metadata['scales'] = header.scales
        
        if hasattr(header, 'crs'):
            metadata['crs'] = header.crs
        if hasattr(header, 'global_encoding'):
            metadata['global_encoding'] = header.global_encoding
        if hasattr(header, 'creation_date'):
            metadata['creation_date'] = header.creation_date
        if hasattr(header, 'generating_software'):
            metadata['generating_software'] = header.generating_software
        
        metadata['dimensions'] = list(original_las.point_format.dimension_names)
        
    return metadata
