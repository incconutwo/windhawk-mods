import customtkinter as ctk
from tkinter import filedialog
import os
import threading
from datetime import datetime
from typing import Optional, Any, Dict, List, Callable
from design_system import DS, CardFrame, ButtonWithHover, PillButton, DangerButton, SuccessButton, GhostButton
from base_controller import BaseController

class AssistantTabController(BaseController):
    """Manages the UI and logic for the Code Assistant tab."""
    def __init__(self, app: 'CodeMergerApp', app_state: 'AppState', gemini_handler: 'GeminiHandler', ds: DS):
        super().__init__(app)
        self.app_state = app_state
        self.gemini_handler = gemini_handler
        self.ds = ds
        self.is_history_visible = False

    def create_tab(self, tab_frame: ctk.CTkFrame) -> None:
        """Creates the 'Code Assistant' tab content within the provided frame."""
        self._setup_ui(tab_frame)
        self._bind_events()
        # Do not populate history sidebar on startup, do it lazily when opened

    def _setup_ui(self, tab: ctk.CTkFrame) -> None:
        """Defines and lays out all widgets in the assistant tab with a minimalist design."""
        tab.grid_columnconfigure(0, weight=1) # Main content
        tab.grid_columnconfigure(1, weight=0) # History sidebar (starts hidden)
        tab.grid_rowconfigure(0, weight=1)
        
        # --- Main Content Area ---
        self.main_content = ctk.CTkFrame(tab, fg_color="transparent")
        self.main_content.grid(row=0, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(5, weight=1) 
        
        # 1. Header & Actions
        header_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        header_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(header_frame, text="ForgeSync", font=self.ds.typography.h1).grid(row=0, column=0, sticky="w")
        self.toggle_history_btn = GhostButton(header_frame, self.ds, text="🕒 History", width=80, command=self._toggle_history)
        self.toggle_history_btn.grid(row=0, column=1, sticky="e")

        # 2. Target File (Minimal Row)
        target_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        target_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        target_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(target_frame, text="Target File", font=self.ds.typography.h2, text_color=self.ds.colors.text.secondary).grid(row=0, column=0, sticky="w", padx=(0, self.ds.spacing.m))
        
        self.target_file_display = ctk.CTkEntry(target_frame, state="readonly", fg_color=self.ds.colors.surface.section, border_width=0, height=32)
        self.target_file_display.grid(row=0, column=1, sticky="ew")
        self.target_file_label = ctk.CTkLabel(target_frame, text="", font=self.ds.typography.body_small) # Hidden ref for internal logic state if needed
        self.set_target_file(None) # Initialize text

        # 3. Context (Minimal Row)
        context_header = ctk.CTkFrame(self.main_content, fg_color="transparent")
        context_header.grid(row=2, column=0, sticky="ew", pady=(0, self.ds.spacing.s))
        ctk.CTkLabel(context_header, text="Context Files", font=self.ds.typography.h2, text_color=self.ds.colors.text.secondary).pack(side="left", padx=(0, self.ds.spacing.m))
        self.add_context_btn = GhostButton(context_header, self.ds, text="+ Add Context", width=100, height=24)
        self.add_context_btn.pack(side="left")
        
        self.context_pills_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.context_pills_frame.grid(row=3, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self._update_context_pills()

        # 4. Instructions (Expanded Area)
        ctk.CTkLabel(self.main_content, text="Instructions", font=self.ds.typography.h2, text_color=self.ds.colors.text.secondary).grid(row=4, column=0, sticky="nw", pady=(0, self.ds.spacing.s))
        
        self.instructions_text = ctk.CTkTextbox(self.main_content, font=self.ds.typography.code, wrap="word", 
                                                fg_color=self.ds.colors.surface.card, border_width=0, corner_radius=8)
        self.instructions_text.grid(row=5, column=0, sticky="nsew", pady=(0, self.ds.spacing.l))
        self.instructions_text.insert("1.0", "Enter your code changes or instructions here...")

        # 5. Action Footer
        action_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        action_frame.grid(row=6, column=0, sticky="ew")
        action_frame.grid_columnconfigure(1, weight=1) # Spacer
        
        self.undo_btn = DangerButton(action_frame, self.ds, text="Undo Last Save", width=120, state="disabled")
        self.undo_btn.grid(row=0, column=0, sticky="w")
        
        self.preview_btn = ButtonWithHover(action_frame, self.ds, text="✨ Preview Changes", height=40, width=160, state="disabled")
        self.preview_btn.grid(row=0, column=2, sticky="e")

        # --- History Sidebar (Drawer) ---
        self.history_sidebar = ctk.CTkFrame(tab, fg_color=self.ds.colors.surface.section, corner_radius=0, width=300)
        # Not gridded initially
        self.history_sidebar.grid_rowconfigure(1, weight=1)
        self.history_sidebar.grid_columnconfigure(0, weight=1)
        
        hist_header = ctk.CTkFrame(self.history_sidebar, fg_color="transparent")
        hist_header.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        ctk.CTkLabel(hist_header, text="Change History", font=self.ds.typography.h2).pack(side="left")
        GhostButton(hist_header, self.ds, text="✕", width=30, command=self._toggle_history).pack(side="right")
        
        self.history_frame = ctk.CTkScrollableFrame(self.history_sidebar, fg_color="transparent")
        self.history_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.s, pady=self.ds.spacing.s)

    def _toggle_history(self) -> None:
        """Toggles the visibility of the history sidebar."""
        if self.is_history_visible:
            self.history_sidebar.grid_forget()
            self.toggle_history_btn.configure(fg_color="transparent")
        else:
            self.history_sidebar.grid(row=0, column=1, sticky="nsew")
            self.toggle_history_btn.configure(fg_color=self.ds.colors.surface.section)
            # Lazily populate history when first opened or if there's been an update
            if not self.history_frame.winfo_children():
                self._populate_history_sidebar()
                
        self.is_history_visible = not self.is_history_visible

    def _bind_events(self) -> None:
        """Binds commands to the UI widgets."""
        self.add_context_btn.configure(command=self.add_context_files)
        self.preview_btn.configure(command=self.start_merge_thread)
        self.undo_btn.configure(command=self.undo_last_change)

    def set_target_file(self, filename: Optional[str], is_dir: bool = False) -> None:
        """
        Updates the target file label based on the user's selection.

        Args:
            filename: The name of the selected file.
            is_dir: True if the selected item is a directory.
        """
        self.target_file_display.configure(state="normal")
        self.target_file_display.delete(0, "end")
        
        if is_dir:
            self.target_file_display.insert(0, "Selected item is a directory")
            self.target_file_label.configure(text="dir") # Internal state reference
        elif filename:
            self.target_file_display.insert(0, filename)
            self.target_file_label.configure(text=filename)
        else:
            self.target_file_display.insert(0, "Select a file from the explorer...")
            self.target_file_label.configure(text="")
            
        self.target_file_display.configure(state="readonly")

    def add_context_files(self, files: Optional[List[str]] = None) -> None:
        """
        Adds files to the context. If no files are provided, opens a file dialog.
        
        Args:
            files: An optional list of absolute file paths to add.
        """
        if not files:
            files = filedialog.askopenfilenames(title="Select context files")
        
        if files:
            # Use a set to prevent duplicates, then convert back to a list
            updated_paths = set(self.app_state.context_file_paths)
            updated_paths.update(files)
            self.app_state.context_file_paths = sorted(list(updated_paths))
            
            self._update_context_pills()
            self.app.update_status(f"Added {len(files)} context file(s).")

    def _update_context_pills(self) -> None:
        """Renders the context files as dismissible pill buttons with widget reuse."""
        children = self.context_pills_frame.winfo_children()
        paths = self.app_state.context_file_paths
        
        # Handle empty state
        if not paths:
            # Hide all existing pills
            for widget in children:
                widget.pack_forget()
            # Show or create the "no files" label
            if not children or not isinstance(children[0], ctk.CTkLabel):
                # Clear any existing pills and create the label
                for widget in children:
                    widget.destroy()
                ctk.CTkLabel(self.context_pills_frame, text="No context files added", 
                            font=self.ds.typography.body_small, 
                            text_color=self.ds.colors.text.secondary).pack(side="left")
            else:
                children[0].pack(side="left")
            return
        
        # Clear the "no files" label if it exists
        if children and isinstance(children[0], ctk.CTkLabel) and "No context" in str(children[0].cget("text")):
            children[0].destroy()
            children = []
        
        # Reuse existing pill widgets
        for i, file_path in enumerate(paths):
            if i < len(children):
                # Reuse existing pill - update text and command
                pill = children[i]
                new_text = f"{os.path.basename(file_path)}  ✕"
                pill.configure(text=new_text, command=lambda fp=file_path: self._remove_context_file(fp))
                pill.pack(side="left", anchor="nw", padx=(0, self.ds.spacing.s), pady=self.ds.spacing.s)
            else:
                # Create new pill
                pill = PillButton(self.context_pills_frame, self.ds, text=os.path.basename(file_path),
                                  command=lambda fp=file_path: self._remove_context_file(fp))
                pill.pack(side="left", anchor="nw", padx=(0, self.ds.spacing.s), pady=self.ds.spacing.s)
        
        # Hide extra pills that are no longer needed
        for i in range(len(paths), len(children)):
            children[i].pack_forget()
    
    def _remove_context_file(self, file_path_to_remove: str) -> None:
        """Removes a context file from the app state and updates the UI."""
        if file_path_to_remove in self.app_state.context_file_paths:
            self.app_state.context_file_paths.remove(file_path_to_remove)
            self._update_context_pills()
    
    def update_contextual_actions(self) -> None:
        """Enables or disables buttons based on the current application state."""
        # Preview button logic
        can_preview = self.app_state.original_file_path and self.gemini_handler.is_configured()
        self.preview_btn.configure(state="normal" if can_preview else "disabled")
        
        # Undo button logic
        can_undo = self.app_state.original_code_backup and self.app_state.original_file_path_for_undo == self.app_state.original_file_path
        self.undo_btn.configure(state="normal" if can_undo else "disabled")

    def undo_last_change(self) -> None:
        """Restores the last saved file from its backup."""
        if self.app_state.original_code_backup and self.app_state.original_file_path_for_undo:
            try:
                with open(self.app_state.original_file_path_for_undo, 'w', encoding='utf-8') as f:
                    f.write(self.app_state.original_code_backup)
                self.app.show_toast("Last save undone.", "success")
                self.app_state.original_code_backup = None
                self.app_state.original_file_path_for_undo = None
                self.update_contextual_actions()
            except Exception as e:
                self.app.show_toast(f"Undo Failed: {e}", "error")
        else:
            self.app.show_toast("No change to undo.", "info")

    def start_merge_thread(self) -> None:
        """Starts the AI merge process in a separate thread."""
        snippet = self.instructions_text.get("1.0", "end-1c").strip()
        
        # Check for exact match with the placeholder text.
        # Previous logic ('in snippet') failed if the code being processed actually contained this phrase.
        default_placeholder = "Enter your code changes or instructions here..."
        
        if not snippet or snippet == default_placeholder:
            self.app.show_toast("Enter instructions or a code snippet.", "warning"); return
        
        self.preview_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_merge_process_threaded, args=(snippet,), daemon=True).start()

    def _run_merge_process_threaded(self, snippet: str) -> None:
        """Worker thread that reads files and calls the Gemini API."""
        try:
            if not self.app_state.original_file_path:
                raise ValueError("No target file selected.")

            with open(self.app_state.original_file_path, 'r', encoding='utf-8') as f: original_code = f.read()
            self.app_state.original_code_backup = original_code
            self.app_state.original_file_path_for_undo = self.app_state.original_file_path
            
            diff_window = None
            def on_diff_window_created(w):
                nonlocal diff_window
                diff_window = w

            # Open DiffWindow immediately with empty updated code
            self.app.after(0, lambda: self._show_diff_viewer_for_stream(original_code, self.app_state.original_file_path, on_diff_window_created))

            def stream_callback(chunk: str):
                if diff_window and diff_window.winfo_exists():
                    self.app.after(0, lambda: diff_window.append_stream_chunk(chunk))

            full_updated_code = self.gemini_handler.run_merge_process(
                self.app_state.original_file_path, original_code, self.app_state.context_file_paths, snippet, stream_callback=stream_callback
            )
            
            if diff_window and diff_window.winfo_exists():
                self.app.after(0, lambda: diff_window.finish_stream())
                
        except (ValueError, ConnectionError, FileNotFoundError) as e:
            self.app.after(0, self.app.show_toast, f"Error: {e}", "error")
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An unexpected error occurred: {e}", "error")
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.preview_btn.configure(state="normal" if self.app_state.original_file_path and self.gemini_handler.is_configured() else "disabled"))

    def _show_diff_viewer_for_stream(self, original_code: str, file_path: str, created_cb: Callable) -> None:
        """Helper to show DiffWindow for streaming and return its instance."""
        from ui_components import DiffWindow
        # Create default save callback
        default_save = lambda new_content: self.save_file(new_content, original_code, file_path)
        dw = DiffWindow(self.app, self.ds, original_code, "", file_path, default_save, self.gemini_handler, self.app.show_toast)
        # Disable accept button initially until stream finishes
        dw.accept_btn.configure(state="disabled")
        created_cb(dw)

    def save_file(self, new_content: str, original_content: str, file_path: str) -> None:
        """
        Saves the new content to a file and records the change in history.

        Args:
            new_content: The new code to write to the file.
            original_content: The original code, for history/undo purposes.
            file_path: The absolute path of the file to save.
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f: f.write(new_content)
            
            history_entry = {
                'file_path': file_path, 'original_code': original_content,
                'updated_code': new_content, 'timestamp': datetime.now().isoformat()
            }
            self.app_state.change_history.insert(0, history_entry)
            self.app_state.change_history = self.app_state.change_history[:10] # Limit history size
            self.app_state.settings_manager.set('change_history', self.app_state.change_history)
            
            # Only update UI if it's visible to save performance
            if self.is_history_visible:
                self._populate_history_sidebar()
            else:
                # Clear it so it rebuilds next time it's opened
                for widget in self.history_frame.winfo_children(): widget.destroy()

            self.app.show_toast(f"File saved!", "success")
            self.update_contextual_actions()
        except Exception as e:
            self.app.show_toast(f"Error saving: {e}", "error")

    def _revert_change(self, history_item: Dict[str, Any]) -> None:
        """
        Reverts a file to its state before a specific historical change.

        Args:
            history_item: The history dictionary object to revert.
        """
        file_path = history_item['file_path']
        original_code = history_item['original_code']
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(original_code)
            
            if self.is_history_visible:
                self._populate_history_sidebar()

            self.app.show_toast(f"Reverted {os.path.basename(file_path)}", "success")
        except Exception as e:
            self.app.show_toast(f"Revert failed: {e}", "error")

    def _reapply_change(self, history_item: Dict[str, Any]) -> None:
        """
        Re-applies a historical change that was previously reverted.

        Args:
            history_item: The history dictionary object to re-apply.
        """
        file_path = history_item['file_path']
        updated_code = history_item['updated_code']
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_code)
            
            if self.is_history_visible:
                self._populate_history_sidebar()

            self.app.show_toast(f"Re-applied changes to {os.path.basename(file_path)}", "success")
        except Exception as e:
            self.app.show_toast(f"Re-apply failed: {e}", "error")

    def _populate_history_sidebar(self) -> None:
        """Renders the list of recent changes in the history sidebar."""
        for widget in self.history_frame.winfo_children(): widget.destroy()

        if not self.app_state.change_history:
            msg = ctk.CTkLabel(self.history_frame, 
                               text="No changes recorded yet.\n\nUse 'Preview Changes' to make and save a modification.",
                               font=self.ds.typography.body, 
                               text_color=self.ds.colors.text.secondary,
                               wraplength=250)
            msg.pack(pady=20, padx=10)
            return

        for item in self.app_state.change_history:
            entry_card = CardFrame(self.history_frame, self.ds)
            entry_card.pack(fill="x", pady=(0, self.ds.spacing.m))
            entry_card.grid_columnconfigure(0, weight=1)

            filename = os.path.basename(item['file_path'])
            ctk.CTkLabel(entry_card, text=filename, font=self.ds.typography.body_bold, anchor="w").grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(self.ds.spacing.m, 0))

            ts = datetime.fromisoformat(item['timestamp'])
            timestamp_str = ts.strftime("%b %d, %H:%M")
            ctk.CTkLabel(entry_card, text=timestamp_str, font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary, anchor="w").grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))

            btn_frame = ctk.CTkFrame(entry_card, fg_color="transparent")
            btn_frame.grid(row=2, column=0, padx=self.ds.spacing.m, pady=self.ds.spacing.s, sticky="ew")
            
            # View button using Ghost style for cleanliness
            view_btn = GhostButton(btn_frame, self.ds, text="View", height=24, width=50,
                                     command=lambda i=item: self.app.show_diff_viewer(i['original_code'], i['updated_code'], i['file_path'], is_readonly=True))
            view_btn.pack(side="left")

            # --- REVERT/RE-APPLY LOGIC ---
            try:
                with open(item['file_path'], 'r', encoding='utf-8') as f:
                    current_content = f.read()
            except (FileNotFoundError, IOError):
                current_content = None

            if current_content is not None:
                if current_content == item['updated_code']:
                    # The change is currently applied, so show a "Revert" button
                    revert_btn = DangerButton(btn_frame, self.ds, text="Revert", height=24, width=50, font=self.ds.typography.body_small,
                                               command=lambda i=item: self._revert_change(i))
                    revert_btn.pack(side="right")
                elif current_content == item['original_code']:
                    # The change is reverted, so show a "Re-apply" button
                    reapply_btn = SuccessButton(btn_frame, self.ds, text="Re-apply", height=24, width=60, font=self.ds.typography.body_small,
                                                command=lambda i=item: self._reapply_change(i))
                    reapply_btn.pack(side="right")
                else:
                    # File has been modified further.
                    info_label = ctk.CTkLabel(btn_frame, text="Modified", font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary)
                    info_label.pack(side="right")
            else:
                # File not found
                info_label = ctk.CTkLabel(btn_frame, text="File Missing", font=self.ds.typography.body_small, text_color=self.ds.colors.warning)
                info_label.pack(side="right")

    def update_theme(self) -> None:
        """Updates the theme for all components in the Assistant tab."""
        # Re-configure main areas
        self.main_content.configure(fg_color="transparent")
        
        # Inputs
        self.target_file_display.configure(fg_color=self.ds.colors.surface.section, text_color=self.ds.colors.text.primary)
        self.instructions_text.configure(fg_color=self.ds.colors.surface.card, text_color=self.ds.colors.text.primary)
        
        # Buttons
        self.toggle_history_btn.configure(hover_color=self.ds.colors.surface.section, text_color=self.ds.colors.text.primary)
        if self.is_history_visible:
             self.toggle_history_btn.configure(fg_color=self.ds.colors.surface.section)
        
        self.add_context_btn.configure(hover_color=self.ds.colors.surface.section, text_color=self.ds.colors.text.primary)
        self.preview_btn.configure(fg_color=self.ds.colors.primary, hover_color=self.ds.colors.primary_hover)
        self.undo_btn.configure(fg_color=self.ds.colors.danger, hover_color=self.ds.colors.danger_hover)
        
        # Sidebar
        self.history_sidebar.configure(fg_color=self.ds.colors.surface.section)
        
        # Text colors
        for widget in self.main_content.winfo_children():
             if isinstance(widget, ctk.CTkLabel) and widget.cget("text") in ["Target File", "Context Files", "Instructions"]:
                  widget.configure(text_color=self.ds.colors.text.secondary)

        # Re-render dynamic lists
        self._update_context_pills()
        self._populate_history_sidebar()