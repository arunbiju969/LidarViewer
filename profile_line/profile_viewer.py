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
            
            print(f"[INFO] ========== CROSS-SECTION LAYER CREATION STARTED ==========")
            print(f"[INFO] Tolerance: {tolerance}m")
            print(f"[INFO] Available points: {len(self.current_points):,}")
            
            # Find all points within tolerance of the line
            cross_section_points = self._extract_cross_section_points(
                self.current_points, self.current_start, self.current_end, tolerance
            )
            
            if cross_section_points.shape[0] == 0:
                QMessageBox.warning(self, "No Points Found", 
                                  f"No points found within {tolerance}m of the profile line.")
                return
                
            print(f"[INFO] Cross-section points found: {len(cross_section_points):,}")
            print(f"[INFO] APPROACH: Attempting ENHANCED method (with preserved attributes)")
            
            # Create cross-section layer with preserved attributes (preferred method)
            self._create_cross_section_layer_with_attributes(cross_section_points, tolerance)
            
        except Exception as e:
            QMessageBox.critical(self, "Layer Creation Error", 
                               f"Failed to create cross-section layer:\n{str(e)}")
            print(f"[ERROR] Cross-section layer creation failed: {e}")
            print(f"[INFO] ========== CROSS-SECTION LAYER CREATION FAILED ==========")
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
    
    def _create_cross_section_layer_with_attributes(self, points, tolerance):
        """Create cross-section layer preserving original point attributes"""
        try:
            from layers.layer_db import generate_layer_id
            
            print(f"[INFO] ENHANCED METHOD: Attempting to preserve original attributes")
            
            # Get the original layer data
            if not hasattr(self.parent(), 'layer_manager'):
                print(f"[WARN] ENHANCED METHOD: No layer_manager found, falling back to DIRECT method")
                return self._create_cross_section_layer_direct(points, tolerance)
                
            current_layer_id = self.parent().layer_manager.get_current_layer_id()
            if not current_layer_id or current_layer_id not in self.parent().layer_manager.layers:
                print(f"[WARN] ENHANCED METHOD: No current layer found, falling back to DIRECT method")
                return self._create_cross_section_layer_direct(points, tolerance)
                
            original_layer = self.parent().layer_manager.layers[current_layer_id]
            original_points = original_layer.get('points', None)
            original_las_data = original_layer.get('las', None)
            
            if original_points is None or original_las_data is None:
                print(f"[WARN] ENHANCED METHOD: Original layer data incomplete, falling back to DIRECT method")
                return self._create_cross_section_layer_direct(points, tolerance)
            
            # Find indices of cross-section points in original data
            from fileio.pdal_exporter import find_original_point_indices
            point_indices = find_original_point_indices(points, original_points, tolerance=1e-3)
            
            if len(point_indices) == 0:
                print("[WARN] ENHANCED METHOD: No matching points found in original data, falling back to DIRECT method")
                return self._create_cross_section_layer_direct(points, tolerance)
            
            print(f"[INFO] ENHANCED METHOD: Found {len(point_indices)} matching points in original data")
            print(f"[INFO] ENHANCED METHOD: Original layer has {len(original_las_data)} attributes")
            
            # Extract attributes for the cross-section points
            cross_section_las_data = {}
            for key, values in original_las_data.items():
                if hasattr(values, '__getitem__') and len(values) == len(original_points):
                    cross_section_las_data[key] = values[point_indices]
                else:
                    # For scalar values or incompatible arrays
                    cross_section_las_data[key] = values
            
            # Create layer name
            import os
            original_file = original_layer.get('file_path', '')
            if original_file:
                base_name = f"CrossSection_{os.path.splitext(os.path.basename(original_file))[0]}"
            else:
                base_name = "CrossSection"
            
            layer_name = f"{base_name}_{len(point_indices)}pts_tol{tolerance}m"
            uuid = generate_layer_id()
            
            # Use the matched points (to ensure consistency)
            matched_points = original_points[point_indices]
            
            # Add layer to manager
            self.parent().layer_manager.add_layer(
                uuid, layer_name, matched_points, cross_section_las_data, visible=True, actor=None
            )
            
            # Configure layer appearance
            default_settings = self.parent().sidebar.get_sidebar_settings()
            default_settings['colormap'] = 'plasma'  # Different colormap for cross-section
            
            from layers.layer_db import save_layer_settings
            save_layer_settings(uuid, layer_name, default_settings)
            
            # Update display and UI
            self.parent().plot_all_layers()
            
            all_layers = [(u, l['file_path']) for u, l in self.parent().layer_manager.layers.items()]
            checked_uuids = set(u for u, l in self.parent().layer_manager.layers.items() if l['visible'])
            self.parent().sidebar.update_layers(all_layers, current_uuid=uuid, checked_uuids=checked_uuids)
            
            self.parent().sidebar.set_status(f"Cross-section layer created: {len(matched_points)} points")
            self.parent().sidebar.update_file_info(layer_name, len(matched_points))
            
            # Get available dimensions from original data
            dims = list(cross_section_las_data.keys()) if cross_section_las_data else ['X', 'Y', 'Z']
            self.parent().sidebar.update_dimensions(dims)
            
            self.parent().sidebar.set_sidebar_settings(default_settings)
            
            # Show success message
            QMessageBox.information(self, "Enhanced Layer Created", 
                                  f"Cross-section layer created with preserved attributes!\n\n"
                                  f"Name: {layer_name}\n"
                                  f"Points: {len(matched_points):,}\n"
                                  f"Tolerance: {tolerance}m\n"
                                  f"Attributes: {len(dims)} dimensions")
            
            print(f"[INFO] ENHANCED METHOD: Successfully created layer '{layer_name}' with {len(dims)} attributes")
            print(f"[INFO] ========== CROSS-SECTION LAYER CREATION COMPLETED (ENHANCED) ==========")
            
        except Exception as e:
            print(f"[ERROR] ENHANCED METHOD: Failed to create enhanced cross-section layer: {e}")
            print(f"[INFO] ENHANCED METHOD: Falling back to DIRECT method")
            return self._create_cross_section_layer_direct(points, tolerance)

    def _create_cross_section_layer_direct(self, points, tolerance):
        """Create cross-section layer directly without file export"""
        try:
            from layers.layer_db import generate_layer_id
            
            print(f"[INFO] DIRECT METHOD: Creating cross-section layer directly in memory")
            print(f"[INFO] DIRECT METHOD: Processing {len(points)} points with tolerance {tolerance}m")
            
            # Get original layer info for naming
            base_name = "CrossSection"
            if hasattr(self.parent(), 'layer_manager'):
                current_layer_id = self.parent().layer_manager.get_current_layer_id()
                if current_layer_id and current_layer_id in self.parent().layer_manager.layers:
                    original_file = self.parent().layer_manager.layers[current_layer_id].get('file_path', '')
                    if original_file:
                        import os
                        base_name = f"CrossSection_{os.path.splitext(os.path.basename(original_file))[0]}"
            
            layer_name = f"{base_name}_{len(points)}pts_tol{tolerance}m"
            uuid = generate_layer_id()
            
            print(f"[INFO] DIRECT METHOD: Creating layer '{layer_name}'")
            print(f"[INFO] DIRECT METHOD: Using minimal LAS data structure (X, Y, Z, intensity, classification)")
            
            # Create minimal LAS-like data structure for compatibility
            fake_las_data = {
                'X': points[:, 0],
                'Y': points[:, 1], 
                'Z': points[:, 2],
                'intensity': np.zeros(len(points), dtype=np.uint16),  # Default intensity
                'classification': np.full(len(points), 1, dtype=np.uint8)  # Unclassified
            }
            
            # Add layer directly to manager
            self.parent().layer_manager.add_layer(
                uuid, layer_name, points, fake_las_data, visible=True, actor=None
            )
            
            # Configure layer appearance (different color for cross-section)
            default_settings = self.parent().sidebar.get_sidebar_settings()
            default_settings['colormap'] = 'plasma'  # Different colormap
            default_settings['dimension'] = 'Z'  # Color by elevation
            
            from layers.layer_db import save_layer_settings
            save_layer_settings(uuid, layer_name, default_settings)
            
            # Update display
            self.parent().plot_all_layers()
            
            # Update sidebar
            all_layers = [(u, l['file_path']) for u, l in self.parent().layer_manager.layers.items()]
            checked_uuids = set(u for u, l in self.parent().layer_manager.layers.items() if l['visible'])
            self.parent().sidebar.update_layers(all_layers, current_uuid=uuid, checked_uuids=checked_uuids)
            
            # Update sidebar info
            self.parent().sidebar.set_status(f"Cross-section layer created: {len(points)} points")
            self.parent().sidebar.update_file_info(layer_name, len(points))
            self.parent().sidebar.update_dimensions(['X', 'Y', 'Z', 'intensity', 'classification'])
            
            # Apply settings to new layer
            self.parent().sidebar.set_sidebar_settings(default_settings)
            
            # Show success message
            QMessageBox.information(self, "Layer Created", 
                                  f"Cross-section layer created successfully!\n\n"
                                  f"Name: {layer_name}\n"
                                  f"Points: {len(points):,}\n"
                                  f"Tolerance: {tolerance}m")
            
            print(f"[INFO] DIRECT METHOD: Successfully created layer '{layer_name}' with minimal attributes")
            print(f"[INFO] ========== CROSS-SECTION LAYER CREATION COMPLETED (DIRECT) ==========")
            
        except Exception as e:
            print(f"[ERROR] DIRECT METHOD: Failed to create cross-section layer: {e}")
            print(f"[INFO] ========== CROSS-SECTION LAYER CREATION FAILED (DIRECT) ==========")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Layer Creation Failed", 
                               f"Failed to create cross-section layer:\n{str(e)}")

    def _export_cross_section_to_laz(self, points):
        """Export cross-section points to a temporary LAZ file with full dimension preservation using PDAL"""
        print(f"[INFO] PDAL EXPORT METHOD: Starting PDAL-based export for {len(points)} points")
        print(f"[INFO] PDAL EXPORT METHOD: This method exports to temporary LAZ file")
        
        try:
            from fileio.pdal_exporter import create_temp_laz_file, find_original_point_indices
        except ImportError:
            print(f"[WARN] PDAL EXPORT METHOD: PDAL modules not available, falling back to basic export")
            return self._basic_export_cross_section_to_laz(points)
            
        try:
            # Get original LAS data and find point indices
            original_las_data = None
            original_points = None
            point_indices = None
            
            if hasattr(self.parent(), 'layer_manager'):
                current_layer_id = self.parent().layer_manager.get_current_layer_id()
                if current_layer_id and current_layer_id in self.parent().layer_manager.layers:
                    layer_data = self.parent().layer_manager.layers[current_layer_id]
                    # Get the full original data structure
                    original_points = layer_data.get('points', None)
                    original_las_dict = layer_data.get('las', None)
                    original_file_path = layer_data.get('file_path', None)
                    
                    if original_las_dict and original_points is not None:
                        # Reconstruct the original data structure
                        original_las_data = {
                            'las': original_las_dict,
                            'points': original_points,
                            'dims': list(original_las_dict.keys()) if original_las_dict else [],
                            'file_path': original_file_path  # Add file path for PDAL
                        }
            
            # Find indices of cross-section points in original data
            if original_points is not None:
                point_indices = find_original_point_indices(points, original_points)
                print(f"[INFO] PDAL EXPORT METHOD: Found {len(point_indices)} matching point indices in original data")
            
            # Create temporary LAZ file with full preservation
            temp_path = create_temp_laz_file(
                points, original_las_data, point_indices, prefix="cross_section"
            )
            
            if temp_path:
                print(f"[INFO] PDAL EXPORT METHOD: Successfully exported with full dimension preservation: {temp_path}")
                return temp_path
            else:
                print("[WARN] PDAL EXPORT METHOD: Advanced PDAL export failed, trying basic export")
                return self._basic_export_cross_section_to_laz(points)
                
        except Exception as e:
            print(f"[ERROR] PDAL EXPORT METHOD: Advanced PDAL export failed: {e}")
            print("[INFO] PDAL EXPORT METHOD: Falling back to basic PDAL export")
            return self._basic_export_cross_section_to_laz(points)
    
    def _basic_export_cross_section_to_laz(self, points):
        """Basic LAZ export fallback using PDAL with text file approach"""
        print(f"[INFO] BASIC PDAL EXPORT METHOD: Starting basic PDAL export for {len(points)} points")
        print(f"[INFO] BASIC PDAL EXPORT METHOD: Using text file -> PDAL -> LAZ approach")
        
        import tempfile
        import os
        try:
            import pdal
            import json
        except ImportError:
            print(f"[ERROR] BASIC PDAL EXPORT METHOD: PDAL library not found")
            QMessageBox.critical(self, "Import Error", "PDAL library not found. Cannot export LAZ file.")
            return None
            
        try:
            # Create temporary text file with points
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as txt_file:
                # Write header
                txt_file.write("X,Y,Z\n")
                # Write points
                for point in points:
                    txt_file.write(f"{point[0]:.6f},{point[1]:.6f},{point[2]:.6f}\n")
                txt_file_path = txt_file.name
            
            # Create temporary LAZ output file
            temp_dir = tempfile.gettempdir()
            temp_filename = f"cross_section_{int(np.random.rand() * 1000000)}.laz"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            try:
                # Create PDAL pipeline for reading text and writing LAZ
                pipeline_config = [
                    {
                        "type": "readers.text",
                        "filename": txt_file_path,
                        "header": "X,Y,Z"
                    },
                    {
                        "type": "writers.las",
                        "filename": temp_path,
                        "compression": "true"
                    }
                ]
                
                # Create and execute pipeline
                pipeline = pdal.Pipeline(json.dumps(pipeline_config))
                count = pipeline.execute()
                
                print(f"[INFO] BASIC PDAL EXPORT METHOD: Successfully exported {count} points to {temp_path}")
                print(f"[INFO] BASIC PDAL EXPORT METHOD: Used text file intermediate: {txt_file_path}")
                return temp_path
                
            finally:
                # Keep temporary text file for debugging - don't clean up
                print(f"[INFO] BASIC PDAL EXPORT METHOD: Text file kept for inspection: {txt_file_path}")
                # try:
                #     os.remove(txt_file_path)
                # except:
                #     pass
            
        except Exception as e:
            print(f"[ERROR] BASIC PDAL EXPORT METHOD: Failed to export cross-section: {e}")
            return None
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        print("[INFO] Profile viewer closed")
        event.accept()
