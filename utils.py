import os
import json
import keyring
import sys
import logging
import traceback
import time
from functools import wraps
from logging.handlers import RotatingFileHandler
from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound
from typing import Optional, Any, List, Callable
from design_system import DS

# =============================================================================
# --- PERFORMANCE UTILITIES ---
# =============================================================================

class PerformanceSettings:
    """
    Global performance settings that can be toggled to reduce animations
    and improve responsiveness on lower-end systems.
    """
    _instance = None
    
    def __new__(cls) -> 'PerformanceSettings':
        if cls._instance is None:
            cls._instance = super(PerformanceSettings, cls).__new__(cls)
            cls._instance._init_settings()
        return cls._instance
    
    def _init_settings(self) -> None:
        """Initialize default performance settings."""
        self.reduce_animations = False  # When True, animations are faster/skipped
        self.animation_speed_multiplier = 1.0  # Lower = faster animations
    
    def enable_reduced_motion(self) -> None:
        """Enable reduced motion mode for better performance."""
        self.reduce_animations = True
        self.animation_speed_multiplier = 0.3
    
    def disable_reduced_motion(self) -> None:
        """Disable reduced motion mode (normal animations)."""
        self.reduce_animations = False
        self.animation_speed_multiplier = 1.0


def debounce(wait_ms: int) -> Callable:
    """
    Decorator to delay function execution until wait_ms after the last call.
    Useful for expensive operations triggered by rapid events (e.g., keystrokes).
    
    Args:
        wait_ms: Milliseconds to wait after the last call before executing.
    
    Example:
        @debounce(150)
        def on_search_change(self, event):
            # This only runs 150ms after the user stops typing
            self.filter_results()
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def debounced(self, *args, **kwargs):
            attr_name = f'_debounce_job_{fn.__name__}'
            # Cancel any existing scheduled call
            if hasattr(self, attr_name) and getattr(self, attr_name) is not None:
                try:
                    self.after_cancel(getattr(self, attr_name))
                except Exception:
                    pass  # Widget may not have after_cancel or job already executed
            # Schedule a new call
            job_id = self.after(wait_ms, lambda: fn(self, *args, **kwargs))
            setattr(self, attr_name, job_id)
        return debounced
    return decorator


def throttle(wait_ms: int) -> Callable:
    """
    Decorator to limit function execution to at most once per wait_ms.
    Unlike debounce, this executes immediately on the first call.
    
    Args:
        wait_ms: Minimum milliseconds between function executions.
    
    Example:
        @throttle(50)
        def on_scroll(self, event):
            # Only executes once per 50ms, no matter how fast user scrolls
            self.redraw_canvas()
    """
    def decorator(fn: Callable) -> Callable:
        last_call_time = [0.0]  # Mutable container for closure
        
        @wraps(fn)
        def throttled(self, *args, **kwargs):
            now = time.time() * 1000  # Current time in ms
            if now - last_call_time[0] >= wait_ms:
                last_call_time[0] = now
                return fn(self, *args, **kwargs)
        return throttled
    return decorator


def schedule_idle(fn: Callable) -> Callable:
    """
    Decorator to schedule a function to run after current events are processed.
    Useful for deferring UI updates to avoid blocking the main thread.
    
    Example:
        @schedule_idle
        def expensive_ui_update(self):
            # Runs after current event processing completes
            self.update_all_widgets()
    """
    @wraps(fn)
    def deferred(self, *args, **kwargs):
        self.after_idle(lambda: fn(self, *args, **kwargs))
    return deferred

# --- CONFIGURATION ---
APP_VERSION = "1.0"
KEYRING_SERVICE_NAME = "ForgeSyncApp"
SETTINGS_FILE_NAME = "forgesync_settings.json"
DEFAULT_PROMPT = """You are an expert, automated code merging tool. Your task is to apply a new code snippet to an original code file with extreme precision.

Your rules are strict:
1. You must only apply the changes from the snippet. Do not refactor, improve, or modify any other part of the original file or context files.
2. Your output MUST be the complete, updated content of the *primary target file only*.
3. Do not add any of your own comments, explanations, or markdown formatting (like ```python).
4. Identify and remove any placeholder comments from the final output. This includes comments like `/* ... unchanged ... */`, `<!-- ... meta tags ... -->`, or `# ... rest of the code ...`."""

# =============================================================================
# --- SETTINGS MANAGER ---
# =============================================================================
class SettingsManager:
    """
    Centralized settings and secrets management.
    Handles loading, saving, and accessing application settings and API keys.
    Uses deferred saving to reduce disk I/O.
    """
    
    # Class-level debounce timer tracking
    _save_timer: Optional[Any] = None
    _SAVE_DEBOUNCE_MS: int = 500  # Wait 500ms after last change before saving
    
    def __init__(self) -> None:
        """Initializes the SettingsManager, loading settings from a file."""
        self.settings_path = os.path.join(os.path.expanduser("~"), SETTINGS_FILE_NAME)
        self.settings = self._load_settings()
        self._save_pending = False
    
    def _load_settings(self) -> dict:
        """Loads settings from a JSON file, applying defaults for missing keys."""
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, LookupError):
            loaded_settings = {}
        
        defaults: dict[str, Any] = {
            'theme': 'Dark',
            'custom_prompt': DEFAULT_PROMPT,
            'github_repo_url': '',
            'github_branch': 'main',
            'gemini_model': 'models/gemini-flash-lite-latest',
            'gemini_models_list': ['models/gemini-flash-lite-latest', 'gemini-flash-latest', 'models/gemini-2.5-pro'],
            'saved_sync_projects': [],
            'change_history': [],
            'saved_system_prompts': [],
        }
        
        for key, value in defaults.items():
            loaded_settings.setdefault(key, value)
        
        return loaded_settings
    
    def save_settings(self) -> None:
        """Saves the current settings to the JSON file immediately."""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            self._save_pending = False
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    def _schedule_save(self) -> None:
        """Schedules a deferred save operation with debouncing."""
        import threading
        
        # Cancel any existing scheduled save
        if SettingsManager._save_timer is not None:
            try:
                SettingsManager._save_timer.cancel()
            except Exception:
                pass
        
        # Schedule new save after debounce delay
        self._save_pending = True
        SettingsManager._save_timer = threading.Timer(
            self._SAVE_DEBOUNCE_MS / 1000.0,
            self._execute_deferred_save
        )
        SettingsManager._save_timer.daemon = True
        SettingsManager._save_timer.start()
    
    def _execute_deferred_save(self) -> None:
        """Executes the actual save operation (called by timer)."""
        SettingsManager._save_timer = None
        self.save_settings()
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Retrieves a setting value by key.
        
        Args:
            key: The key of the setting to retrieve.
            default: The default value to return if the key is not found.
            
        Returns:
            The value of the setting.
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any, immediate: bool = False) -> None:
        """
        Sets a setting value. Saves are deferred by default to reduce disk I/O.
        
        Args:
            key: The key of the setting to set.
            value: The new value for the setting.
            immediate: If True, save immediately instead of deferring.
        """
        self.settings[key] = value
        if immediate:
            self.save_settings()
        else:
            self._schedule_save()
    
    def flush(self) -> None:
        """Forces any pending saves to complete immediately."""
        if self._save_pending:
            if SettingsManager._save_timer is not None:
                try:
                    SettingsManager._save_timer.cancel()
                except Exception:
                    pass
                SettingsManager._save_timer = None
            self.save_settings()
    
    def get_api_key(self) -> Optional[str]:
        """Retrieves the Gemini API key from the system's secure keyring."""
        return keyring.get_password(KEYRING_SERVICE_NAME, "gemini_api_key")
    
    def save_api_key(self, api_key: str) -> None:
        """Saves the Gemini API key to the system's secure keyring."""
        keyring.set_password(KEYRING_SERVICE_NAME, "gemini_api_key", api_key)
    
    def get_github_token(self) -> Optional[str]:
        """Retrieves the GitHub token from the system's secure keyring."""
        return keyring.get_password(KEYRING_SERVICE_NAME, "github_api_token")
    
    def save_github_token(self, api_token: str) -> None:
        """Saves the GitHub token to the system's secure keyring."""
        keyring.set_password(KEYRING_SERVICE_NAME, "github_api_token", api_token)

# =============================================================================
# --- SYNTAX HIGHLIGHTER ---
# =============================================================================
class SyntaxHighlighter:
    """
    Enhanced syntax highlighting for a Text widget using Pygments.
    It supports theme changes and debounced highlighting on key release for performance.
    """
    
    def __init__(self, text_widget: Any, ds: DS):
        """
        Initializes the SyntaxHighlighter.

        Args:
            text_widget: The tkinter or customtkinter Text widget to highlight.
            ds: The design system instance for theming.
        """
        self.text = text_widget
        self.ds = ds
        self._highlight_job: Optional[str] = None
        self.style: Optional[Any] = None
        self.set_theme()
        
        if hasattr(text_widget, 'bind'):
            text_widget.bind('<KeyRelease>', self._on_key_release, add=True)
    
    def set_theme(self) -> None:
        """Sets the pygments style based on the current application theme."""
        style_name = 'monokai' if self.ds.theme_mode.lower() == 'dark' else 'default'
        try:
            self.style = get_style_by_name(style_name)
            self._configure_tags()
        except ClassNotFound:
            self.style = get_style_by_name('default')
            self._configure_tags()
    
    def _configure_tags(self) -> None:
        """Configures the Text widget's tags with colors from the pygments style."""
        base_fg = self.ds.colors.text.primary
        self.text.configure(fg=base_fg)
        
        if not self.style: return
        for token, style in self.style:
            tag = str(token)
            fg = style['color']
            if fg:
                self.text.tag_config(tag, foreground=f"#{fg}")
    
    def highlight(self, file_path: Optional[str] = None, code: Optional[str] = None) -> None:
        """
        Performs syntax highlighting on the text widget's content.

        Args:
            file_path: The path to the file, used to guess the lexer.
            code: The code to highlight. If None, uses the widget's content.
        """
        if self.style is None: return

        if code is None:
            code = self.text.get("1.0", "end-1c")
        
        for tag in self.text.tag_names():
            if str(tag).startswith('Token.'):
                self.text.tag_remove(tag, "1.0", "end")
        
        try:
            if file_path:
                extension = os.path.splitext(file_path)[1]
                lexer = get_lexer_by_name(extension.lstrip('.').lower())
            else:
                lexer = guess_lexer(code)
        except (ClassNotFound, TypeError):
            lexer = get_lexer_by_name('text')
        
        import collections
        tags_to_add = collections.defaultdict(list)
        pos = 0

        for token, content in lex(code, lexer):
            length = len(content)
            if length > 0:
                start_index = f"1.0 + {pos}c"
                pos += length
                end_index = f"1.0 + {pos}c"
                tags_to_add[str(token)].extend((start_index, end_index))
                
        for tag, indices in tags_to_add.items():
            if indices:
                # Batch tag_add calls to avoid Tkinter lag. Keep chunks reasonably small.
                chunk_size = 2000
                for i in range(0, len(indices), chunk_size):
                    self.text.tag_add(tag, *indices[i:i+chunk_size])
    
    def _on_key_release(self, event: Optional[Any] = None) -> None:
        """Schedules a debounced re-highlighting of the text."""
        if self._highlight_job:
            self.text.after_cancel(self._highlight_job)
        self._highlight_job = self.text.after(300, self.highlight)

# =============================================================================
# --- LOGGING SETUP ---
# =============================================================================
def setup_logging():
    """Configures global logging to FILE and CONSOLE (CMD)."""
    log_file_path = os.path.join(os.path.expanduser("~"), "forgesync_error.log")
    
    try:
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # 1. File Handler
        file_handler = RotatingFileHandler(log_file_path, maxBytes=1024*1024, backupCount=3, encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        
        # 2. Stream Handler (To CMD)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Logs unhandled exceptions."""
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            logger.critical("Unhandled exception caught:", exc_info=(exc_type, exc_value, exc_traceback))
            
            # Print full stack trace to CMD explicitly
            print("--- CRITICAL ERROR ---", file=sys.stderr)
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            print("----------------------", file=sys.stderr)

        sys.excepthook = handle_exception
        logger.info("ForgeSync Logging configured. Outputting to File and Console.")
    
    except Exception as e:
        print(f"FATAL: Could not configure logging. Error: {e}")