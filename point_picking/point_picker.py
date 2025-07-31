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
        self._picker_callback = self.viewer.plotter.enable_point_picking(
            callback=self._on_point_picked,
            left_clicking=True,
            show_message=True,
            use_picker=True
        )
        self._enabled = True  # Enable point picking by default
        self._picker_callback = None


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
