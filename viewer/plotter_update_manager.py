"""
Plotter Update Manager - Optimizes PyVista plotter updates
Reduces unnecessary redraws and improves performance
"""

from PyQt6.QtCore import QTimer
from typing import Optional

class PlotterUpdateManager:
    """
    Manages plotter updates to reduce frequency and improve performance
    """
    
    def __init__(self, plotter):
        self.plotter = plotter
        self._update_pending = False
        self._batch_mode = False
        self._debounce_timer = None
        self._debounce_delay = 50  # milliseconds
        
    def request_update(self, immediate: bool = False):
        """
        Request a plotter update
        
        Args:
            immediate: If True, update immediately regardless of batch mode
        """
        if immediate:
            self._perform_update()
        elif self._batch_mode:
            self._update_pending = True
        else:
            self._debounced_update()
    
    def _debounced_update(self):
        """Debounce rapid update requests"""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        
        self._debounce_timer = QTimer()
        self._debounce_timer.timeout.connect(self._perform_update)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.start(self._debounce_delay)
    
    def _perform_update(self):
        """Actually perform the plotter update"""
        if hasattr(self.plotter, 'update'):
            self.plotter.update()
        self._update_pending = False
        if self._debounce_timer is not None:
            self._debounce_timer = None
    
    def start_batch_mode(self):
        """Start batching updates - no updates will occur until end_batch_mode"""
        self._batch_mode = True
        self._update_pending = False
        print("[DEBUG] PlotterUpdateManager: Started batch mode")
    
    def end_batch_mode(self):
        """End batching and perform update if one was requested"""
        self._batch_mode = False
        if self._update_pending:
            self._perform_update()
            print("[DEBUG] PlotterUpdateManager: Ended batch mode with update")
        else:
            print("[DEBUG] PlotterUpdateManager: Ended batch mode without update")
    
    def is_batch_mode(self) -> bool:
        """Check if currently in batch mode"""
        return self._batch_mode
    
    def set_debounce_delay(self, delay_ms: int):
        """Set the debounce delay in milliseconds"""
        self._debounce_delay = max(10, delay_ms)  # Minimum 10ms
