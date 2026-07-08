import customtkinter as ctk
import threading
import sys
import io
from typing import Callable, Optional, Any
from tkinterdnd2 import TkinterDnD, DND_FILES

from utils import SettingsManager, DEFAULT_PROMPT, setup_logging
from design_system import (DS, CardFrame, ButtonWithHover, SecondaryButton, SuccessButton, DangerButton)
from ui_components import ToastNotification, DiffWindow
from gemini_handler import GeminiHandler
from github_handler import GitHubHandler
from app_state import AppState
from file_management import SidebarController
from ai_interactions import AssistantTabController
from git_management import GitTabsController
from tools_management import ToolsController

# FIX: Force UTF-8 encoding for stdio to prevent "unsupported encoding" errors in some envs
if sys.stdout and not sys.stdout.encoding:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='replace')
    except Exception:
        pass

class CodeMergerApp(ctk.CTk, TkinterDnD.DnDWrapper):
    """
    Main application window, acting as a central orchestrator for all controllers and UI components.
    """
    def __init__(self, settings_manager: SettingsManager, app_state: AppState):
        """
        Initializes the main application window.

        Args:
            settings_manager: The application's settings manager instance.
            app_state: The application's shared state instance.
        """
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        
        self.settings_manager = settings_manager
        self.app_state = app_state
        self.ds = DS()
        self.ds.set_theme(self.settings_manager.get('theme'))
        
        self.gemini_handler: Optional[GeminiHandler] = None
        self.github_handler: Optional[GitHubHandler] = None
        self.sidebar_controller: Optional[SidebarController] = None
        self.assistant_controller: Optional[AssistantTabController] = None
        self.git_controller: Optional[GitTabsController] = None
        self.tools_controller: Optional[ToolsController] = None
        
        self.title(f"ForgeSync {self.settings_manager.get('APP_VERSION', '1.0')}")
        self.geometry("1700x950"); self.minsize(1400, 800)
        
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        
        self._create_base_layout()
        
        self.update_idletasks()
        x, y = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2), (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        self.overlay: Optional[ctk.CTkToplevel] = None
        self.busy_counter = 0 # Thread-safe UI lock counter
        self._busy_lock = threading.Lock()

    def set_handlers(self, gemini_handler: GeminiHandler, github_handler: GitHubHandler) -> None:
        """Sets the API handler instances for the application."""
        self.gemini_handler = gemini_handler
        self.github_handler = github_handler

    def initialize_controllers(self) -> None:
        """Initializes all the UI controllers after handlers have been set."""
        if not self.gemini_handler or not self.github_handler:
            raise ValueError("Handlers must be set before initializing controllers.")
        
        # Show loading state explicitly
        self.update_status("Initializing UI components...")
        self.update_idletasks()
        
        # Initialize controllers but defer tab content creation
        self.sidebar_controller = SidebarController(self, self.app_state, self.ds)
        self.assistant_controller = AssistantTabController(self, self.app_state, self.gemini_handler, self.ds)
        self.git_controller = GitTabsController(self, self.app_state, self.gemini_handler, self.github_handler, self.ds)
        self.tools_controller = ToolsController(self, self.app_state, self.gemini_handler, self.github_handler, self.ds) 
        
        # --- Create Sidebar and Tabs fast ---
        self.sidebar_controller.create_sidebar(self.sidebar_frame)

        # Track which tabs have been initialized (lazy loading)
        self._tabs_initialized = {
            "💡ForgeSync": False,
            "🌿GitHub GUI": False,
            "🛠Tools": False,
            "⚙️Settings": False
        }
        
        # Create all tab containers
        self.tab_view.add("💡ForgeSync")
        self.tab_view.add("🌿GitHub GUI")
        self.tab_view.add("🛠Tools")
        self.tab_view.add("⚙️Settings")

        self.tab_view.configure(command=self._on_tab_change)
        
        # Defer the actual heavy loading of the first tab
        self.after(50, self._finish_initialization)
        
    def _finish_initialization(self) -> None:
        """Completes heavy UI initialization after the window appears."""
        # Only initialize the first tab at startup (lazy loading)
        self.assistant_controller.create_tab(self.tab_view.tab("💡ForgeSync"))
        self._tabs_initialized["💡ForgeSync"] = True
        
        self.tab_view.set("💡ForgeSync") 
        self._load_api_key_on_startup()
        
        # Ensure settings tab is initialized before accessing model_menu
        self._ensure_settings_initialized()
        self.model_menu.configure(command=self._on_model_change)
        
        self.update_status("Ready")
        if self.git_controller:
            self.git_controller.fetch_all_repos_background()
    
    def _on_tab_change(self) -> None:
        """Lazily initializes tabs when first accessed for faster startup."""
        current_tab = self.tab_view.get()
        
        if not self._tabs_initialized.get(current_tab, True):
            # Initialize the tab content on first access
            if current_tab == "🌿GitHub GUI":
                self.git_controller.create_source_control_tab(self.tab_view.tab(current_tab))
            elif current_tab == "🛠Tools":
                self.tools_controller.create_tab(self.tab_view.tab(current_tab))
            elif current_tab == "⚙️Settings":
                self._create_settings_tab(self.tab_view.tab(current_tab))
            
            self._tabs_initialized[current_tab] = True
    
    def _ensure_settings_initialized(self) -> None:
        """Ensures the settings tab is initialized (needed for model_menu access)."""
        if not self._tabs_initialized.get("⚙️Settings", True):
            self._create_settings_tab(self.tab_view.tab("⚙️Settings"))
            self._tabs_initialized["⚙️Settings"] = True
    
    def _create_base_layout(self) -> None:
        """Creates the main sidebar, content frame, and status bar."""
        self.sidebar_frame = ctk.CTkFrame(self, width=380, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=1, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        main_frame.grid_rowconfigure(0, weight=1); main_frame.grid_columnconfigure(0, weight=1)
        
        self.tab_view = ctk.CTkTabview(
            main_frame,
            fg_color=self.ds.colors.surface.section,
            segmented_button_fg_color=self.ds.colors.surface.base,
            segmented_button_selected_color=self.ds.colors.primary,
            segmented_button_selected_hover_color=self.ds.colors.primary_hover,
            segmented_button_unselected_color=self.ds.colors.surface.base,
            segmented_button_unselected_hover_color=self.ds.colors.surface.card
        )
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        
        self._create_status_bar()
    
    def _create_settings_tab(self, tab: ctk.CTkFrame) -> None:
        """Creates the content for the 'Settings' tab."""
        tab.grid_columnconfigure(0, weight=1); tab.grid_rowconfigure(0, weight=1)
        
        settings_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        settings_scroll.grid(row=0, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        settings_scroll.grid_columnconfigure(0, weight=1)
        
        self.settings_api_frame = CardFrame(settings_scroll, self.ds)
        self.settings_api_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        self.settings_api_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.settings_api_frame, text="API Configuration", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, self.ds.spacing.s), sticky="w")
        ctk.CTkLabel(self.settings_api_frame, text="Gemini API Key:", font=self.ds.typography.body).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.api_key_entry = ctk.CTkEntry(self.settings_api_frame, show="*"); self.api_key_entry.grid(row=1, column=1, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        if (key := self.settings_manager.get_api_key()): self.api_key_entry.insert(0, key)
        ctk.CTkLabel(self.settings_api_frame, text="GitHub Token:", font=self.ds.typography.body).grid(row=2, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.github_token_entry = ctk.CTkEntry(self.settings_api_frame, show="*", placeholder_text="Personal Access Token"); self.github_token_entry.grid(row=2, column=1, padx=(0, self.ds.spacing.l), pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")
        if (token := self.settings_manager.get_github_token()): self.github_token_entry.insert(0, token)
        
        self.settings_appearance_frame = CardFrame(settings_scroll, self.ds)
        self.settings_appearance_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        self.settings_appearance_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.settings_appearance_frame, text="Appearance & Model", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, self.ds.spacing.s), sticky="w")
        
        ctk.CTkLabel(self.settings_appearance_frame, text="AI Model:", font=self.ds.typography.body).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        
        model_frame = ctk.CTkFrame(self.settings_appearance_frame, fg_color="transparent")
        model_frame.grid(row=1, column=1, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        model_frame.grid_columnconfigure(0, weight=1)
        
        model_list = self.settings_manager.get('gemini_models_list')
        self.model_menu = ctk.CTkComboBox(model_frame, values=model_list)
        self.model_menu.grid(row=0, column=0, sticky="ew")
        self.model_menu.set(self.settings_manager.get('gemini_model'))
        
        # Container for Save and Delete buttons
        model_btn_frame = ctk.CTkFrame(model_frame, fg_color="transparent")
        model_btn_frame.grid(row=0, column=1, padx=(self.ds.spacing.m, 0), sticky="e")

        self.save_model_btn = SecondaryButton(model_btn_frame, self.ds, text="Save", command=self._add_new_gemini_model, width=60)
        self.save_model_btn.pack(side="left")
        
        self.delete_model_btn = DangerButton(model_btn_frame, self.ds, text="X", command=self._delete_current_model, width=30)
        self.delete_model_btn.pack(side="left", padx=(self.ds.spacing.s, 0))

        ctk.CTkLabel(self.settings_appearance_frame, text="Theme:", font=self.ds.typography.body).grid(row=2, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(self.settings_appearance_frame, values=["Light", "Dark", "System"], command=self._on_theme_change); self.theme_menu.grid(row=2, column=1, padx=(0, self.ds.spacing.l), pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")
        self.theme_menu.set(self.settings_manager.get('theme'))
        
        self.settings_prompt_frame = CardFrame(settings_scroll, self.ds)
        self.settings_prompt_frame.grid(row=2, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        self.settings_prompt_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.settings_prompt_frame, text="System Prompt", font=self.ds.typography.h2).grid(row=0, column=0, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, self.ds.spacing.s), sticky="w")
        self.prompt_text = ctk.CTkTextbox(self.settings_prompt_frame, height=150, font=self.ds.typography.code, wrap="word"); self.prompt_text.grid(row=1, column=0, padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m), sticky="ew")
        self.prompt_text.insert("1.0", self.settings_manager.get('custom_prompt'))
        self.settings_restore_btn = SecondaryButton(self.settings_prompt_frame, self.ds, text="Restore Default", command=self._restore_default_prompt)
        self.settings_restore_btn.grid(row=2, column=0, padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m), sticky="w")
        
        self.settings_save_btn = SuccessButton(settings_scroll, self.ds, text="💾 Save Settings", command=self._save_settings, height=45)
        self.settings_save_btn.grid(row=3, column=0, pady=self.ds.spacing.s, sticky="ew")

    def _create_status_bar(self) -> None:
        """Creates the status bar at the bottom of the window."""
        status_frame = ctk.CTkFrame(self, height=35, corner_radius=0)
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_propagate(False)
        self.status_label = ctk.CTkLabel(status_frame, text="Ready", font=("Segoe UI", 11), anchor="w")
        self.status_label.grid(row=0, column=0, padx=15, sticky="w")
        self.progress_bar = ctk.CTkProgressBar(status_frame, width=150, height=8, mode="indeterminate", progress_color=self.ds.colors.primary)

    def _load_api_key_on_startup(self) -> None:
        """Loads and configures the Gemini API key if it's saved in the keyring."""
        if self.gemini_handler and (api_key := self.settings_manager.get_api_key()):
            self.update_status("Found saved Gemini API key, configuring...")
            self.gemini_handler.configure_gemini(api_key, is_startup=True)
            if self.assistant_controller:
                self.assistant_controller.update_contextual_actions()
    
    def _on_model_change(self, new_model: str) -> None:
        """Handles model selection change and shows a confirmation toast."""
        self.show_toast(f"Model selected: {new_model}", "info")

    def _save_settings(self) -> None:
        """Saves all settings from the UI to the settings manager and reconfigures APIs."""
        self.settings_manager.set('theme', self.theme_menu.get())
        self.settings_manager.set('custom_prompt', self.prompt_text.get("1.0", "end-1c"))
        
        # Save the currently selected model
        selected_model = self.model_menu.get()
        self.settings_manager.set('gemini_model', selected_model)
        
        if (token := self.github_token_entry.get()): self.settings_manager.save_github_token(token)
        
        if self.gemini_handler:
            self.gemini_handler.configure_gemini(self.api_key_entry.get())
        if self.assistant_controller:
            self.assistant_controller.update_contextual_actions()
        if self.git_controller:
            self.git_controller.fetch_all_repos_background()
        self.show_toast("Settings Saved!", "success")

    def _add_new_gemini_model(self) -> None:
        """Adds a new model name from the combobox to the settings."""
        new_model = self.model_menu.get().strip()
        if not new_model:
            self.show_toast("Model name cannot be empty.", "warning")
            return

        model_list = self.settings_manager.get('gemini_models_list')
        
        if new_model not in model_list:
            model_list.append(new_model)
            self.settings_manager.set('gemini_models_list', model_list)
            self.model_menu.configure(values=model_list)
            self.model_menu.set(new_model) # Set the new model as active
            self.show_toast(f"Model '{new_model}' saved to list.", "success")
        else:
            self.show_toast(f"Model '{new_model}' already exists in list.", "info")
            
    def _delete_current_model(self) -> None:
        """Deletes the currently selected model from the list."""
        model_to_delete = self.model_menu.get().strip()
        model_list = self.settings_manager.get('gemini_models_list')
        
        default_models = ['gemini-flash-lite-latest', 'gemini-flash-latest', 'gemini-2.5-pro']
        if model_to_delete in default_models:
            self.show_toast("Cannot delete default models.", "error")
            return
            
        if model_to_delete in model_list:
            model_list.remove(model_to_delete)
            self.settings_manager.set('gemini_models_list', model_list)
            
            # Update the combobox values and set a new default
            new_selection = model_list[0] if model_list else 'gemini-flash-lite-latest'
            self.model_menu.configure(values=model_list)
            self.model_menu.set(new_selection)
            self.settings_manager.set('gemini_model', new_selection)

            self.show_toast(f"Model '{model_to_delete}' deleted.", "info")
        else:
            self.show_toast(f"Model '{model_to_delete}' not found in list.", "warning")

    def _on_theme_change(self, new_theme: str) -> None:
        """Handles theme changes and triggers updates across all UI components."""
        self.ds.set_theme(new_theme)
        
        # --- Update all major application components ---
        self._update_app_theme()
        self._update_settings_tab_theme()
        
        if self.sidebar_controller: self.sidebar_controller.update_theme()
        if self.assistant_controller: self.assistant_controller.update_theme()
        if self.git_controller: self.git_controller.update_theme()
        if self.tools_controller: self.tools_controller.update_theme()
        
    def _update_app_theme(self) -> None:
        """Updates the theme of core application elements like the tab view."""
        self.tab_view.configure(
            fg_color=self.ds.colors.surface.section,
            segmented_button_fg_color=self.ds.colors.surface.base,
            segmented_button_selected_color=self.ds.colors.primary,
            segmented_button_selected_hover_color=self.ds.colors.primary_hover,
            segmented_button_unselected_color=self.ds.colors.surface.base,
            segmented_button_unselected_hover_color=self.ds.colors.surface.card
        )
        self.progress_bar.configure(progress_color=self.ds.colors.primary)
    
    def _update_settings_tab_theme(self) -> None:
        """Meticulously re-styles all components in the settings tab for the new theme."""
        # Re-configure card backgrounds and borders
        if hasattr(self, 'settings_api_frame'):
            self.settings_api_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.settings_appearance_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.settings_prompt_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
    
            # Re-configure button colors
            self.settings_restore_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.settings_save_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
            self.save_model_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.delete_model_btn.configure(fg_color=self.ds.colors.danger, hover_color=self.ds.colors.danger_hover)


    def _restore_default_prompt(self) -> None:
        """Restores the system prompt text to its default value."""
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", DEFAULT_PROMPT)

    def update_system_prompt_text(self, new_prompt: str) -> None:
        """Public method to update the system prompt textbox from another controller."""
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", new_prompt)

    def show_diff_viewer(self, original: str, updated: str, file_path: str, is_readonly: bool = False, on_accept_callback: Optional[Callable] = None) -> None:
        """
        Displays the modal diff viewer window.

        Args:
            original: The original code content.
            updated: The new, modified code content.
            file_path: The path of the file being changed.
            is_readonly: If True, the 'Accept' button is disabled.
            on_accept_callback: An optional function to call after the file is saved.
        """
        save_cb = None
        if not is_readonly and self.assistant_controller:
            # Create a default save callback
            default_save = lambda new_content: self.assistant_controller.save_file(new_content, original, file_path)
            
            # Chain the on_accept_callback if it exists
            if on_accept_callback:
                save_cb = lambda new_content: (default_save(new_content), on_accept_callback())
            else:
                save_cb = default_save

        DiffWindow(self, self.ds, original, updated, file_path, save_cb, self.gemini_handler, self.show_toast)

    def update_staged_files_display(self) -> None:
        """Refreshes the staged files list in the GitHub Push tab."""
        if self.git_controller:
            self.git_controller.update_staged_files_ui()
            
    def update_status(self, message: str) -> None: 
        """Updates the text in the status bar."""
        self.after(0, lambda: self.status_label.configure(text=message))
        
    def show_toast(self, message: str, msg_type: str = 'info') -> None: 
        """Displays a toast notification."""
        self.after(0, lambda: ToastNotification(self, self.ds, message, msg_type))

    def _update_overlay_geometry(self, event: Optional[Any] = None) -> None:
        """Callback to update the overlay's geometry to match the main window."""
        if self.overlay:
            self.overlay.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{self.winfo_x()}+{self.winfo_y()}")

    def show_progress_overlay(self) -> None:
        """Displays a semi-transparent overlay with a progress bar for long operations."""
        with self._busy_lock:
            self.busy_counter += 1
            if self.busy_counter == 1: # Only create and show on the first call
                if self.overlay: return
                self.overlay = ctk.CTkToplevel(self)
                self.overlay.overrideredirect(True)
                self.overlay.attributes('-alpha', 0.0)
                self.overlay.configure(fg_color=self.ds.colors.surface.base)
    
                self._update_overlay_geometry()
                self.bind("<Configure>", self._update_overlay_geometry)
    
                def fade_in() -> None:
                    if not self.overlay: return
                    alpha = self.overlay.attributes('-alpha')
                    if alpha < 0.7:
                        # Faster animation: larger alpha increment, slightly longer interval
                        self.overlay.attributes('-alpha', min(0.7, alpha + 0.25))
                        self.overlay.after(30, fade_in)
                fade_in()
                
                self.update_status("Processing...")
                self.progress_bar.place(relx=0.5, rely=0.5, anchor="center")
                self.progress_bar.start()

    def hide_progress_overlay(self) -> None:
        """Hides the progress overlay."""
        with self._busy_lock:
            self.busy_counter = max(0, self.busy_counter - 1)
            if self.busy_counter == 0: # Only hide when all tasks are done
                if not self.overlay: return
                
                self.unbind("<Configure>")
    
                def fade_out() -> None:
                    if not self.overlay: return
                    alpha = self.overlay.attributes('-alpha')
                    if alpha > 0.0:
                        # Faster animation: larger alpha decrement
                        self.overlay.attributes('-alpha', max(0.0, alpha - 0.25))
                        self.overlay.after(30, fade_out)
                    else:
                        if self.overlay:
                            self.overlay.destroy()
                            self.overlay = None
                fade_out()
    
                self.update_status("Ready")
                self.progress_bar.stop()
                self.progress_bar.place_forget()

if __name__ == "__main__":
    setup_logging()
    settings = SettingsManager()
    app_state = AppState(settings)
    
    app = CodeMergerApp(settings, app_state)
    
    gemini_handler = GeminiHandler(settings, app.update_status, app.show_toast)
    github_handler = GitHubHandler(app.update_status, app.show_toast)
    
    app.set_handlers(gemini_handler, github_handler)
    
    # We call initialize_controllers right away, but the heavy lifting inside it is deferred
    app.initialize_controllers()
    
    app.mainloop()