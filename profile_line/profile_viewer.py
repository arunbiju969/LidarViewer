"""
Height profile visualization dialog for the LiDAR viewer.
This module provides the ProfileViewer dialog for displaying height vs distance graphs.
"""

import sys
import numpy as np
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ProfileViewer(QDialog):
    """Dialog for viewing and interacting with height profiles."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile_data = None
        self.profile_calculator = None
        self.current_points = None
        self.current_start = None
        self.current_end = None
        self.setup_ui()
        
    def setup_ui(self):
        """Create the profile viewer UI"""
        self.setWindowTitle("Height Profile Viewer")
        self.setModal(False)
        self.resize(1200, 900)
        
        layout = QVBoxLayout(self)
        
        # Controls panel
        controls_group = QGroupBox("Profile Settings")
        controls_layout = QFormLayout(controls_group)
        
        # Tolerance control
        self.tolerance_spinbox = QDoubleSpinBox()
        self.tolerance_spinbox.setRange(0.1, 10.0)
        self.tolerance_spinbox.setValue(1.0)
        self.tolerance_spinbox.setSuffix(" m")
        self.tolerance_spinbox.setDecimals(1)
        self.tolerance_spinbox.setSingleStep(0.1)
        self.tolerance_spinbox.valueChanged.connect(self._on_settings_changed)
        controls_layout.addRow("Search Tolerance:", self.tolerance_spinbox)
        
        # Sample points control
        self.samples_spinbox = QSpinBox()
        self.samples_spinbox.setRange(10, 1000)
        self.samples_spinbox.setValue(100)
        self.samples_spinbox.setSingleStep(10)
        self.samples_spinbox.valueChanged.connect(self._on_settings_changed)
        controls_layout.addRow("Sample Points:", self.samples_spinbox)
        
        # Recalculate button
        self.recalculate_button = QPushButton("Recalculate Profile")
        self.recalculate_button.clicked.connect(self._recalculate_profile)
        controls_layout.addRow("", self.recalculate_button)
        
        layout.addWidget(controls_group)
        
        # Plot area
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(12, 8))
            self.canvas = FigureCanvas(self.figure)
            
            # Add navigation toolbar for zoom, pan, etc.
            self.toolbar = NavigationToolbar(self.canvas, self)
            layout.addWidget(self.toolbar)
            layout.addWidget(self.canvas)
            
            # Set up matplotlib style
            plt.style.use('default')
            
        else:
            error_label = QLabel("Matplotlib not available. Install matplotlib to view profiles.")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            layout.addWidget(error_label)
        
        # Statistics panel
        self.stats_group = QGroupBox("Profile Statistics")
        self.stats_layout = QFormLayout(self.stats_group)
        layout.addWidget(self.stats_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_layer_button = QPushButton("Create Cross-Section Layer")
        self.create_layer_button.clicked.connect(self.create_cross_section_layer)
        button_layout.addWidget(self.create_layer_button)
        
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_profile)
        button_layout.addWidget(self.export_button)
        
        self.save_image_button = QPushButton("Save Image")
        self.save_image_button.clicked.connect(self.save_image)
        button_layout.addWidget(self.save_image_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        # Enable/disable controls based on matplotlib availability
        if not MATPLOTLIB_AVAILABLE:
            self.recalculate_button.setEnabled(False)
            self.create_layer_button.setEnabled(False)
            self.export_button.setEnabled(False)
            self.save_image_button.setEnabled(False)
        
    def set_profile_calculator(self, calculator):
        """Set the profile calculator for recalculation"""
        self.profile_calculator = calculator
        
    def display_profile(self, profile_data, points=None, start_point=None, end_point=None):
        """Plot height vs distance graph"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        self.profile_data = profile_data
        self.current_points = points
        self.current_start = start_point
        self.current_end = end_point
        
        # Update statistics
        self._update_statistics()
        
        # Clear and create new plot
        self.figure.clear()
        
        # Create main profile plot
        ax_main = self.figure.add_subplot(2, 1, 1)
        
        distances = profile_data['distances']
        
        # Plot different height profiles
        ax_main.plot(distances, profile_data['mean_heights'], 'b-', 
                    label='Mean Height', linewidth=2, marker='o', markersize=3)
        
        # Fill between min and max
        ax_main.fill_between(distances, profile_data['min_heights'], profile_data['max_heights'], 
                           alpha=0.3, color='lightblue', label='Min-Max Range')
        
        # Plot min/max lines
        ax_main.plot(distances, profile_data['min_heights'], 'g--', 
                    label='Min Height', alpha=0.8, linewidth=1)
        ax_main.plot(distances, profile_data['max_heights'], 'r--', 
                    label='Max Height', alpha=0.8, linewidth=1)
        
        ax_main.set_xlabel('Distance along line (m)')
        ax_main.set_ylabel('Height (m)')
        ax_main.set_title('Height Profile', fontsize=14, fontweight='bold')
        ax_main.legend(loc='upper right')
        ax_main.grid(True, alpha=0.3)
        
        # Add elevation markers at start and end
        if len(distances) > 0:
            start_height = profile_data['mean_heights'][0]
            end_height = profile_data['mean_heights'][-1]
            
            ax_main.annotate(f'Start: {start_height:.1f}m', 
                           xy=(distances[0], start_height), 
                           xytext=(10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='green', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
            
            ax_main.annotate(f'End: {end_height:.1f}m', 
                           xy=(distances[-1], end_height), 
                           xytext=(-10, 10), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='red', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # Create point count subplot
        ax_count = self.figure.add_subplot(2, 1, 2)
        
        ax_count.bar(distances, profile_data['point_counts'], 
                    width=distances[1]-distances[0] if len(distances) > 1 else 1.0,
                    alpha=0.7, color='orange', label='Point Count')
        
        ax_count.set_xlabel('Distance along line (m)')
        ax_count.set_ylabel('Number of Points')
        ax_count.set_title('Point Density Along Profile', fontsize=12)
        ax_count.grid(True, alpha=0.3)
        
        # Adjust layout to prevent overlap
        self.figure.tight_layout()
        
        # Draw the plot
        self.canvas.draw()
        
        print("[INFO] Profile visualization updated")
        
    def _update_statistics(self):
        """Update the statistics panel"""
        if not self.profile_data:
            return
            
        # Clear existing statistics
        for i in reversed(range(self.stats_layout.count())):
            self.stats_layout.itemAt(i).widget().setParent(None)
        
        summary = self.profile_data.get('summary', {})
        
        stats = [
            ("Total Length", f"{self.profile_data.get('total_length', 0):.2f} m"),
            ("Valid Samples", f"{summary.get('valid_samples', 0)}"),
            ("Coverage", f"{summary.get('coverage_percentage', 0):.1f}%"),
            ("Min Elevation", f"{summary.get('min_elevation', 0):.2f} m"),
            ("Max Elevation", f"{summary.get('max_elevation', 0):.2f} m"),
            ("Mean Elevation", f"{summary.get('mean_elevation', 0):.2f} m"),
            ("Elevation Range", f"{summary.get('elevation_range', 0):.2f} m"),
            ("Total Change", f"{summary.get('total_elevation_change', 0):.2f} m"),
        ]
        
        for label, value in stats:
            self.stats_layout.addRow(f"{label}:", QLabel(value))
        
    def _on_settings_changed(self):
        """Called when tolerance or sample count changes"""
        # Enable recalculate button to show settings have changed
        self.recalculate_button.setStyleSheet("QPushButton { background-color: #ffeb3b; }")
        
    def _recalculate_profile(self):
        """Recalculate profile with new settings"""
        if not (self.profile_calculator and self.current_points is not None 
                and self.current_start is not None and self.current_end is not None):
            QMessageBox.warning(self, "Cannot Recalculate", 
                              "Profile cannot be recalculated. Original data not available.")
            return
            
        try:
            # Get new settings
            tolerance = self.tolerance_spinbox.value()
            num_samples = self.samples_spinbox.value()
            
            print(f"[INFO] Recalculating profile with tolerance={tolerance}, samples={num_samples}")
            
            # Recalculate profile
            new_profile_data = self.profile_calculator.calculate_profile(
                self.current_points, self.current_start, self.current_end,
                num_samples=num_samples, tolerance=tolerance
            )
            
            # Update display
            self.display_profile(new_profile_data, self.current_points, 
                               self.current_start, self.current_end)
            
            # Reset button style
            self.recalculate_button.setStyleSheet("")
            
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", 
                               f"Failed to recalculate profile:\n{str(e)}")
            print(f"[ERROR] Profile recalculation failed: {e}")
        
    def export_profile(self):
        """Export profile data to CSV"""
        if self.profile_data is None:
            QMessageBox.warning(self, "No Data", "No profile data to export.")
            return
            
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Profile Data", "height_profile.csv", 
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Create CSV data manually (avoid pandas dependency)
                import csv
                
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow(['Distance_m', 'Min_Height_m', 'Max_Height_m', 
                                   'Mean_Height_m', 'Std_Height_m', 'Point_Count'])
                    
                    # Write data
                    for i in range(len(self.profile_data['distances'])):
                        writer.writerow([
                            self.profile_data['distances'][i],
                            self.profile_data['min_heights'][i],
                            self.profile_data['max_heights'][i],
                            self.profile_data['mean_heights'][i],
                            self.profile_data['std_heights'][i],
                            self.profile_data['point_counts'][i]
                        ])
                
                QMessageBox.information(self, "Export Successful", 
                                      f"Profile data exported to:\n{file_path}")
                print(f"[INFO] Profile data exported to: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", 
                                   f"Failed to export profile data:\n{str(e)}")
                print(f"[ERROR] Failed to export profile data: {e}")
    
    def save_image(self):
        """Save the profile plot as an image"""
        if not MATPLOTLIB_AVAILABLE or self.profile_data is None:
            QMessageBox.warning(self, "Cannot Save", "No plot to save.")
            return
            
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Profile Image", "height_profile.png",
            "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg);;All Files (*)"
        )
        
        if file_path:
            try:
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Save Successful", 
                                      f"Profile image saved to:\n{file_path}")
                print(f"[INFO] Profile image saved to: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Save Error", 
                                   f"Failed to save profile image:\n{str(e)}")
                print(f"[ERROR] Failed to save profile image: {e}")
    
    def create_cross_section_layer(self):
        """Create a new layer with only the points in the cross-section"""
        if not (self.current_points is not None and self.current_start is not None 
                and self.current_end is not None):
            QMessageBox.warning(self, "Cannot Create Layer", 
                              "Cross-section data not available.")
            return
            
        try:
            # Get settings
            tolerance = self.tolerance_spinbox.value()
            
            print(f"[INFO] Creating cross-section layer with tolerance={tolerance}")
            
            # Find all points within tolerance of the line
            cross_section_points = self._extract_cross_section_points(
                self.current_points, self.current_start, self.current_end, tolerance
            )
            
            if cross_section_points.shape[0] == 0:
                QMessageBox.warning(self, "No Points Found", 
                                  f"No points found within {tolerance}m of the profile line.")
                return
                
            # Export as temporary LAZ file
            temp_file = self._export_cross_section_to_laz(cross_section_points)
            
            if temp_file:
                # Signal parent to import the file
                if hasattr(self.parent(), '_import_cross_section_layer'):
                    self.parent()._import_cross_section_layer(temp_file, cross_section_points.shape[0])
                    QMessageBox.information(self, "Layer Created", 
                                          f"Cross-section layer created with {cross_section_points.shape[0]} points.\n"
                                          f"Temporary file: {temp_file}")
                else:
                    QMessageBox.information(self, "Export Successful", 
                                          f"Cross-section exported to: {temp_file}\n"
                                          f"Points: {cross_section_points.shape[0]}")
                
        except Exception as e:
            QMessageBox.critical(self, "Layer Creation Error", 
                               f"Failed to create cross-section layer:\n{str(e)}")
            print(f"[ERROR] Cross-section layer creation failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_cross_section_points(self, points, start_point, end_point, tolerance):
        """Extract points within tolerance distance of the line"""
        from scipy.spatial import cKDTree
        
        # Generate many sample points along the line for better coverage
        num_line_samples = max(100, int(np.linalg.norm(end_point - start_point) * 10))
        line_points = self._interpolate_line_points(start_point, end_point, num_line_samples)
        
        # Build spatial index for line points
        line_tree = cKDTree(line_points[:, :2])  # Only X,Y for 2D distance
        
        # Find all points within tolerance of any line point
        point_indices = set()
        
        for point in points:
            distances, indices = line_tree.query(point[:2], k=1)
            if distances <= tolerance:
                # Find the original point index
                original_idx = np.where((points == point).all(axis=1))[0]
                if len(original_idx) > 0:
                    point_indices.add(original_idx[0])
        
        # Convert to list and extract points
        selected_indices = list(point_indices)
        return points[selected_indices] if selected_indices else np.array([]).reshape(0, 3)
    
    def _interpolate_line_points(self, start, end, num_samples):
        """Generate evenly spaced points along the line"""
        t = np.linspace(0, 1, num_samples)
        line_points = np.array([start + t_val * (end - start) for t_val in t])
        return line_points
    
    def _export_cross_section_to_laz(self, points):
        """Export cross-section points to a temporary LAZ file with full dimension preservation"""
        try:
            from fileio.las_exporter import create_temp_laz_file, find_original_point_indices
        except ImportError:
            # Fallback to basic export
            return self._basic_export_cross_section_to_laz(points)
            
        try:
            # Get original LAS data and find point indices
            original_las = None
            original_points = None
            point_indices = None
            
            if hasattr(self.parent(), 'layer_manager'):
                current_layer_id = self.parent().layer_manager.get_current_layer_id()
                if current_layer_id and current_layer_id in self.parent().layer_manager.layers:
                    layer_data = self.parent().layer_manager.layers[current_layer_id]
                    original_las = layer_data.get('las', None)
                    original_points = layer_data.get('points', None)
            
            # Find indices of cross-section points in original data
            if original_points is not None:
                point_indices = find_original_point_indices(points, original_points)
                print(f"[INFO] Found {len(point_indices)} matching point indices")
            
            # Create temporary LAZ file with full preservation
            temp_path = create_temp_laz_file(
                points, original_las, point_indices, prefix="cross_section"
            )
            
            if temp_path:
                print(f"[INFO] Cross-section exported with full dimension preservation: {temp_path}")
                return temp_path
            else:
                print("[WARN] Enhanced export failed, trying basic export")
                return self._basic_export_cross_section_to_laz(points)
                
        except Exception as e:
            print(f"[ERROR] Enhanced export failed: {e}")
            return self._basic_export_cross_section_to_laz(points)
    
    def _basic_export_cross_section_to_laz(self, points):
        """Basic LAZ export fallback"""
        import tempfile
        import os
        try:
            import laspy
        except ImportError:
            QMessageBox.critical(self, "Import Error", "laspy library not found. Cannot export LAZ file.")
            return None
            
        try:
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            temp_filename = f"cross_section_{int(np.random.rand() * 1000000)}.laz"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Get original LAS data if available from parent
            original_las = None
            if hasattr(self.parent(), 'layer_manager'):
                current_layer_id = self.parent().layer_manager.get_current_layer_id()
                if current_layer_id and current_layer_id in self.parent().layer_manager.layers:
                    original_las = self.parent().layer_manager.layers[current_layer_id].get('las', None)
            
            if original_las:
                # Create new LAS file based on original header
                header = laspy.LasHeader(point_format=original_las.header.point_format, 
                                       version=original_las.header.version)
                header.offsets = original_las.header.offsets
                header.scales = original_las.header.scales
                
                # Copy CRS information
                if hasattr(original_las.header, 'crs') and original_las.header.crs:
                    header.crs = original_las.header.crs
                
                las_file = laspy.LasData(header)
                
                # Set coordinates
                las_file.x = points[:, 0]
                las_file.y = points[:, 1] 
                las_file.z = points[:, 2]
                
                # Copy other dimensions if they exist in original
                point_indices = []
                for point in points:
                    # Find matching points in original data
                    distances = np.sqrt(np.sum((original_las.xyz - point)**2, axis=1))
                    closest_idx = np.argmin(distances)
                    if distances[closest_idx] < 0.001:  # Very close match
                        point_indices.append(closest_idx)
                    else:
                        point_indices.append(0)  # Fallback
                
                # Copy available dimensions
                for dim_name in original_las.point_format.dimension_names:
                    if dim_name not in ['X', 'Y', 'Z']:
                        try:
                            original_data = getattr(original_las, dim_name.lower())
                            setattr(las_file, dim_name.lower(), original_data[point_indices])
                        except:
                            print(f"[WARN] Could not copy dimension: {dim_name}")
                            
            else:
                # Create basic LAS file
                header = laspy.LasHeader(point_format=3, version="1.2")
                las_file = laspy.LasData(header)
                las_file.x = points[:, 0]
                las_file.y = points[:, 1]
                las_file.z = points[:, 2]
            
            # Write the file
            las_file.write(temp_path)
            print(f"[INFO] Cross-section exported to: {temp_path}")
            return temp_path
            
        except Exception as e:
            print(f"[ERROR] Failed to export cross-section: {e}")
            return None
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        print("[INFO] Profile viewer closed")
        event.accept()
