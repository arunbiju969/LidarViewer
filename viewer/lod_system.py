"""
Level-of-Detail (LOD) System for Point Cloud Rendering Optimization

This module provides intelligent point decimation based on camera distance,
dataset size, and user preferences to dramatically improve rendering performance
for large point cloud datasets.
"""

import numpy as np
from typing import Tuple, Optional, Dict, Any
import time

class LODSystem:
    """
    Level-of-Detail system for optimizing point cloud rendering performance.
    
    Features:
    - Distance-based point decimation
    - Adaptive sampling based on dataset size
    - Smooth transitions between detail levels
    - Performance monitoring and auto-adjustment
    """
    
    def __init__(self):
        self.enabled = True
        self.auto_mode = True
        
        # LOD thresholds (camera distance multipliers relative to scene size)
        self.distance_thresholds = {
            'far': 5.0,      # Very far: show every 20th point
            'medium': 2.0,   # Medium: show every 5th point  
            'near': 1.0,     # Near: show every 2nd point
            'close': 0.5     # Close: show all points
        }
        
        # Point decimation factors for each LOD level
        self.decimation_factors = {
            'far': 20,       # 1/20th of points (5% visible)
            'medium': 5,     # 1/5th of points (20% visible)
            'near': 2,       # 1/2 of points (50% visible)
            'close': 1       # All points (100% visible)
        }
        
        # Dataset size thresholds for automatic LOD activation
        self.size_thresholds = {
            'small': 50000,     # < 50K points: LOD optional
            'medium': 200000,   # 50K-200K: Light LOD
            'large': 500000,    # 200K-500K: Moderate LOD
            'massive': 1000000  # > 500K: Aggressive LOD
        }
        
        # Performance tracking
        self.performance_stats = {
            'last_render_time': 0.0,
            'average_render_time': 0.0,
            'render_count': 0,
            'auto_adjustments': 0
        }
        
        print("[LOD] Level-of-Detail system initialized")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the LOD system"""
        self.enabled = enabled
        print(f"[LOD] System {'enabled' if enabled else 'disabled'}")
    
    def set_auto_mode(self, auto: bool):
        """Enable or disable automatic LOD adjustment"""
        self.auto_mode = auto
        print(f"[LOD] Auto mode {'enabled' if auto else 'disabled'}")
    
    def calculate_scene_size(self, points: np.ndarray) -> float:
        """Calculate the approximate size of the scene for distance calculations"""
        if points is None or len(points) == 0:
            return 1.0
        
        try:
            # Calculate bounding box diagonal as scene size
            min_coords = np.min(points, axis=0)
            max_coords = np.max(points, axis=0)
            scene_size = np.linalg.norm(max_coords - min_coords)
            return max(scene_size, 1.0)  # Avoid division by zero
        except Exception as e:
            print(f"[LOD] Error calculating scene size: {e}")
            return 1.0
    
    def get_camera_distance(self, viewer) -> float:
        """Get the current camera distance from the scene center"""
        try:
            if not hasattr(viewer, 'plotter') or not hasattr(viewer.plotter, 'camera'):
                return 1.0
            
            camera = viewer.plotter.camera
            if camera is None:
                return 1.0
            
            # Get camera position and focal point
            camera_pos = np.array(camera.GetPosition())
            focal_point = np.array(camera.GetFocalPoint())
            
            # Calculate distance
            distance = np.linalg.norm(camera_pos - focal_point)
            return max(distance, 0.1)  # Avoid zero distance
            
        except Exception as e:
            print(f"[LOD] Error getting camera distance: {e}")
            return 1.0
    
    def determine_lod_level(self, points: np.ndarray, viewer, force_level: Optional[str] = None) -> str:
        """
        Determine the appropriate LOD level based on dataset size and camera distance.
        
        Args:
            points: The point cloud data
            viewer: The viewer instance for camera information
            force_level: Force a specific LOD level (for testing/manual override)
            
        Returns:
            str: LOD level ('close', 'near', 'medium', 'far')
        """
        if not self.enabled:
            return 'close'  # Full detail when LOD disabled
        
        if force_level:
            return force_level
        
        point_count = len(points) if points is not None else 0
        
        # For small datasets, always use full detail
        if point_count < self.size_thresholds['small']:
            return 'close'
        
        # Get camera distance relative to scene size
        camera_distance = self.get_camera_distance(viewer)
        scene_size = self.calculate_scene_size(points)
        relative_distance = camera_distance / scene_size if scene_size > 0 else 1.0
        
        # Determine LOD level based on distance and dataset size
        if relative_distance > self.distance_thresholds['far']:
            return 'far'
        elif relative_distance > self.distance_thresholds['medium']:
            return 'medium'
        elif relative_distance > self.distance_thresholds['near']:
            return 'near'
        else:
            return 'close'
    
    def apply_lod(self, points: np.ndarray, scalars: Optional[np.ndarray], 
                  lod_level: str) -> Tuple[np.ndarray, Optional[np.ndarray], Dict[str, Any]]:
        """
        Apply Level-of-Detail decimation to point cloud data.
        
        Args:
            points: Original point cloud data (N, 3)
            scalars: Optional scalar values for coloring (N,)
            lod_level: LOD level to apply ('close', 'near', 'medium', 'far')
            
        Returns:
            Tuple of (decimated_points, decimated_scalars, lod_info)
        """
        start_time = time.time()
        
        if not self.enabled or points is None or len(points) == 0:
            return points, scalars, {'level': 'close', 'decimation': 1, 'original_count': len(points) if points is not None else 0}
        
        original_count = len(points)
        decimation_factor = self.decimation_factors.get(lod_level, 1)
        
        if decimation_factor <= 1:
            # No decimation needed
            lod_info = {
                'level': lod_level,
                'decimation': 1,
                'original_count': original_count,
                'final_count': original_count,
                'reduction_percent': 0.0,
                'processing_time': time.time() - start_time
            }
            return points, scalars, lod_info
        
        try:
            # Apply systematic decimation (every Nth point)
            # This preserves spatial distribution better than random sampling
            decimated_indices = np.arange(0, len(points), decimation_factor)
            decimated_points = points[decimated_indices]
            
            # Apply same decimation to scalars if provided
            decimated_scalars = None
            if scalars is not None:
                decimated_scalars = scalars[decimated_indices]
            
            final_count = len(decimated_points)
            reduction_percent = ((original_count - final_count) / original_count) * 100
            
            lod_info = {
                'level': lod_level,
                'decimation': decimation_factor,
                'original_count': original_count,
                'final_count': final_count,
                'reduction_percent': reduction_percent,
                'processing_time': time.time() - start_time
            }
            
            print(f"[LOD] Applied {lod_level} LOD: {original_count:,} → {final_count:,} points "
                  f"({reduction_percent:.1f}% reduction)")
            
            return decimated_points, decimated_scalars, lod_info
            
        except Exception as e:
            print(f"[LOD] Error applying LOD: {e}")
            # Return original data on error
            lod_info = {
                'level': 'error',
                'decimation': 1,
                'original_count': original_count,
                'final_count': original_count,
                'reduction_percent': 0.0,
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
            return points, scalars, lod_info
    
    def get_adaptive_decimation(self, point_count: int) -> int:
        """
        Get adaptive decimation factor based on dataset size.
        
        Args:
            point_count: Number of points in the dataset
            
        Returns:
            int: Recommended decimation factor
        """
        if point_count < self.size_thresholds['small']:
            return 1  # No decimation for small datasets
        elif point_count < self.size_thresholds['medium']:
            return 2  # Light decimation for medium datasets
        elif point_count < self.size_thresholds['large']:
            return 5  # Moderate decimation for large datasets
        else:
            return 10  # Aggressive decimation for massive datasets
    
    def update_performance_stats(self, render_time: float):
        """Update performance statistics for auto-adjustment"""
        self.performance_stats['last_render_time'] = render_time
        self.performance_stats['render_count'] += 1
        
        # Calculate rolling average
        if self.performance_stats['render_count'] == 1:
            self.performance_stats['average_render_time'] = render_time
        else:
            # Exponential moving average
            alpha = 0.1
            self.performance_stats['average_render_time'] = (
                alpha * render_time + 
                (1 - alpha) * self.performance_stats['average_render_time']
            )
    
    def should_auto_adjust(self) -> bool:
        """Determine if automatic LOD adjustment is needed based on performance"""
        if not self.auto_mode:
            return False
        
        # If average render time is too high, suggest more aggressive LOD
        target_render_time = 0.05  # 50ms target for smooth interaction
        return self.performance_stats['average_render_time'] > target_render_time
    
    def get_lod_summary(self) -> Dict[str, Any]:
        """Get a summary of current LOD system status"""
        return {
            'enabled': self.enabled,
            'auto_mode': self.auto_mode,
            'distance_thresholds': self.distance_thresholds,
            'decimation_factors': self.decimation_factors,
            'performance_stats': self.performance_stats.copy()
        }
    
    def configure_thresholds(self, distance_thresholds: Optional[Dict] = None, 
                           decimation_factors: Optional[Dict] = None):
        """
        Configure LOD thresholds and decimation factors.
        
        Args:
            distance_thresholds: Custom distance thresholds
            decimation_factors: Custom decimation factors
        """
        if distance_thresholds:
            self.distance_thresholds.update(distance_thresholds)
            print(f"[LOD] Updated distance thresholds: {self.distance_thresholds}")
        
        if decimation_factors:
            self.decimation_factors.update(decimation_factors)
            print(f"[LOD] Updated decimation factors: {self.decimation_factors}")


# Global LOD system instance
_lod_system = None

def get_lod_system() -> LODSystem:
    """Get the global LOD system instance"""
    global _lod_system
    if _lod_system is None:
        _lod_system = LODSystem()
    return _lod_system

def initialize_lod_system() -> LODSystem:
    """Initialize and return the LOD system"""
    global _lod_system
    _lod_system = LODSystem()
    return _lod_system
