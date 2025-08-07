"""
LiDAR Viewer Exception Handling System
Provides custom exceptions and error handling utilities
"""

from typing import Optional, Any
from utils.logger import log_error, log_warning

class LidarViewerException(Exception):
    """Base exception for LiDAR Viewer specific errors"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        log_error(f"LidarViewerException: {message} (code: {error_code})")

class LayerLoadError(LidarViewerException):
    """Raised when layer loading fails"""
    
    def __init__(self, file_path: str, reason: str):
        super().__init__(f"Failed to load layer: {file_path} - {reason}", "LAYER_LOAD_ERROR")
        self.file_path = file_path
        self.reason = reason

class VisualizationError(LidarViewerException):
    """Raised when visualization operations fail"""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(f"Visualization error during {operation}: {reason}", "VIZ_ERROR")
        self.operation = operation
        self.reason = reason

class PerformanceWarning(Warning):
    """Warning for performance-related issues"""
    pass

def safe_execute(func, *args, fallback_value=None, error_message: Optional[str] = None, **kwargs):
    """
    Safely execute a function with proper error handling
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        fallback_value: Value to return if function fails
        error_message: Custom error message
        **kwargs: Keyword arguments for the function
    
    Returns:
        Function result or fallback_value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_message:
            log_error(f"{error_message}: {str(e)}")
        else:
            log_error(f"Error executing {func.__name__}: {str(e)}")
        return fallback_value

def handle_layer_load_error(file_path: str, exception: Exception) -> LayerLoadError:
    """
    Convert generic exceptions to specific layer load errors
    """
    error_str = str(exception).lower()
    
    if "no such file" in error_str or "not found" in error_str:
        return LayerLoadError(file_path, "File not found")
    elif "permission" in error_str or "access" in error_str:
        return LayerLoadError(file_path, "Permission denied")
    elif "memory" in error_str or "allocation" in error_str:
        return LayerLoadError(file_path, "Insufficient memory")
    elif "format" in error_str or "invalid" in error_str:
        return LayerLoadError(file_path, "Invalid file format")
    else:
        return LayerLoadError(file_path, f"Unknown error: {str(exception)}")

def warn_performance_issue(operation: str, point_count: int, threshold: int = 1000000):
    """
    Issue performance warning for large datasets
    """
    if point_count > threshold:
        message = f"Performance warning: {operation} with {point_count:,} points may be slow"
        log_warning(message)
        import warnings
        warnings.warn(message, PerformanceWarning)

class ErrorHandler:
    """Context manager for structured error handling"""
    
    def __init__(self, operation: str, show_user_message: bool = True):
        self.operation = operation
        self.show_user_message = show_user_message
        self.success = True
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.success = False
            self.error = exc_val
            log_error(f"Error in {self.operation}: {str(exc_val)}", exc_info=True)
            
            if self.show_user_message:
                self._show_user_error(exc_val)
            
            # Suppress the exception (return True)
            return True
        return False
    
    def _show_user_error(self, error: Exception):
        """Show user-friendly error message"""
        try:
            from PySide6.QtWidgets import QMessageBox
            
            if isinstance(error, LayerLoadError):
                QMessageBox.critical(None, "Layer Load Error", 
                                   f"Could not load layer:\n{error.file_path}\n\nReason: {error.reason}")
            elif isinstance(error, VisualizationError):
                QMessageBox.critical(None, "Visualization Error", 
                                   f"Error during {error.operation}:\n{error.reason}")
            else:
                QMessageBox.critical(None, "Error", 
                                   f"An error occurred during {self.operation}:\n{str(error)}")
        except ImportError:
            # Qt not available, just log
            log_error(f"User error message (Qt not available): {str(error)}")

# Decorator for safe method execution
def safe_method(fallback_value=None, error_message: Optional[str] = None):
    """
    Decorator to safely execute methods with error handling
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            return safe_execute(func, *args, fallback_value=fallback_value, 
                              error_message=error_message, **kwargs)
        return wrapper
    return decorator
