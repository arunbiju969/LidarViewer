"""
Plugin Base Classes and Plugin Manager for LiDAR Viewer

This module provides the core plugin architecture, including base classes for different types of plugins
and the plugin manager for loading and managing plugins.
"""

import os
import sys
import json
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal as Signal, QThread
from PyQt6.QtWidgets import QWidget, QDialog, QDockWidget, QMenu
from PyQt6.QtGui import QIcon, QAction

# Import debug control - fall back to regular print if not available
try:
    from utils.debug_control import debug_print
except ImportError:
    def debug_print(message, debug_type="general"):
        if debug_type in ["info", "error"]:
            print(message)
        # Suppress other debug types if debug control not available


class PluginInfo:
    """Container for plugin metadata"""
    
    def __init__(self, name: str, version: str, author: str, description: str, 
                 dependencies: List[str] = None, category: str = "General"):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.dependencies = dependencies or []
        self.category = category
        self.enabled = True
        self.loaded = False


class PluginAPI:
    """API interface provided to plugins to interact with the main application"""
    
    def __init__(self, main_window, viewer, layer_manager, sidebar, plugin_manager=None):
        self.main_window = main_window
        self.viewer = viewer
        self.layer_manager = layer_manager
        self.sidebar = sidebar
        self.plugin_manager = plugin_manager  # Reference to global plugin manager
        
    def get_current_layer(self):
        """Get the currently active layer"""
        layer_id = self.layer_manager.get_current_layer_id()
        if layer_id and layer_id in self.layer_manager.layers:
            return self.layer_manager.layers[layer_id]
        return None
    
    def get_all_layers(self):
        """Get all layers"""
        return self.layer_manager.layers
    
    def get_visible_layers(self):
        """Get all visible layers"""
        return {uid: layer for uid, layer in self.layer_manager.layers.items() 
                if layer.get('visible', False)}
    
    def add_layer(self, name: str, points, las_data=None, visible=True):
        """Add a new layer to the viewer"""
        from layers.layer_db import generate_layer_id
        layer_id = generate_layer_id()
        self.layer_manager.add_layer(layer_id, name, points, las_data, visible=visible, actor=None)
        return layer_id
    
    def update_status(self, message: str):
        """Update the status message in the sidebar"""
        self.sidebar.set_status(message)
    
    def show_message_dialog(self, title: str, message: str):
        """Show a message dialog to the user"""
        self.main_window.show_metadata_dialog(message, title)
    
    def get_plotter(self):
        """Get the PyVista plotter for direct visualization"""
        return self.viewer.plotter if hasattr(self.viewer, 'plotter') else None
    
    def refresh_viewer(self):
        """Refresh the viewer display"""
        self.main_window.plot_all_layers()


class BasePlugin(ABC):
    """Base class for all plugins"""
    
    def __init__(self, api: PluginAPI):
        self.api = api
        self._enabled = True
        self._actions = []
        self._dock_widgets = []
        self._menu_items = []
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Plugin metadata"""
        pass
    
    @abstractmethod
    def activate(self):
        """Called when the plugin is activated"""
        pass
    
    def deactivate(self):
        """Called when the plugin is deactivated"""
        # Remove all UI elements added by this plugin
        self._cleanup_ui()
    
    def _cleanup_ui(self):
        """Clean up UI elements added by this plugin"""
        # Remove actions from toolbars and menus
        for action in self._actions:
            if action.parent():
                action.parent().removeAction(action)
        
        # Remove dock widgets
        for dock in self._dock_widgets:
            if dock.parent():
                dock.parent().removeDockWidget(dock)
        
        # Clear lists
        self._actions.clear()
        self._dock_widgets.clear()
        self._menu_items.clear()
    
    def add_toolbar_action(self, name: str, callback, icon: str = None, tooltip: str = None) -> QAction:
        """Add an action to the main toolbar"""
        action = QAction(name, self.api.main_window)
        if icon and os.path.exists(icon):
            action.setIcon(QIcon(icon))
        if tooltip:
            action.setToolTip(tooltip)
        action.triggered.connect(callback)
        
        # Add to view toolbar if it exists
        if hasattr(self.api.main_window, 'view_toolbar'):
            self.api.main_window.view_toolbar.addAction(action)
        
        self._actions.append(action)
        return action
    
    def add_menu_item(self, menu_name: str, action_name: str, callback, shortcut: str = None) -> QAction:
        """Add a menu item to the main menu bar"""
        menubar = self.api.main_window.menuBar()
        
        # Find or create menu
        menu = None
        for action in menubar.actions():
            if action.text() == menu_name:
                menu = action.menu()
                break
        
        if not menu:
            menu = menubar.addMenu(menu_name)
        
        # Add action
        action = menu.addAction(action_name)
        action.triggered.connect(callback)
        if shortcut:
            action.setShortcut(shortcut)
        
        self._actions.append(action)
        return action
    
    def add_dock_widget(self, name: str, widget: QWidget, area=None, visible: bool = True) -> QDockWidget:
        """Add a dockable widget to the main window, replacing any existing visible dock"""
        from PyQt6.QtCore import Qt
        
        if area is None:
            area = Qt.RightDockWidgetArea
        
        debug_print(f"[DEBUG] add_dock_widget called for '{name}', area={area}, visible={visible}", "plugin")
        
        # Get the plugin manager from the API to manage dock widgets globally
        plugin_manager = getattr(self.api, 'plugin_manager', None)
        if plugin_manager:
            debug_print(f"[DEBUG] Global plugin manager _dock_widgets count: {len(plugin_manager._dock_widgets)}", "plugin")
        else:
            debug_print(f"[DEBUG] No plugin manager reference found in API", "plugin")
        
        # Close any existing visible dock widgets in the same area to avoid stacking
        self._close_existing_docks_in_area(area)
        
        dock = QDockWidget(name, self.api.main_window)
        dock.setWidget(widget)
        
        debug_print(f"[DEBUG] Created new dock widget: '{name}'", "plugin")
        
        # Set minimum width for better layout - increased for proper button/path display
        dock.setMinimumWidth(400)  # Increased from 350 to 400
        
        # Apply theme-aware styling based on current theme
        dock_style = self._get_dock_theme_style()
        dock.setStyleSheet(dock_style)
        
        debug_print(f"[DEBUG] Adding dock widget '{name}' to main window area {area}", "plugin")
        self.api.main_window.addDockWidget(area, dock)
        
        # Set visibility based on parameter
        if not visible:
            dock.hide()
            debug_print(f"[DEBUG] Hidden dock widget '{name}' as requested", "plugin")
        else:
            debug_print(f"[DEBUG] Dock widget '{name}' set to visible", "plugin")
        
        # Add to both plugin-specific and global lists
        self._dock_widgets.append(dock)
        if plugin_manager and hasattr(plugin_manager, '_dock_widgets'):
            plugin_manager._dock_widgets.append(dock)
            debug_print(f"[DEBUG] Added to global _dock_widgets list. New count: {len(plugin_manager._dock_widgets)}", "plugin")
        else:
            debug_print(f"[DEBUG] Could not add to global _dock_widgets list", "plugin")
        
        debug_print(f"[DEBUG] Added to plugin _dock_widgets list. New count: {len(self._dock_widgets)}", "plugin")
        return dock
    
    def _close_existing_docks_in_area(self, area):
        """Close any existing visible dock widgets in the specified area"""
        debug_print(f"[DEBUG] _close_existing_docks_in_area called for area {area}", "plugin")
        try:
            # Get all dock widgets from the main window
            main_window = self.api.main_window
            all_docks = main_window.findChildren(QDockWidget)
            
            debug_print(f"[DEBUG] Found {len(all_docks)} total dock widgets in main window", "plugin")
            
            visible_docks_in_area = []
            for dock in all_docks:
                dock_area = main_window.dockWidgetArea(dock)
                is_visible = dock.isVisible()
                debug_print(f"[DEBUG] Dock '{dock.windowTitle()}': area={dock_area}, visible={is_visible}", "plugin")
                
                # Check if dock is in the same area and is visible
                if is_visible and dock_area == area:
                    visible_docks_in_area.append(dock)
                    debug_print(f"[DEBUG] Found dock to hide: '{dock.windowTitle()}'", "plugin")
            
            debug_print(f"[DEBUG] Found {len(visible_docks_in_area)} visible dock widgets in target area", "plugin")
            
            for dock in visible_docks_in_area:
                # Hide the existing dock instead of closing to preserve state
                dock.hide()
                debug_print(f"[INFO] Hiding existing dock widget: {dock.windowTitle()}", "plugin")
                    
        except Exception as e:
            debug_print(f"[DEBUG] Error closing existing docks: {e}", "plugin")
            import traceback
            traceback.print_exc()
    
    def show_dock_widget(self, dock_widget_name=None):
        """Show this plugin's dock widget and hide others in the same area"""
        if not hasattr(self, 'dock_widget') or not self.dock_widget:
            debug_print(f"[DEBUG] No dock widget found for plugin", "plugin")
            return False
        
        dock_name = dock_widget_name or self.dock_widget.windowTitle()
        debug_print(f"[DEBUG] BasePlugin.show_dock_widget called for '{dock_name}'", "plugin")
        
        try:
            main_window = self.api.main_window
            target_area = main_window.dockWidgetArea(self.dock_widget)
            
            # Hide other visible dock widgets in the same area
            all_docks = main_window.findChildren(QDockWidget)
            for dock in all_docks:
                dock_area = main_window.dockWidgetArea(dock)
                if dock != self.dock_widget and dock.isVisible() and dock_area == target_area:
                    dock.hide()
                    debug_print(f"[DEBUG] BasePlugin: Hiding dock widget '{dock.windowTitle()}'", "plugin")
            
            # Show this plugin's dock widget
            self.dock_widget.show()
            self.dock_widget.raise_()
            debug_print(f"[INFO] BasePlugin: Showed dock widget '{dock_name}'", "plugin")
            return True
            
        except Exception as e:
            print(f"[ERROR] BasePlugin: Error showing dock widget '{dock_name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _get_dock_theme_style(self):
        """Get theme-appropriate styling for dock widgets"""
        try:
            # Check current theme from main window
            if (hasattr(self.api.main_window, 'sidebar') and 
                hasattr(self.api.main_window.sidebar, 'theme_box')):
                current_theme = self.api.main_window.sidebar.theme_box.currentText()
                
                if current_theme.lower() == "dark":
                    return """
                        QDockWidget {
                            margin-left: 8px;
                            margin-right: 8px;
                            background-color: #181a1b;
                            color: white;
                            border: 2px solid #3daee9;
                            border-radius: 8px;
                        }
                        QDockWidget::title {
                            background-color: #3daee9;
                            color: white;
                            padding: 4px;
                            text-align: center;
                            font-weight: bold;
                        }
                    """
        except Exception as e:
            debug_print(f"[DEBUG] Plugin dock theme detection failed: {e}", "plugin")
        
        # Default light theme styling
        return """
            QDockWidget {
                margin-left: 8px;
                margin-right: 8px;
            }
        """
        
        # Set visibility based on parameter
        if not visible:
            dock.hide()
        
        self._dock_widgets.append(dock)
        return dock


class AnalysisPlugin(BasePlugin):
    """Base class for data analysis plugins"""
    
    def __init__(self, api: PluginAPI):
        super().__init__(api)
        self.results = {}
    
    @abstractmethod
    def analyze(self, layer_data) -> Dict[str, Any]:
        """Perform analysis on layer data"""
        pass
    
    def save_results(self, filepath: str):
        """Save analysis results to file"""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)


class VisualizationPlugin(BasePlugin):
    """Base class for visualization plugins"""
    
    def __init__(self, api: PluginAPI):
        super().__init__(api)
        self.actors = []
    
    @abstractmethod
    def create_visualization(self, layer_data):
        """Create visualization actors"""
        pass
    
    def clear_visualization(self):
        """Remove all visualization actors"""
        plotter = self.api.get_plotter()
        if plotter:
            for actor in self.actors:
                try:
                    plotter.remove_actor(actor)
                except:
                    pass
        self.actors.clear()


class FilterPlugin(BasePlugin):
    """Base class for data filtering plugins"""
    
    @abstractmethod
    def filter_points(self, points, **kwargs):
        """Filter point cloud data"""
        pass


class ExportPlugin(BasePlugin):
    """Base class for export/import plugins"""
    
    @abstractmethod
    def export_data(self, data, filepath: str, **kwargs):
        """Export data to file"""
        pass
    
    def import_data(self, filepath: str, **kwargs):
        """Import data from file (optional)"""
        pass


class PluginManager(QObject):
    """Manages loading, activating, and deactivating plugins"""
    
    plugin_loaded = Signal(object)  # Emitted when a plugin is loaded
    plugin_activated = Signal(object)  # Emitted when a plugin is activated
    plugin_deactivated = Signal(object)  # Emitted when a plugin is deactivated
    plugin_error = Signal(str, str)  # Emitted when there's a plugin error (plugin_name, error_msg)
    
    def __init__(self, api: PluginAPI):
        super().__init__()
        self.api = api
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_modules = {}
        self.plugin_paths = []
        self._dock_widgets = []  # Global dock widget tracking
        
        # Default plugin directories
        self.add_plugin_path(os.path.join(os.path.dirname(__file__), 'built_in'))
        self.add_plugin_path(os.path.join(os.path.dirname(__file__), 'user_plugins'))
    
    def add_plugin_path(self, path: str):
        """Add a directory to search for plugins"""
        if os.path.exists(path) and path not in self.plugin_paths:
            self.plugin_paths.append(path)
            # Add to Python path for imports
            if path not in sys.path:
                sys.path.insert(0, path)
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugin files"""
        plugins = []
        
        for plugin_path in self.plugin_paths:
            if not os.path.exists(plugin_path):
                continue
                
            for item in os.listdir(plugin_path):
                item_path = os.path.join(plugin_path, item)
                
                # Look for Python files
                if item.endswith('.py') and not item.startswith('_'):
                    plugins.append(item_path)
                
                # Look for plugin packages (directories with __init__.py)
                elif os.path.isdir(item_path):
                    init_file = os.path.join(item_path, '__init__.py')
                    if os.path.exists(init_file):
                        plugins.append(init_file)
        
        return plugins
    
    def load_plugin(self, plugin_path: str) -> Optional[BasePlugin]:
        """Load a single plugin from file"""
        try:
            # Determine module name and spec
            if plugin_path.endswith('__init__.py'):
                module_name = os.path.basename(os.path.dirname(plugin_path))
                spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            else:
                module_name = os.path.splitext(os.path.basename(plugin_path))[0]
                spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot create spec for {plugin_path}")
            
            # Import the module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find plugin classes that inherit from BasePlugin
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BasePlugin) and 
                    obj is not BasePlugin and
                    not inspect.isabstract(obj)):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                print(f"[WARN] No plugin classes found in {plugin_path}")
                return None
            
            # Use the first valid plugin class
            plugin_class = plugin_classes[0]
            plugin_instance = plugin_class(self.api)
            
            # Store references
            plugin_name = plugin_instance.info.name
            self.plugins[plugin_name] = plugin_instance
            self.plugin_modules[plugin_name] = module
            
            self.plugin_loaded.emit(plugin_instance)
            print(f"[INFO] Loaded plugin: {plugin_name} v{plugin_instance.info.version}")
            return plugin_instance
            
        except Exception as e:
            error_msg = f"Failed to load plugin from {plugin_path}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.plugin_error.emit(os.path.basename(plugin_path), error_msg)
            return None
    
    def load_all_plugins(self):
        """Discover and load all plugins"""
        plugin_files = self.discover_plugins()
        loaded_count = 0
        
        for plugin_file in plugin_files:
            plugin = self.load_plugin(plugin_file)
            if plugin:
                loaded_count += 1
        
        print(f"[INFO] Loaded {loaded_count} plugins from {len(plugin_files)} files found")
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """Activate a loaded plugin"""
        debug_print(f"[DEBUG] activate_plugin called for '{plugin_name}'", "plugin")
        
        if plugin_name not in self.plugins:
            print(f"[ERROR] Plugin '{plugin_name}' not found")
            return False
        
        plugin = self.plugins[plugin_name]
        debug_print(f"[DEBUG] Found plugin instance: {type(plugin).__name__}", "plugin")
        
        try:
            debug_print(f"[DEBUG] Calling activate() on plugin '{plugin_name}'", "plugin")
            plugin.activate()
            plugin.info.enabled = True
            self.plugin_activated.emit(plugin)
            print(f"[INFO] Activated plugin: {plugin_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to activate plugin '{plugin_name}': {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            self.plugin_error.emit(plugin_name, error_msg)
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """Deactivate an active plugin"""
        if plugin_name not in self.plugins:
            print(f"[ERROR] Plugin '{plugin_name}' not found")
            return False
        
        plugin = self.plugins[plugin_name]
        
        try:
            plugin.deactivate()
            plugin.info.enabled = False
            self.plugin_deactivated.emit(plugin)
            print(f"[INFO] Deactivated plugin: {plugin_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to deactivate plugin '{plugin_name}': {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.plugin_error.emit(plugin_name, error_msg)
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin by name"""
        return self.plugins.get(plugin_name)
    
    def get_plugins_by_category(self, category: str) -> List[BasePlugin]:
        """Get all plugins in a specific category"""
        return [plugin for plugin in self.plugins.values() 
                if plugin.info.category == category]
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all loaded plugins"""
        return self.plugins.copy()
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin (deactivate, reload module, reactivate)"""
        if plugin_name not in self.plugins:
            print(f"[ERROR] Plugin '{plugin_name}' not found")
            return False
        
        # Deactivate first
        was_active = self.plugins[plugin_name].info.enabled
        if was_active:
            self.deactivate_plugin(plugin_name)
        
        try:
            # Reload the module
            module = self.plugin_modules[plugin_name]
            importlib.reload(module)
            
            # Find the plugin class again
            plugin_classes = [obj for name, obj in inspect.getmembers(module)
                            if (inspect.isclass(obj) and 
                                issubclass(obj, BasePlugin) and 
                                obj is not BasePlugin and
                                not inspect.isabstract(obj))]
            
            if plugin_classes:
                # Create new instance
                plugin_class = plugin_classes[0]
                new_plugin = plugin_class(self.api)
                self.plugins[plugin_name] = new_plugin
                
                # Reactivate if it was active
                if was_active:
                    self.activate_plugin(plugin_name)
                
                print(f"[INFO] Reloaded plugin: {plugin_name}")
                return True
            
        except Exception as e:
            error_msg = f"Failed to reload plugin '{plugin_name}': {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.plugin_error.emit(plugin_name, error_msg)
            return False
        
        return False


# Utility functions for plugin developers
def get_plugin_data_dir(plugin_name: str) -> str:
    """Get a data directory for storing plugin-specific files"""
    data_dir = os.path.join(os.path.dirname(__file__), 'plugin_data', plugin_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_plugin_config_file(plugin_name: str) -> str:
    """Get a config file path for a plugin"""
    data_dir = get_plugin_data_dir(plugin_name)
    return os.path.join(data_dir, 'config.json')


def load_plugin_config(plugin_name: str, default_config: Dict = None) -> Dict:
    """Load plugin configuration from file"""
    config_file = get_plugin_config_file(plugin_name)
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load config for plugin '{plugin_name}': {e}")
    
    return default_config or {}


def save_plugin_config(plugin_name: str, config: Dict):
    """Save plugin configuration to file"""
    config_file = get_plugin_config_file(plugin_name)
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save config for plugin '{plugin_name}': {e}")
