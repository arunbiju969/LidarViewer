"""
Debug Control System for LiDAR Viewer
Simple module to control debug output verbosity
"""

# Global debug flags - can be modified at runtime
DEBUG_VERBOSE = False    # General debug messages
PLUGIN_DEBUG = False     # Plugin-specific debug messages
LAYER_DEBUG = False      # Layer management debug messages

def set_debug_level(level="minimal"):
    """
    Set overall debug verbosity level
    
    Args:
        level (str): 'minimal', 'normal', 'verbose', 'all'
    """
    global DEBUG_VERBOSE, PLUGIN_DEBUG, LAYER_DEBUG
    
    if level == "minimal":
        DEBUG_VERBOSE = False
        PLUGIN_DEBUG = False  
        LAYER_DEBUG = False
    elif level == "normal":
        DEBUG_VERBOSE = False
        PLUGIN_DEBUG = False
        LAYER_DEBUG = True
    elif level == "verbose":
        DEBUG_VERBOSE = True
        PLUGIN_DEBUG = False
        LAYER_DEBUG = True
    elif level == "all":
        DEBUG_VERBOSE = True
        PLUGIN_DEBUG = True
        LAYER_DEBUG = True

def debug_print(message, debug_type="general"):
    """
    Print debug messages only if debugging is enabled for that type
    
    Args:
        message (str): Debug message to print
        debug_type (str): Type of debug message ('general', 'plugin', 'layer', 'info')
    """
    if debug_type == "plugin" and PLUGIN_DEBUG:
        print(message)
    elif debug_type == "layer" and LAYER_DEBUG:
        print(message)
    elif debug_type == "general" and DEBUG_VERBOSE:
        print(message)
    elif debug_type == "info":  # Always print INFO messages
        print(message)

# Set default to minimal verbosity
set_debug_level("minimal")
