# Height Profile Feature Implementation Plan

## Overview
Build a height profile along a line feature for the LiDAR viewer that allows users to draw a line on the 3D point cloud and view a 2D height profile graph showing elevation changes along that line.

## 1. User Interface Components

### Toolbar Button
- Add a "Height Profile" toggle button to the ViewToolbar (similar to point picking and bounding box)
- Button toggles between "Height Profile" and "Cancel Profile" states
- Visual feedback when height profile mode is active

### Profile Window
- Create a separate dialog/window to display the height profile graph
- Resizable dialog with matplotlib integration
- Export functionality for profile data and images

### Line Drawing
- Visual feedback showing the drawn line on the 3D viewer
- Two-click interaction: first click sets start point, second click sets end point
- Line displayed as a colored line actor in the 3D scene

### Status Indicator
- Show when height profile mode is active (similar to point picking status)
- Clear instructions for user interaction

## 2. Core Functionality Components

### A. Line Drawing System (`profile_line/line_drawer.py`)
```python
class LineDrawer:
    def __init__(self, viewer):
        self.viewer = viewer
        self.start_point = None
        self.end_point = None
        self.line_actor = None
        self.is_drawing = False
        self._picking_callback = None
        
    def start_line_drawing(self):
        """Enable line drawing mode with two-click interaction"""
        self.is_drawing = True
        self.start_point = None
        self.end_point = None
        self._enable_picking()
        
    def stop_line_drawing(self):
        """Disable line drawing mode"""
        self.is_drawing = False
        self._disable_picking()
        self.clear_line()
        
    def _enable_picking(self):
        """Enable point picking for line drawing"""
        self._picking_callback = self.viewer.plotter.enable_point_picking(
            callback=self._on_point_picked,
            left_clicking=True,
            show_message=False
        )
        
    def _disable_picking(self):
        """Disable point picking"""
        if self._picking_callback:
            self.viewer.plotter.disable_picking()
            self._picking_callback = None
        
    def _on_point_picked(self, picked):
        """Handle point picking events"""
        if not self.is_drawing or picked is None or picked.n_points == 0:
            return
            
        point = picked.points[0]
        
        if self.start_point is None:
            self.on_first_click(point)
        else:
            self.on_second_click(point)
            
    def on_first_click(self, picked_point):
        """Store start point, show temporary marker"""
        self.start_point = picked_point
        print(f"[INFO] Start point selected: {picked_point}")
        # Add visual marker for start point
        self._add_point_marker(picked_point, color='green', name='start_marker')
        
    def on_second_click(self, picked_point):
        """Store end point, draw final line, trigger profile calculation"""
        self.end_point = picked_point
        print(f"[INFO] End point selected: {picked_point}")
        # Add visual marker for end point
        self._add_point_marker(picked_point, color='red', name='end_marker')
        # Draw the line
        self.draw_line(self.start_point, self.end_point)
        # Trigger profile calculation (via callback to MainWindow)
        if hasattr(self, 'on_line_completed_callback') and self.on_line_completed_callback:
            self.on_line_completed_callback(self.start_point, self.end_point)
        
    def draw_line(self, start, end):
        """Create and display line actor in 3D viewer"""
        import pyvista as pv
        import numpy as np
        
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
        
    def _add_point_marker(self, point, color='blue', name='marker'):
        """Add a point marker to the viewer"""
        import pyvista as pv
        import numpy as np
        
        sphere = pv.Sphere(radius=0.5, center=point)
        self.viewer.plotter.add_mesh(
            sphere,
            color=color,
            name=name,
            pickable=False
        )
        
    def clear_line(self):
        """Remove line actor and markers from viewer"""
        try:
            if self.line_actor:
                self.viewer.plotter.remove_actor(self.line_actor)
                self.line_actor = None
            # Remove markers
            for name in ['start_marker', 'end_marker']:
                try:
                    self.viewer.plotter.remove_actor(name)
                except:
                    pass
            self.viewer.plotter.update()
        except Exception as e:
            print(f"[WARN] Error clearing line: {e}")
```

### B. Height Profile Calculator (`profile_line/profile_calculator.py`)
```python
import numpy as np
from scipy.spatial import cKDTree

class ProfileCalculator:
    def __init__(self):
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
            tolerance: Search radius around each sample point
            
        Returns:
            dict: Profile data with distances, heights, statistics
        """
        # Generate sample points along the line
        line_points = self.interpolate_line_points(start_point, end_point, num_samples)
        
        # Build spatial index for efficient queries
        tree = cKDTree(points[:, :2])  # Only use X,Y for 2D distance
        
        profile_data = {
            'distances': [],
            'min_heights': [],
            'max_heights': [],
            'mean_heights': [],
            'std_heights': [],
            'point_counts': []
        }
        
        # Calculate total line length
        line_length = np.linalg.norm(end_point - start_point)
        
        for i, sample_point in enumerate(line_points):
            # Find nearby points
            indices = tree.query_ball_point(sample_point[:2], tolerance)
            
            if len(indices) > 0:
                nearby_points = points[indices]
                heights = nearby_points[:, 2]  # Z values
                
                # Calculate statistics
                stats = self.calculate_height_statistics(heights)
                
                # Distance along line
                distance = (i / (num_samples - 1)) * line_length
                
                profile_data['distances'].append(distance)
                profile_data['min_heights'].append(stats['min'])
                profile_data['max_heights'].append(stats['max'])
                profile_data['mean_heights'].append(stats['mean'])
                profile_data['std_heights'].append(stats['std'])
                profile_data['point_counts'].append(len(heights))
            else:
                # No points found - use NaN or interpolation
                distance = (i / (num_samples - 1)) * line_length
                profile_data['distances'].append(distance)
                profile_data['min_heights'].append(np.nan)
                profile_data['max_heights'].append(np.nan)
                profile_data['mean_heights'].append(np.nan)
                profile_data['std_heights'].append(np.nan)
                profile_data['point_counts'].append(0)
        
        # Convert to numpy arrays
        for key in profile_data:
            profile_data[key] = np.array(profile_data[key])
            
        return profile_data
        
    def interpolate_line_points(self, start, end, num_samples):
        """Generate evenly spaced points along the line"""
        t = np.linspace(0, 1, num_samples)
        line_points = np.array([start + t_val * (end - start) for t_val in t])
        return line_points
        
    def calculate_height_statistics(self, heights):
        """Calculate min, max, mean, std dev of heights"""
        return {
            'min': np.min(heights),
            'max': np.max(heights),
            'mean': np.mean(heights),
            'std': np.std(heights)
        }
```

### C. Profile Visualization (`profile_line/profile_viewer.py`)
```python
import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt
import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class ProfileViewer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data = None
        self.setup_ui()
        
    def setup_ui(self):
        """Create the profile viewer UI"""
        self.setWindowTitle("Height Profile Viewer")
        self.setModal(False)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Controls panel
        controls_group = QGroupBox("Profile Settings")
        controls_layout = QFormLayout(controls_group)
        
        self.tolerance_spinbox = QDoubleSpinBox()
        self.tolerance_spinbox.setRange(0.1, 10.0)
        self.tolerance_spinbox.setValue(1.0)
        self.tolerance_spinbox.setSuffix(" m")
        controls_layout.addRow("Search Tolerance:", self.tolerance_spinbox)
        
        self.samples_spinbox = QSpinBox()
        self.samples_spinbox.setRange(10, 1000)
        self.samples_spinbox.setValue(100)
        controls_layout.addRow("Sample Points:", self.samples_spinbox)
        
        layout.addWidget(controls_group)
        
        # Plot area
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(10, 6))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
        else:
            error_label = QLabel("Matplotlib not available. Install matplotlib to view profiles.")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_profile)
        button_layout.addWidget(self.export_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
    def display_profile(self, profile_data):
        """Plot height vs distance graph"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        self.profile_data = profile_data
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        distances = profile_data['distances']
        
        # Plot different height profiles
        ax.plot(distances, profile_data['mean_heights'], 'b-', label='Mean Height', linewidth=2)
        ax.fill_between(distances, profile_data['min_heights'], profile_data['max_heights'], 
                       alpha=0.3, color='gray', label='Min-Max Range')
        
        # Plot min/max lines
        ax.plot(distances, profile_data['min_heights'], 'g--', label='Min Height', alpha=0.7)
        ax.plot(distances, profile_data['max_heights'], 'r--', label='Max Height', alpha=0.7)
        
        ax.set_xlabel('Distance along line (m)')
        ax.set_ylabel('Height (m)')
        ax.set_title('Height Profile')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.canvas.draw()
        
    def export_profile(self):
        """Export profile data to CSV"""
        if self.profile_data is None:
            return
            
        from PySide6.QtWidgets import QFileDialog
        import pandas as pd
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile Data", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Create DataFrame
                df = pd.DataFrame({
                    'Distance_m': self.profile_data['distances'],
                    'Min_Height_m': self.profile_data['min_heights'],
                    'Max_Height_m': self.profile_data['max_heights'],
                    'Mean_Height_m': self.profile_data['mean_heights'],
                    'Std_Height_m': self.profile_data['std_heights'],
                    'Point_Count': self.profile_data['point_counts']
                })
                
                df.to_csv(file_path, index=False)
                print(f"[INFO] Profile data exported to: {file_path}")
                
            except Exception as e:
                print(f"[ERROR] Failed to export profile data: {e}")
```

## 3. Integration Points

### A. ViewToolbar Updates (`viewer/view_toolbar.py`)
Add height profile toggle button after the bounding box button:

```python
# Add height profile toggle action
self.height_profile_action = QAction("Height Profile", self)
self.height_profile_action.setCheckable(True)
self.height_profile_action.setChecked(False)
self.height_profile_action.triggered.connect(self._toggle_height_profile)
self.addAction(self.height_profile_action)

def _toggle_height_profile(self):
    print("[DEBUG] Height profile toggle triggered.")
    if hasattr(self.main_window, '_toggle_height_profile_mode'):
        new_state = self.height_profile_action.isChecked()
        self.main_window._toggle_height_profile_mode(new_state)
        if new_state:
            self.height_profile_action.setText("Cancel Profile")
        else:
            self.height_profile_action.setText("Height Profile")
    else:
        print("[WARN] MainWindow missing _toggle_height_profile_mode method.")
```

### B. MainWindow Integration (`lidar_viewer.py`)
Add height profile components to MainWindow:

```python
def __init__(self, ...):
    # ...existing code...
    
    # Initialize height profile components
    from profile_line.line_drawer import LineDrawer
    from profile_line.profile_calculator import ProfileCalculator
    from profile_line.profile_viewer import ProfileViewer
    
    self.line_drawer = LineDrawer(self.viewer)
    self.profile_calculator = ProfileCalculator()
    self.profile_viewer = ProfileViewer(self)
    
    # Set callback for line completion
    self.line_drawer.on_line_completed_callback = self._on_profile_line_completed

def _toggle_height_profile_mode(self, enabled):
    """Enable/disable height profile drawing mode"""
    if enabled:
        self.line_drawer.start_line_drawing()
        self._show_height_profile_status(True)
        print("[INFO] Height profile mode enabled. Click two points to draw a line.")
    else:
        self.line_drawer.stop_line_drawing()
        self._show_height_profile_status(False)
        print("[INFO] Height profile mode disabled.")

def _show_height_profile_status(self, enabled):
    """Show or hide height profile status indicator"""
    # Add similar status label as point picking
    if not hasattr(self, 'height_profile_status_label'):
        from PySide6.QtWidgets import QLabel
        self.height_profile_status_label = QLabel("Height Profile Mode: Click two points")
        self.height_profile_status_label.setStyleSheet("""
            QLabel {
                background-color: rgba(233, 174, 61, 200);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                margin: 10px;
            }
        """)
        self.height_profile_status_label.setAlignment(Qt.AlignCenter)
        self.height_profile_status_label.hide()
        # Add to viewer container layout
        viewer_container_layout = self.findChild(QVBoxLayout)
        viewer_container_layout.insertWidget(1, self.height_profile_status_label)
    
    if enabled:
        self.height_profile_status_label.show()
    else:
        self.height_profile_status_label.hide()

def _on_profile_line_completed(self, start_point, end_point):
    """Called when user completes drawing a line"""
    print(f"[INFO] Profile line completed: {start_point} -> {end_point}")
    
    # Get current layer points
    current_layer_id = self.layer_manager.get_current_layer_id()
    if not current_layer_id or current_layer_id not in self.layer_manager.layers:
        print("[WARN] No current layer available for profile calculation")
        return
        
    layer = self.layer_manager.layers[current_layer_id]
    points = layer.get('points', None)
    
    if points is None or points.shape[0] == 0:
        print("[WARN] No points available in current layer")
        return
    
    # Calculate profile
    try:
        profile_data = self.profile_calculator.calculate_profile(
            points, start_point, end_point, num_samples=100, tolerance=1.0
        )
        
        # Show profile viewer
        self.profile_viewer.display_profile(profile_data)
        self.profile_viewer.show()
        
        # Disable height profile mode
        self.view_toolbar.height_profile_action.setChecked(False)
        self._toggle_height_profile_mode(False)
        
    except Exception as e:
        print(f"[ERROR] Failed to calculate profile: {e}")
```

## 4. Implementation Steps

### Phase 1: Basic Line Drawing (2-3 days)
1. **Create directory structure**: `profile_line/` folder with `__init__.py`
2. **Implement LineDrawer class**: Basic two-click line drawing functionality
3. **Add height profile button**: Update ViewToolbar with new toggle button
4. **Basic line visualization**: Display line in 3D viewer
5. **Status indicator**: Add height profile mode status label

### Phase 2: Profile Calculation (3-4 days)
1. **Implement ProfileCalculator class**: Core height profile calculation logic
2. **Add spatial indexing**: Use scipy.spatial.cKDTree for efficient queries
3. **Height statistics**: Calculate min/max/mean/std along line
4. **Parameter tuning**: Test different tolerance values and sampling densities
5. **Error handling**: Handle edge cases (no points, invalid lines)

### Phase 3: Profile Visualization (2-3 days)
1. **Create ProfileViewer dialog**: Qt dialog with matplotlib integration
2. **Profile plotting**: Height vs distance graphs with multiple profiles
3. **Interactive features**: Zoom, pan, legend
4. **Settings controls**: Tolerance and sample count adjustment
5. **Export functionality**: CSV export for profile data

### Phase 4: Advanced Features (2-3 days)
1. **Profile settings persistence**: Save/load user preferences
2. **Multiple profile support**: Handle multiple profile lines
3. **Profile comparison**: Compare profiles from different layers
4. **Performance optimization**: Handle large point clouds efficiently

### Phase 5: Polish & Integration (1-2 days)
1. **UI/UX improvements**: Better visual feedback, keyboard shortcuts
2. **Error handling**: Comprehensive error handling and user feedback
3. **Documentation**: Add docstrings and usage documentation
4. **Testing**: Test with various point cloud sizes and line orientations

## 5. Technical Considerations

### Spatial Indexing
- Use `scipy.spatial.cKDTree` for efficient nearest neighbor queries
- Build index once per layer for multiple profile calculations
- Consider 2D vs 3D indexing based on use case

### Line-Point Distance Calculation
```python
def point_to_line_distance_2d(point, line_start, line_end):
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
```

### Memory Management
- Process large point clouds in chunks if needed
- Use NumPy for efficient array operations
- Consider lazy loading for very large datasets

### User Experience
- Clear visual feedback during line drawing
- Intuitive cursor changes and status messages
- Keyboard shortcuts (Escape to cancel, Enter to confirm)
- Context-sensitive help

## 6. File Structure
```
LidarViewer/
├── profile_line/
│   ├── __init__.py
│   ├── line_drawer.py          # Line drawing interaction
│   ├── profile_calculator.py   # Height profile calculation
│   └── profile_viewer.py       # Profile visualization dialog
├── viewer/
│   └── view_toolbar.py         # (modified - add height profile button)
├── lidar_viewer.py             # (modified - integrate height profile)
└── environment.yml             # (modified - add matplotlib, scipy)
```

## 7. Dependencies to Add

Update `environment.yml`:
```yaml
dependencies:
  # ...existing dependencies...
  - matplotlib       # For profile plotting
  - scipy            # For spatial indexing (cKDTree)
  - pandas           # For data export (optional)
```

## 8. Usage Workflow

1. **Load point cloud**: User loads LAS/LAZ file as usual
2. **Enable height profile mode**: Click "Height Profile" button in toolbar
3. **Draw line**: Click two points in 3D viewer to define profile line
4. **View profile**: Profile viewer dialog opens automatically with height graph
5. **Analyze results**: View min/max/mean heights along the line
6. **Export data**: Export profile data to CSV if needed
7. **Multiple profiles**: Repeat process for additional profile lines

## 9. Future Enhancements

- **3D profile visualization**: Show profile as a vertical plane in 3D
- **Profile comparison**: Compare profiles from different time periods
- **Automated feature extraction**: Detect ridges, valleys, slopes
- **Profile smoothing**: Apply filters to reduce noise
- **Cross-section analysis**: Generate cross-sections perpendicular to main profile
- **Volume calculations**: Calculate cut/fill volumes between profiles

This comprehensive plan provides a solid foundation for implementing the height profile feature while maintaining consistency with the existing codebase architecture.
