"""
Line drawing functionality for height profile feature.
This module provides the LineDrawer class for interactive line drawing in the 3D viewer.
"""

import numpy as np
import pyvista as pv


class LineDrawer:
    """Handles interactive line drawing for height profile calculations."""
    
    def __init__(self, viewer):
        """Initialize the line drawer with a viewer reference.
        
        Args:
            viewer: The PointCloudViewer instance
        """
        self.viewer = viewer
        self.start_point = None
        self.end_point = None
        self.line_actor = None
        self.is_drawing = False
        self._picking_callback = None
        self.on_line_completed_callback = None
        
    def start_line_drawing(self):
        """Enable line drawing mode with two-click interaction"""
        print("[INFO] Starting line drawing mode")
        self.is_drawing = True
        self.start_point = None
        self.end_point = None
        self._enable_picking()
        
    def stop_line_drawing(self):
        """Disable line drawing mode"""
        print("[INFO] Stopping line drawing mode")
        self.is_drawing = False
        self._disable_picking()
        
    def clear_completed_line(self):
        """Clear any existing completed line from the viewer."""
        self.clear_line()
        
    def _enable_picking(self):
        """Enable point picking for line drawing"""
        try:
            self._picking_callback = self.viewer.plotter.enable_point_picking(
                callback=self._on_point_picked,
                left_clicking=True,
                show_message=False
            )
            print("[DEBUG] Point picking enabled for line drawing")
        except Exception as e:
            print(f"[ERROR] Failed to enable picking for line drawing: {e}")
        
    def _disable_picking(self):
        """Disable point picking"""
        try:
            if hasattr(self.viewer, 'plotter'):
                self.viewer.plotter.disable_picking()
                print("[DEBUG] Point picking disabled by LineDrawer")
        except Exception as e:
            print(f"[DEBUG] Could not disable picking in LineDrawer: {e}")
        
    def _on_point_picked(self, picked):
        """Handle point picking events"""
        if not self.is_drawing or picked is None:
            print("[DEBUG] Ignoring point pick - not in drawing mode or no points")
            return
            
        # Handle different types of picked data
        if isinstance(picked, np.ndarray):
            # Direct numpy array - use as point
            if picked.size == 0:
                print("[DEBUG] Ignoring point pick - empty array")
                return
            point = picked
        elif hasattr(picked, 'points') and hasattr(picked, 'n_points'):
            # PyVista object
            if picked.n_points == 0:
                print("[DEBUG] Ignoring point pick - no points in picked object")
                return
            point = picked.points[0]
        else:
            print(f"[DEBUG] Ignoring point pick - unknown picked type: {type(picked)}")
            return
            
        print(f"[DEBUG] Point picked: {point}")
        
        if self.start_point is None:
            self.on_first_click(point)
        else:
            self.on_second_click(point)
            
    def on_first_click(self, picked_point):
        """Store start point"""
        self.start_point = picked_point
        print(f"[INFO] Start point selected: {picked_point}")
        
    def on_second_click(self, picked_point):
        """Store end point, draw final line, trigger profile calculation"""
        self.end_point = picked_point
        print(f"[INFO] End point selected: {picked_point}")
        # Draw the line
        self.draw_line(self.start_point, self.end_point)
        # Trigger profile calculation (via callback to MainWindow)
        if hasattr(self, 'on_line_completed_callback') and self.on_line_completed_callback:
            self.on_line_completed_callback(self.start_point, self.end_point)
        
    def draw_line(self, start, end):
        """Create and display line actor in 3D viewer"""
        try:
            # Create line points
            line_points = np.array([start, end])
            line = pv.PolyData(line_points)
            
            # Create line cells
            cells = np.array([2, 0, 1])  # Line with 2 points, connecting points 0 and 1
            line.lines = cells
            
            # Add line to plotter
            self.line_actor = self.viewer.plotter.add_mesh(
                line, 
                color='yellow', 
                line_width=3, 
                name='profile_line',
                pickable=False
            )
            self.viewer.plotter.update()
            print("[INFO] Profile line drawn in 3D viewer")
            
        except Exception as e:
            print(f"[ERROR] Failed to draw line: {e}")
        
    def clear_line(self):
        """Remove line actor from viewer"""
        try:
            # Remove line actor
            if self.line_actor:
                self.viewer.plotter.remove_actor(self.line_actor)
                self.line_actor = None
                print("[DEBUG] Removed line actor")
            
            # Also try to remove by name (backup method)
            try:
                self.viewer.plotter.remove_actor('profile_line')
            except:
                pass
                    
            self.viewer.plotter.update()
            print("[DEBUG] Cleared line drawing actor")
            
        except Exception as e:
            print(f"[WARN] Error clearing line: {e}")
