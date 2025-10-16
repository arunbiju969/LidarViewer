from typing import Optional

import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QWidget, QHBoxLayout
from .plotter_update_manager import PlotterUpdateManager
from .lod_system import get_lod_system
import time
import numpy as np

class PointCloudViewer(QWidget):
    def set_back_view(self):
        """Set the camera to the back view (opposite of front view, using bounds)."""
        if hasattr(self, 'plotter') and hasattr(self.plotter, 'camera'):
            bounds = None
            if hasattr(self.plotter, 'bounds') and self.plotter.bounds is not None:
                bounds = self.plotter.bounds
            elif hasattr(self, 'last_bounds'):
                bounds = self.last_bounds
            if bounds and all(b is not None for b in bounds):
                xmin, xmax, ymin, ymax, zmin, zmax = bounds
                center = [0.5 * (xmin + xmax), 0.5 * (ymin + ymax), 0.5 * (zmin + zmax)]
                dist = max(xmax - xmin, ymax - ymin, zmax - zmin) * 2
                # For back view, move camera in +Y direction (opposite of front)
                position = [center[0], center[1] + dist, center[2]]
                self.plotter.camera.SetPosition(*position)
                self.plotter.camera.SetFocalPoint(*center)
                self.plotter.camera.SetViewUp(0, 0, 1)
                self.plotter.reset_camera()
                self.update_manager.request_update()
            else:
                print("[WARN] set_back_view: Could not determine bounds for camera positioning.")
        else:
            print("[WARN] set_back_view: plotter or camera not available.")
    def set_point_size(self, size, actor=None):
        self._point_size = size
        if actor is not None:
            try:
                actor.GetProperty().SetPointSize(size)
                print(f"[DEBUG] Updated actor id={id(actor)} point size to: {size}")
            except Exception as e:
                print(f"[ERROR] Failed to set point size for actor {actor}: {e}")
        else:
            # Fallback: update all actors (legacy behavior, should be avoided)
            actors = getattr(self.plotter.renderer, 'actors', {})
            if hasattr(actors, 'values'):
                for a in actors.values():
                    try:
                        a.GetProperty().SetPointSize(size)
                        print(f"[DEBUG] Updated actor id={id(a)} point size to: {size}")
                    except Exception as e:
                        print(f"[ERROR] Failed to set point size for actor {a}: {e}")
            else:
                print("[WARN] No actors found in plotter renderer to update point size.")
        self.update_manager.request_update()
    def set_theme(self, theme):
        """Set plotter background and default colormap based on theme."""
        self._theme = theme
        if theme == "Dark":
            self.plotter.set_background("#232629")
            self._colormap = "plasma"
        else:
            self.plotter.set_background("white")
            self._colormap = "viridis"
        self.update_manager.request_update()

    def set_top_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, 0, 1)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 1, 0)
            self.plotter.reset_camera()
            self.update_manager.request_update()

    def set_front_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, -1, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.update_manager.request_update()

    def set_left_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(-1, 0, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.update_manager.request_update()

    def set_right_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(1, 0, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.update_manager.request_update()

    def set_bottom_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, 0, -1)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 1, 0)
            self.plotter.reset_camera()
            self.update_manager.request_update()
    def __init__(self, parent=None):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton
        super().__init__(parent)
        self.plotter = QtInteractor(self)  # type: ignore[arg-type]
        self.plotter.add_axes()
        layout = QHBoxLayout()
        layout.addWidget(self.plotter)
        self.setLayout(layout)
        self._colormap = "viridis"
        self._point_size = 3
        self._performance_mode = "auto"  # "auto", "performance", "quality"
        self._large_dataset_threshold = 100000  # Points threshold for auto mode
        self.last_bounds = None
        
        # Initialize update manager for optimized plotter updates
        self.update_manager = PlotterUpdateManager(self.plotter)
        
        # Initialize LOD system
        self.lod_system = get_lod_system()
        print("[PERFORMANCE] LOD system initialized for point cloud viewer")

    def set_performance_mode(self, mode="auto"):
        """
        Set rendering performance mode.
        
        Args:
            mode (str): "auto", "performance", or "quality"
                - "auto": Smart mode based on dataset size
                - "performance": Fast rendering (no spheres, optimized for large datasets)
                - "quality": High-quality rendering (spheres, best visual quality)
        """
        self._performance_mode = mode
        print(f"[PERFORMANCE] Set performance mode to: {mode}")
        
        # Configure LOD system based on performance mode
        if mode == "performance":
            # Aggressive LOD for maximum performance
            self.lod_system.configure_thresholds(
                distance_thresholds={'far': 3.0, 'medium': 1.5, 'near': 0.8, 'close': 0.3},
                decimation_factors={'far': 25, 'medium': 10, 'near': 3, 'close': 1}
            )
        elif mode == "quality":
            # Conservative LOD to maintain quality
            self.lod_system.configure_thresholds(
                distance_thresholds={'far': 8.0, 'medium': 4.0, 'near': 2.0, 'close': 1.0},
                decimation_factors={'far': 10, 'medium': 3, 'near': 2, 'close': 1}
            )
        else:  # "auto" mode - balanced settings
            # Reset to default balanced settings
            self.lod_system.configure_thresholds(
                distance_thresholds={'far': 5.0, 'medium': 2.0, 'near': 1.0, 'close': 0.5},
                decimation_factors={'far': 20, 'medium': 5, 'near': 2, 'close': 1}
            )
    
    def set_lod_enabled(self, enabled: bool):
        """Enable or disable the LOD system"""
        self.lod_system.set_enabled(enabled)
        print(f"[PERFORMANCE] LOD system {'enabled' if enabled else 'disabled'}")
    
    def get_lod_status(self) -> dict:
        """Get current LOD system status and performance statistics"""
        return self.lod_system.get_lod_summary()
    
    def force_lod_level(self, level: Optional[str] = None):
        """
        Force a specific LOD level for testing or manual control.
        
        Args:
            level (str): 'close', 'near', 'medium', 'far', or None for auto
        """
        if level:
            print(f"[PERFORMANCE] Forcing LOD level to: {level}")
            # This would require modification of the LOD system to support forced levels
            # For now, we'll just log the request
        else:
            print("[PERFORMANCE] LOD level set to automatic")
    
    def _should_use_spheres(self, point_count):
        """
        Determine whether to use spherical rendering based on performance mode and dataset size.
        
        Args:
            point_count (int): Number of points in the dataset
            
        Returns:
            bool: True if spheres should be used, False for flat point rendering
        """
        if self._performance_mode == "quality":
            return True
        elif self._performance_mode == "performance":
            return False
        else:  # "auto" mode
            # Use spheres only for small datasets
            use_spheres = point_count < self._large_dataset_threshold
            if not use_spheres:
                print(f"[PERFORMANCE] Large dataset detected ({point_count:,} points) - using flat point rendering for better performance")
            return use_spheres

    def display_point_cloud(self, points, scalars=None, cmap=None, return_actor=False, show_scalar_bar=False, return_lod_info=False):
        print(f"[DEBUG] display_point_cloud called: points.shape={getattr(points, 'shape', None)}, return_actor={return_actor}, show_scalar_bar={show_scalar_bar}")
        
        # Performance optimization: determine rendering mode based on dataset size
        point_count = len(points) if points is not None else 0
        use_spheres = self._should_use_spheres(point_count)
        
        # Apply LOD (Level-of-Detail) processing for performance optimization
        start_time = time.time()
        lod_level = self.lod_system.determine_lod_level(points, self)
        lod_points, lod_scalars, lod_info = self.lod_system.apply_lod(points, scalars, lod_level)
        
        # Log LOD performance information
        if lod_info['decimation'] > 1:
            print(f"[PERFORMANCE] LOD {lod_level}: {lod_info['original_count']:,} → {lod_info['final_count']:,} points "
                  f"({lod_info['reduction_percent']:.1f}% reduction, {lod_info['processing_time']*1000:.1f}ms)")
        
        scalar_bar_args = {}
        # Set scalar bar text color based on theme
        if hasattr(self, '_theme') and self._theme == "Dark":
            scalar_bar_args['color'] = 'white'
        else:
            scalar_bar_args['color'] = 'black'
        point_size = getattr(self, '_point_size', 3)
        actor = None
        
        # Use LOD-processed points and scalars for rendering
        render_points = lod_points
        render_scalars = lod_scalars
        
        scalars_array = None
        direct_color_scalars = False
        if render_scalars is not None:
            try:
                scalars_array = np.asarray(render_scalars)
                direct_color_scalars = scalars_array.ndim == 2 and scalars_array.shape[1] in (3, 4)
            except Exception:
                scalars_array = render_scalars
                direct_color_scalars = False

        if scalars_array is not None:
            if direct_color_scalars:
                actor = self.plotter.add_points(
                    render_points,
                    scalars=scalars_array,
                    render_points_as_spheres=use_spheres,
                    point_size=point_size,
                    show_scalar_bar=False,
                    pickable=True
                )
            else:
                used_cmap = cmap if cmap is not None else self._colormap
                actor = self.plotter.add_points(
                    render_points,
                    scalars=scalars_array,
                    cmap=used_cmap,
                    render_points_as_spheres=use_spheres,
                    point_size=point_size,
                    scalar_bar_args=scalar_bar_args,
                    show_scalar_bar=show_scalar_bar,
                    pickable=True
                )
        else:
            actor = self.plotter.add_points(
                render_points, 
                color="#3daee9", 
                render_points_as_spheres=use_spheres,  # Dynamic based on performance mode
                point_size=point_size, 
                pickable=True
            )
        
        # Update performance statistics
        render_time = time.time() - start_time
        self.lod_system.update_performance_stats(render_time)
        
        self.update_manager.request_update()
        
        # Return based on what's requested
        if return_lod_info and return_actor:
            return actor, lod_info
        elif return_lod_info:
            return lod_info
        elif return_actor:
            return actor
        else:
            return None
