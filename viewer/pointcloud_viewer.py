import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QWidget, QHBoxLayout

class PointCloudViewer(QWidget):
    def set_point_size(self, size):
        self._point_size = size
        # Update point size for all actors in the plotter
        actors = getattr(self.plotter.renderer, 'actors', {})
        if hasattr(actors, 'values'):
            for actor in actors.values():
                try:
                    actor.GetProperty().SetPointSize(size)
                    #print(f"[DEBUG] Updated actor {actor} point size to: {size}")
                except Exception as e:
                    print(f"[ERROR] Failed to set point size for actor {actor}: {e}")
        else:
            print("[WARN] No actors found in plotter renderer to update point size.")
        self.plotter.update()
    def set_theme(self, theme):
        """Set plotter background and default colormap based on theme."""
        self._theme = theme
        if theme == "Dark":
            self.plotter.set_background("#232629")
            self._colormap = "plasma"
        else:
            self.plotter.set_background("white")
            self._colormap = "viridis"
        self.plotter.update()

    def set_top_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, 0, 1)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 1, 0)
            self.plotter.reset_camera()
            self.plotter.update()

    def set_front_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, -1, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.plotter.update()

    def set_left_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(-1, 0, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.plotter.update()

    def set_right_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(1, 0, 0)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 0, 1)
            self.plotter.reset_camera()
            self.plotter.update()

    def set_bottom_view(self):
        if hasattr(self.plotter, 'camera'):
            self.plotter.camera.SetPosition(0, 0, -1)
            self.plotter.camera.SetFocalPoint(0, 0, 0)
            self.plotter.camera.SetViewUp(0, 1, 0)
            self.plotter.reset_camera()
            self.plotter.update()
    def __init__(self, parent=None):
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton
        super().__init__(parent)
        self.plotter = QtInteractor(self)
        self.plotter.add_axes()
        layout = QHBoxLayout()
        layout.addWidget(self.plotter)
        self.setLayout(layout)
        self._colormap = "viridis"
        self._point_size = 3

    def display_point_cloud(self, points, scalars=None, cmap=None, return_actor=False):
        print(f"[DEBUG] display_point_cloud called: points.shape={getattr(points, 'shape', None)}, return_actor={return_actor}")
        scalar_bar_args = {}
        # Set scalar bar text color based on theme
        if hasattr(self, '_theme') and self._theme == "Dark":
            scalar_bar_args['color'] = 'white'
        else:
            scalar_bar_args['color'] = 'black'
        point_size = getattr(self, '_point_size', 3)
        actor = None
        if scalars is not None:
            used_cmap = cmap if cmap is not None else self._colormap
            actor = self.plotter.add_points(
                points,
                scalars=scalars,
                cmap=used_cmap,
                render_points_as_spheres=True,
                point_size=point_size,
                scalar_bar_args=scalar_bar_args
            )
        else:
            actor = self.plotter.add_points(points, color="#3daee9", render_points_as_spheres=True, point_size=point_size)
        self.plotter.update()
        if return_actor:
            return actor
