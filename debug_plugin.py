#!/usr/bin/env python3
"""
Detailed Plugin Class Investigation
"""

import sys
import os
import inspect

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import the plugin manager first
    from plugins.plugin_manager import BasePlugin
    print(f"BasePlugin imported successfully: {BasePlugin}")
    
    # Now test one specific plugin
    import plugins.user_plugins.gridmetrics_plugin as gm
    
    print("\nAll classes in gridmetrics_plugin:")
    for name, obj in inspect.getmembers(gm):
        if inspect.isclass(obj):
            print(f"  {name}: {obj}")
            print(f"    MRO: {obj.__mro__}")
            if hasattr(obj, '__bases__'):
                print(f"    Bases: {obj.__bases__}")
    
    print(f"\nBasePlugin type: {type(BasePlugin)}")
    print(f"BasePlugin: {BasePlugin}")
    
    # Check if GridMetricsPlugin exists
    if hasattr(gm, 'GridMetricsPlugin'):
        plugin_cls = gm.GridMetricsPlugin
        print(f"\nGridMetricsPlugin found: {plugin_cls}")
        print(f"GridMetricsPlugin bases: {plugin_cls.__bases__}")
        print(f"Is subclass of BasePlugin: {issubclass(plugin_cls, BasePlugin)}")
        print(f"Is abstract: {inspect.isabstract(plugin_cls)}")
        print(f"Is same as BasePlugin: {plugin_cls is BasePlugin}")
    else:
        print("\nGridMetricsPlugin not found!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
