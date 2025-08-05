"""
Height profile calculation functionality for the LiDAR viewer.
This module provides the ProfileCalculator class for computing height statistics along a line.
"""

import numpy as np
from scipy.spatial import cKDTree


class ProfileCalculator:
    """Calculates height profiles along a line through point cloud data."""
    
    def __init__(self):
        """Initialize the profile calculator."""
        self.points = None
        self.line_start = None
        self.line_end = None
        
    def calculate_profile(self, points, start_point, end_point, num_samples=100, tolerance=1.0):
        """
        Calculate height profile along a line
        
        Args:
            points: Nx3 numpy array of LiDAR points (x, y, z)
            start_point: 3D start point of line
            end_point: 3D end point of line
            num_samples: Number of sample points along the line
            tolerance: Search radius around each sample point (meters)
            
        Returns:
            dict: Profile data with distances, heights, statistics
        """
        # Validate inputs
        if points is None or points.shape[0] == 0:
            raise ValueError("No points provided for profile calculation")
            
        if start_point is None or end_point is None:
            raise ValueError("Invalid start or end point")
            
        if np.array_equal(start_point, end_point):
            raise ValueError("Start and end points are identical")
            
        print(f"[INFO] Calculating profile with {points.shape[0]} points, {num_samples} samples, tolerance={tolerance}m")
        
        # Store parameters
        self.points = points
        self.line_start = np.array(start_point)
        self.line_end = np.array(end_point)
        
        # Generate sample points along the line
        line_points = self.interpolate_line_points(start_point, end_point, num_samples)
        
        # Build spatial index for efficient queries (2D for horizontal distance)
        print("[INFO] Building spatial index...")
        tree = cKDTree(points[:, :2])  # Only use X,Y for 2D distance
        
        profile_data = {
            'distances': [],
            'min_heights': [],
            'max_heights': [],
            'mean_heights': [],
            'std_heights': [],
            'point_counts': [],
            'line_start': start_point,
            'line_end': end_point,
            'total_length': np.linalg.norm(end_point - start_point)
        }
        
        # Calculate total line length
        line_length = np.linalg.norm(end_point - start_point)
        print(f"[INFO] Profile line length: {line_length:.2f} meters")
        
        # Process each sample point along the line
        for i, sample_point in enumerate(line_points):
            # Find nearby points within tolerance
            indices = tree.query_ball_point(sample_point[:2], tolerance)
            
            # Distance along line
            distance = (i / (num_samples - 1)) * line_length
            
            if len(indices) > 0:
                # Get heights of nearby points
                nearby_points = points[indices]
                heights = nearby_points[:, 2]  # Z values
                
                # Calculate statistics
                stats = self.calculate_height_statistics(heights)
                
                profile_data['distances'].append(distance)
                profile_data['min_heights'].append(stats['min'])
                profile_data['max_heights'].append(stats['max'])
                profile_data['mean_heights'].append(stats['mean'])
                profile_data['std_heights'].append(stats['std'])
                profile_data['point_counts'].append(len(heights))
                
            else:
                # No points found - use NaN for missing data
                profile_data['distances'].append(distance)
                profile_data['min_heights'].append(np.nan)
                profile_data['max_heights'].append(np.nan)
                profile_data['mean_heights'].append(np.nan)
                profile_data['std_heights'].append(np.nan)
                profile_data['point_counts'].append(0)
        
        # Convert lists to numpy arrays for easier processing
        for key in ['distances', 'min_heights', 'max_heights', 'mean_heights', 'std_heights', 'point_counts']:
            profile_data[key] = np.array(profile_data[key])
            
        # Post-process to handle missing data
        profile_data = self.interpolate_missing_data(profile_data)
        
        # Add summary statistics
        profile_data['summary'] = self.calculate_profile_summary(profile_data)
        
        print(f"[INFO] Profile calculation complete. {np.sum(~np.isnan(profile_data['mean_heights']))} valid samples")
        
        return profile_data
        
    def interpolate_line_points(self, start, end, num_samples):
        """Generate evenly spaced points along the line"""
        t = np.linspace(0, 1, num_samples)
        start = np.array(start)
        end = np.array(end)
        line_points = np.array([start + t_val * (end - start) for t_val in t])
        return line_points
        
    def calculate_height_statistics(self, heights):
        """Calculate min, max, mean, std dev of heights"""
        if len(heights) == 0:
            return {
                'min': np.nan,
                'max': np.nan,
                'mean': np.nan,
                'std': np.nan
            }
            
        return {
            'min': np.min(heights),
            'max': np.max(heights),
            'mean': np.mean(heights),
            'std': np.std(heights) if len(heights) > 1 else 0.0
        }
        
    def interpolate_missing_data(self, profile_data):
        """Interpolate missing data points using linear interpolation"""
        for key in ['min_heights', 'max_heights', 'mean_heights']:
            values = profile_data[key]
            
            # Find valid (non-NaN) indices
            valid_mask = ~np.isnan(values)
            
            if np.sum(valid_mask) < 2:
                # Not enough valid points for interpolation
                continue
                
            # Interpolate missing values
            valid_distances = profile_data['distances'][valid_mask]
            valid_values = values[valid_mask]
            
            # Only interpolate, don't extrapolate
            interpolated = np.interp(
                profile_data['distances'], 
                valid_distances, 
                valid_values,
                left=np.nan, 
                right=np.nan
            )
            
            # Update only the previously NaN values that are within interpolation range
            interp_mask = (profile_data['distances'] >= valid_distances[0]) & \
                         (profile_data['distances'] <= valid_distances[-1])
            
            profile_data[key] = np.where(
                np.isnan(values) & interp_mask, 
                interpolated, 
                values
            )
            
        return profile_data
        
    def calculate_profile_summary(self, profile_data):
        """Calculate summary statistics for the entire profile"""
        valid_mean = profile_data['mean_heights'][~np.isnan(profile_data['mean_heights'])]
        
        if len(valid_mean) == 0:
            return {
                'total_elevation_change': 0.0,
                'max_elevation': np.nan,
                'min_elevation': np.nan,
                'mean_elevation': np.nan,
                'elevation_range': 0.0,
                'valid_samples': 0,
                'coverage_percentage': 0.0
            }
            
        summary = {
            'total_elevation_change': abs(valid_mean[-1] - valid_mean[0]) if len(valid_mean) > 1 else 0.0,
            'max_elevation': np.nanmax(profile_data['max_heights']),
            'min_elevation': np.nanmin(profile_data['min_heights']),
            'mean_elevation': np.nanmean(valid_mean),
            'elevation_range': np.nanmax(profile_data['max_heights']) - np.nanmin(profile_data['min_heights']),
            'valid_samples': len(valid_mean),
            'coverage_percentage': (len(valid_mean) / len(profile_data['distances'])) * 100
        }
        
        return summary
        
    def point_to_line_distance_2d(self, point, line_start, line_end):
        """Calculate perpendicular distance from point to line segment in 2D"""
        line_vec = line_end[:2] - line_start[:2]
        point_vec = point[:2] - line_start[:2]
        
        line_len = np.linalg.norm(line_vec)
        if line_len == 0:
            return np.linalg.norm(point_vec)
        
        line_unitvec = line_vec / line_len
        proj_length = np.dot(point_vec, line_unitvec)
        proj_length = np.clip(proj_length, 0, line_len)
        proj_point = line_start[:2] + proj_length * line_unitvec
        
        return np.linalg.norm(point[:2] - proj_point)
        
    def get_cross_section_points(self, points, start_point, end_point, tolerance=1.0):
        """
        Get all points within tolerance distance of the line for detailed analysis
        
        Returns:
            dict: Cross-section data with points, distances along line, and perpendicular distances
        """
        if points is None or points.shape[0] == 0:
            return {'points': np.array([]), 'line_distances': np.array([]), 'perp_distances': np.array([])}
            
        line_start = np.array(start_point)
        line_end = np.array(end_point)
        
        # Calculate perpendicular distances for all points
        perp_distances = np.array([
            self.point_to_line_distance_2d(point, line_start, line_end) 
            for point in points
        ])
        
        # Filter points within tolerance
        within_tolerance = perp_distances <= tolerance
        cross_section_points = points[within_tolerance]
        perp_distances = perp_distances[within_tolerance]
        
        if len(cross_section_points) == 0:
            return {'points': np.array([]), 'line_distances': np.array([]), 'perp_distances': np.array([])}
        
        # Calculate distances along the line
        line_vec = line_end - line_start
        line_length = np.linalg.norm(line_vec)
        line_unitvec = line_vec / line_length if line_length > 0 else np.zeros(3)
        
        line_distances = np.array([
            np.dot(point - line_start, line_unitvec) 
            for point in cross_section_points
        ])
        
        return {
            'points': cross_section_points,
            'line_distances': line_distances,
            'perp_distances': perp_distances,
            'line_start': line_start,
            'line_end': line_end,
            'total_length': line_length
        }
