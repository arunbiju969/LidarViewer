"""
Plugin Manager Dialog

Provides a GUI interface for managing plugins - viewing, enabling/disabling, 
and configuring plugins.
"""

import os
from typing import Dict, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QTextEdit, QGroupBox, QCheckBox, QSplitter,
    QMessageBox, QHeaderView, QLineEdit, QComboBox, QFormLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from .plugin_manager import PluginManager, BasePlugin


class PluginInfoWidget(QGroupBox):
    """Widget to display detailed information about a selected plugin"""
    
    def __init__(self, parent=None):
        super().__init__("Plugin Information", parent)
        self.setup_ui()
        self.current_plugin = None
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Basic info
        info_layout = QFormLayout()
        self.name_label = QLabel("-")
        self.version_label = QLabel("-")
        self.author_label = QLabel("-")
        self.category_label = QLabel("-")
        
        info_layout.addRow("Name:", self.name_label)
        info_layout.addRow("Version:", self.version_label)
        info_layout.addRow("Author:", self.author_label)
        info_layout.addRow("Category:", self.category_label)
        
        layout.addLayout(info_layout)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setReadOnly(True)
        self.description_edit.setMaximumHeight(100)
        layout.addWidget(QLabel("Description:"))
        layout.addWidget(self.description_edit)
        
        # Dependencies
        self.dependencies_label = QLabel("-")
        layout.addWidget(QLabel("Dependencies:"))
        layout.addWidget(self.dependencies_label)
        
        # Status
        self.status_label = QLabel("-")
        self.status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_label)
    
    def update_info(self, plugin: BasePlugin):
        """Update the display with plugin information"""
        self.current_plugin = plugin
        
        if plugin is None:
            self.clear_info()
            return
        
        info = plugin.info
        self.name_label.setText(info.name)
        self.version_label.setText(info.version)
        self.author_label.setText(info.author)
        self.category_label.setText(info.category)
        self.description_edit.setPlainText(info.description)
        
        # Dependencies
        if info.dependencies:
            deps_text = ", ".join(info.dependencies)
        else:
            deps_text = "None"
        self.dependencies_label.setText(deps_text)
        
        # Status
        if info.enabled:
            self.status_label.setText("Active")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("Inactive")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def clear_info(self):
        """Clear all information"""
        self.name_label.setText("-")
        self.version_label.setText("-")
        self.author_label.setText("-")
        self.category_label.setText("-")
        self.description_edit.setPlainText("")
        self.dependencies_label.setText("-")
        self.status_label.setText("-")
        self.status_label.setStyleSheet("font-weight: bold;")


class PluginManagerDialog(QDialog):
    """Dialog for managing plugins in the LiDAR viewer"""
    
    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setup_ui()
        self.refresh_plugin_list()
        
        # Connect plugin manager signals
        self.plugin_manager.plugin_loaded.connect(self.refresh_plugin_list)
        self.plugin_manager.plugin_activated.connect(self.refresh_plugin_list)
        self.plugin_manager.plugin_deactivated.connect(self.refresh_plugin_list)
        self.plugin_manager.plugin_error.connect(self.show_plugin_error)
    
    def setup_ui(self):
        self.setWindowTitle("Plugin Manager")
        self.setModal(False)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        # Left side - plugin list
        left_widget = QGroupBox("Available Plugins")
        left_layout = QVBoxLayout(left_widget)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Search plugins...")
        self.filter_edit.textChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.filter_edit)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self.filter_plugins)
        filter_layout.addWidget(self.category_filter)
        
        left_layout.addLayout(filter_layout)
        
        # Plugin tree
        self.plugin_tree = QTreeWidget()
        self.plugin_tree.setHeaderLabels(["Plugin", "Version", "Status", "Category"])
        self.plugin_tree.itemSelectionChanged.connect(self.on_plugin_selected)
        self.plugin_tree.itemChanged.connect(self.on_plugin_toggled)
        left_layout.addWidget(self.plugin_tree)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_plugins)
        
        self.activate_button = QPushButton("Activate")
        self.activate_button.clicked.connect(self.activate_selected_plugin)
        self.activate_button.setEnabled(False)
        
        self.deactivate_button = QPushButton("Deactivate")
        self.deactivate_button.clicked.connect(self.deactivate_selected_plugin)
        self.deactivate_button.setEnabled(False)
        
        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.reload_selected_plugin)
        self.reload_button.setEnabled(False)
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.activate_button)
        button_layout.addWidget(self.deactivate_button)
        button_layout.addWidget(self.reload_button)
        button_layout.addStretch()
        
        left_layout.addLayout(button_layout)
        
        splitter.addWidget(left_widget)
        
        # Right side - plugin details
        self.plugin_info = PluginInfoWidget()
        splitter.addWidget(self.plugin_info)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.close_button)
        
        layout.addLayout(bottom_layout)
    
    def refresh_plugins(self):
        """Reload all plugins from disk"""
        # Load new plugins
        self.plugin_manager.load_all_plugins()
        self.refresh_plugin_list()
    
    def refresh_plugin_list(self):
        """Refresh the plugin list display"""
        self.plugin_tree.clear()
        
        # Update category filter
        categories = set()
        for plugin in self.plugin_manager.get_all_plugins().values():
            categories.add(plugin.info.category)
        
        current_category = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem("All Categories")
        for category in sorted(categories):
            self.category_filter.addItem(category)
        
        # Restore category selection
        index = self.category_filter.findText(current_category)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        
        # Populate tree
        for plugin_name, plugin in self.plugin_manager.get_all_plugins().items():
            self.add_plugin_to_tree(plugin)
        
        # Expand all and resize columns
        self.plugin_tree.expandAll()
        header = self.plugin_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    
    def add_plugin_to_tree(self, plugin: BasePlugin):
        """Add a plugin to the tree widget"""
        info = plugin.info
        
        # Find or create category item
        category_item = None
        for i in range(self.plugin_tree.topLevelItemCount()):
            item = self.plugin_tree.topLevelItem(i)
            if item.text(0) == info.category:
                category_item = item
                break
        
        if category_item is None:
            category_item = QTreeWidgetItem([info.category, "", "", ""])
            font = QFont()
            font.setBold(True)
            category_item.setFont(0, font)
            self.plugin_tree.addTopLevelItem(category_item)
        
        # Add plugin item
        status = "Active" if info.enabled else "Inactive"
        plugin_item = QTreeWidgetItem([info.name, info.version, status, ""])
        plugin_item.setData(0, Qt.UserRole, plugin)
        
        # Add checkbox for enable/disable
        plugin_item.setFlags(plugin_item.flags() | Qt.ItemIsUserCheckable)
        plugin_item.setCheckState(0, Qt.Checked if info.enabled else Qt.Unchecked)
        
        # Color coding
        if info.enabled:
            plugin_item.setForeground(2, plugin_item.foreground(0))
        else:
            from PyQt6.QtGui import QColor
            plugin_item.setForeground(2, QColor("red"))
        
        category_item.addChild(plugin_item)
    
    def filter_plugins(self):
        """Filter plugins based on search text and category"""
        search_text = self.filter_edit.text().lower()
        selected_category = self.category_filter.currentText()
        
        for i in range(self.plugin_tree.topLevelItemCount()):
            category_item = self.plugin_tree.topLevelItem(i)
            category_name = category_item.text(0)
            
            # Check if category should be visible
            category_visible = (selected_category == "All Categories" or 
                              selected_category == category_name)
            
            if not category_visible:
                category_item.setHidden(True)
                continue
            
            # Check plugins in this category
            plugins_visible = False
            for j in range(category_item.childCount()):
                plugin_item = category_item.child(j)
                plugin_name = plugin_item.text(0).lower()
                
                # Show plugin if it matches search
                plugin_visible = search_text in plugin_name
                plugin_item.setHidden(not plugin_visible)
                
                if plugin_visible:
                    plugins_visible = True
            
            # Hide category if no plugins are visible
            category_item.setHidden(not plugins_visible)
    
    def on_plugin_selected(self):
        """Handle plugin selection in the tree"""
        current_item = self.plugin_tree.currentItem()
        
        if current_item is None or current_item.parent() is None:
            # Category item selected or nothing selected
            self.plugin_info.clear_info()
            self.activate_button.setEnabled(False)
            self.deactivate_button.setEnabled(False)
            self.reload_button.setEnabled(False)
            return
        
        # Plugin item selected
        plugin = current_item.data(0, Qt.UserRole)
        self.plugin_info.update_info(plugin)
        
        # Update button states
        self.activate_button.setEnabled(not plugin.info.enabled)
        self.deactivate_button.setEnabled(plugin.info.enabled)
        self.reload_button.setEnabled(True)
    
    def on_plugin_toggled(self, item, column):
        """Handle plugin checkbox toggle"""
        if item.parent() is None:
            return  # Category item, ignore
        
        plugin = item.data(0, Qt.UserRole)
        if plugin is None:
            return
        
        if item.checkState(0) == Qt.Checked:
            self.plugin_manager.activate_plugin(plugin.info.name)
        else:
            self.plugin_manager.deactivate_plugin(plugin.info.name)
        
        # Refresh the display
        QTimer.singleShot(100, self.refresh_plugin_list)
    
    def activate_selected_plugin(self):
        """Activate the selected plugin"""
        current_item = self.plugin_tree.currentItem()
        if current_item and current_item.parent() is not None:
            plugin = current_item.data(0, Qt.UserRole)
            self.plugin_manager.activate_plugin(plugin.info.name)
    
    def deactivate_selected_plugin(self):
        """Deactivate the selected plugin"""
        current_item = self.plugin_tree.currentItem()
        if current_item and current_item.parent() is not None:
            plugin = current_item.data(0, Qt.UserRole)
            self.plugin_manager.deactivate_plugin(plugin.info.name)
    
    def reload_selected_plugin(self):
        """Reload the selected plugin"""
        current_item = self.plugin_tree.currentItem()
        if current_item and current_item.parent() is not None:
            plugin = current_item.data(0, Qt.UserRole)
            self.plugin_manager.reload_plugin(plugin.info.name)
    
    def show_plugin_error(self, plugin_name: str, error_msg: str):
        """Show plugin error message"""
        QMessageBox.critical(self, f"Plugin Error - {plugin_name}", 
                           f"Plugin error occurred:\n\n{error_msg}")
