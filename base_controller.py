import customtkinter as ctk
from typing import Dict, Optional
from ui_components import ButtonSpinner

class BaseController:
    """
    A base class for controllers to share common functionality, particularly
    for managing the UI state during long-running, asynchronous operations.
    """
    def __init__(self, app: 'CodeMergerApp'):
        self.app = app
        self.spinners: Dict[ctk.CTkButton, ButtonSpinner] = {}

    def _start_long_process(self) -> None:
        """
        Signals the main app to show the global progress overlay.
        The calling function is responsible for disabling its own button.
        """
        self.app.show_progress_overlay()

    def _stop_long_process(self) -> None:
        """
        Signals the main app to hide the global progress overlay.
        The calling function is responsible for re-enabling its own button.
        """
        self.app.hide_progress_overlay()
        
    import contextlib

    @contextlib.contextmanager
    def long_process(self):
        """Context manager to safely show/hide progress overlay even if exceptions occur."""
        self._start_long_process()
        try:
            yield
        finally:
            self._stop_long_process()

    def update_theme(self) -> None:
        """
        Updates the UI theme. 
        Override this method in subclasses that need to react to theme changes.
        """
        pass