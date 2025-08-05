"""
PointPicker module for interactive point selection in the LiDAR viewer.

This module will provide tools for picking points in the 3D view, handling user clicks, and returning selected point data.
"""

class PointPicker:
    """
    Handles interactive point picking in the viewer.
    Usage:
        - Connect to the viewer's picking/click events.
        - Return selected point coordinates and metadata.
    """
    def __init__(self, viewer):
        self.viewer = viewer
        self.picked_points = []  # Store picked points (coords, index)
        self._enabled = False  # Disable point picking by default
        self._picker_callback = None

    def set_enabled(self, enabled):
        """Enable or disable point picking"""
        if enabled and not self._enabled:
            # First disable any existing picking to avoid PyVistaPickingError
            try:
                self.viewer.plotter.disable_picking()
            except Exception:
                pass  # Ignore if no picking was active
            
            # Enable point picking
            self._picker_callback = self.viewer.plotter.enable_point_picking(
                callback=self._on_point_picked,
                left_clicking=True,
                show_message=True,
                use_picker=True
            )
            self._enabled = True
            print("[INFO] Point picking enabled.")
        elif not enabled and self._enabled:
            # Disable point picking
            try:
                self.viewer.plotter.disable_picking()
            except Exception:
                pass  # Ignore if picking was already disabled
            self._picker_callback = None
            self._enabled = False
            print("[INFO] Point picking disabled.")
    
    def is_enabled(self):
        """Check if point picking is currently enabled"""
        return self._enabled

    def _on_point_picked(self, picked):
        print("[DEBUG] _on_point_picked callback triggered.")
        # picked is a pyvista.PolyData with one point
        if picked is not None and picked.n_points > 0:
            coords = picked.points[0]
            # Try to get point index if available
            point_id = None
            if hasattr(picked, 'point_arrays') and 'vtkOriginalPointIds' in picked.point_arrays:
                point_id = int(picked.point_arrays['vtkOriginalPointIds'][0])
            self.picked_points.append((coords, point_id))
            print(f"[INFO] Picked point: coords={coords}, index={point_id}")
            # TODO: Integrate with UI (highlight, sidebar, etc.)
        else:
            print("[WARN] No point picked.")
