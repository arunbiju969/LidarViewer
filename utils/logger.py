"""
LiDAR Viewer Logging System
Provides structured logging with different levels and optional file output
"""

import logging
import os
from datetime import datetime
from typing import Optional

class LidarLogger:
    """
    Structured logging system for LiDAR Viewer
    """
    
    def __init__(self, name: str = "LidarViewer", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Console formatter (simplified for user)
        console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str):
        """Debug level logging"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Info level logging"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Warning level logging"""
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Error level logging"""
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False):
        """Critical level logging"""
        self.logger.critical(message, exc_info=exc_info)
    
    def set_level(self, level: str):
        """Set logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"""
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {level}')
        
        # Update console handler level
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(numeric_level)

# Global logger instance
_global_logger = None

def get_logger() -> LidarLogger:
    """Get the global logger instance"""
    global _global_logger
    if _global_logger is None:
        # Create log file in current directory
        log_file = os.path.join(os.getcwd(), "lidar_viewer.log")
        _global_logger = LidarLogger("LidarViewer", log_file)
    return _global_logger

def log_debug(message: str):
    """Debug logging shortcut"""
    get_logger().debug(message)

def log_info(message: str):
    """Info logging shortcut"""
    get_logger().info(message)

def log_warning(message: str):
    """Warning logging shortcut"""
    get_logger().warning(message)

def log_error(message: str, exc_info: bool = False):
    """Error logging shortcut"""
    get_logger().error(message, exc_info=exc_info)

def log_critical(message: str, exc_info: bool = False):
    """Critical logging shortcut"""
    get_logger().critical(message, exc_info=exc_info)

def set_log_level(level: str):
    """Set global logging level"""
    get_logger().set_level(level)
