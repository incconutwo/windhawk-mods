import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
from typing import Optional, Any
from design_system import DS, ButtonWithHover, SuccessButton, SecondaryButton
from ui_components import FileTreeView
from utils import debounce

MAX_FILE_SIZE_MB = 50 # Increased to support short videos and images

class SidebarController:
    """Manages the UI and logic for the file explorer sidebar."""
    def __init__(self, app: 'CodeMergerApp', app_state: 'AppState', ds: DS):
        """
        Initializes the SidebarController.

        Args:
            app: The main application instance.
            app_state: The shared application state.
            ds: The design system instance.
        """
        self.app = app
        self.app_state = app_state
        self.ds = ds
        self.file_tree: Optional[FileTreeView] = None
        self.context_menu = tk.Menu(self.app, tearoff=0)

    def create_sidebar(self, sidebar_frame: ctk.CTkFrame) -> None:
        """Creates and configures all widgets within the sidebar frame."""
        self._setup_ui(sidebar_frame)
        self._bind_events()
        self.update_view()

    def _setup_ui(self, parent_frame: ctk.CTkFrame) -> None:
        """Defines and lays out the UI elements of the sidebar."""
        parent_frame.grid_rowconfigure(3, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_propagate(False)
        
        ctk.CTkLabel(parent_frame, text="📁 File Explorer", font=self.ds.typography.h1).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        
        controls_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        controls_frame.grid_columnconfigure(0, weight=1)
        self.open_folder_btn = ButtonWithHover(controls_frame, self.ds, text="Open Folder", height=35)
        self.open_folder_btn.grid(row=0, column=0, sticky="ew")
        self.current_folder_label = ctk.CTkLabel(controls_frame, text="No folder opened", font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary)
        self.current_folder_label.grid(row=1, column=0, sticky="w", pady=(self.ds.spacing.s, 0))
        
        self.search_entry = ctk.CTkEntry(parent_frame, placeholder_text="Search files...", height=35)
        self.search_entry.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))

        self.tree_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        self.tree_container.grid(row=3, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        self.tree_container.grid_rowconfigure(0, weight=1); self.tree_container.grid_columnconfigure(0, weight=1)
        
        self.empty_state_frame = ctk.CTkFrame(self.tree_container, fg_color="transparent")
        self.empty_state_frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(self.empty_state_frame, text="📂", font=("Segoe UI", 50)).pack(pady=(80, 10))
        ctk.CTkLabel(self.empty_state_frame, text="No Folder Open", font=self.ds.typography.h2).pack()
        ctk.CTkLabel(self.empty_state_frame, text="Click 'Open Folder' to start.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary).pack()

        self.file_tree = FileTreeView(self.tree_container, self.ds, selectmode="extended", show="tree")
        
        staging_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        staging_frame.grid(row=4, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        staging_frame.grid_columnconfigure((0, 1), weight=1)
        self.stage_btn = SuccessButton(staging_frame, self.ds, text="➕ Stage", height=35, state="disabled")
        self.stage_btn.grid(row=0, column=0, padx=(0, self.ds.spacing.s), sticky="ew")
        self.clear_stage_btn = SecondaryButton(staging_frame, self.ds, text="🗑️ Clear", height=35)
        self.clear_stage_btn.grid(row=0, column=1, padx=(self.ds.spacing.s, 0), sticky="ew")

    def _bind_events(self) -> None:
        """Binds commands and events to the UI widgets."""
        self.open_folder_btn.configure(command=self.open_folder)
        self.search_entry.bind("<KeyRelease>", self._filter_tree)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)
        self.file_tree.bind("<Button-3>", self._show_context_menu) # Right-click event
        self.stage_btn.configure(command=self.stage_selected_files)
        self.clear_stage_btn.configure(command=self.clear_staged_files)

    def _show_context_menu(self, event: Any) -> None:
        """Creates and displays a context menu on right-click."""
        if not self.file_tree: return
        
        item_id = self.file_tree.identify_row(event.y)
        if not item_id: return

        # Programmatically select the item under the cursor
        self.file_tree.selection_set(item_id)
        
        values = self.file_tree.item(item_id, "values")
        if not values or not os.path.isfile(values[0]):
            return # Only show menu for files, not directories

        file_path = values[0]
        filename = os.path.basename(file_path)

        # Clear previous menu items
        self.context_menu.delete(0, "end")

        self.context_menu.add_command(label=f"Set '{filename}' as Target", command=lambda: self.app.assistant_controller.set_target_file(filename) if self.app.assistant_controller else None)
        self.context_menu.add_command(label=f"Add '{filename}' to Context", command=lambda: self.app.assistant_controller.add_context_files([file_path]) if self.app.assistant_controller else None)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Stage for Commit", command=self.stage_selected_files)
        
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def open_folder(self) -> None:
        """Opens a directory dialog and populates the file tree with its contents."""
        folder_path = filedialog.askdirectory()
        if not folder_path or not self.file_tree: return
        self.app_state.opened_folder_path = folder_path
        self.current_folder_label.configure(text=os.path.basename(folder_path))
        for i in self.file_tree.get_children(): self.file_tree.delete(i)
        self.populate_tree(folder_path, "")
        self.app.update_status(f"Opened: {os.path.basename(folder_path)}")
        self.clear_staged_files()
        self.update_view()

    def update_view(self) -> None:
        """Shows either the file tree or the empty state message."""
        if self.app_state.opened_folder_path:
            self.empty_state_frame.grid_forget()
            if self.file_tree: self.file_tree.grid(row=0, column=0, sticky="nsew")
        else:
            if self.file_tree: self.file_tree.grid_forget()
            self.empty_state_frame.grid(row=0, column=0, sticky="nsew")

    def populate_tree(self, path: str, parent: str, filter_term: str = "") -> None:
        """
        Recursively populates the file tree view from a given path.

        Args:
            path: The current directory path to scan.
            parent: The parent item's ID in the treeview.
            filter_term: A search string to filter file names.
        """
        if not self.file_tree: return
        ignored_dirs = {".git", "__pycache__", ".vscode", "node_modules", "venv", ".env"}
        try:
            items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
            for item in items:
                if item.startswith('.') or item in ignored_dirs: continue
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    node = self.file_tree.insert(parent, "end", text=f"📁 {item}", open=False)
                    self.populate_tree(item_path, node, filter_term)
                elif not filter_term or filter_term in item.lower():
                    self.file_tree.insert(parent, "end", text=f"📄 {item}", values=[item_path])
        except PermissionError: pass

    def _filter_tree(self, event: Optional[Any] = None) -> None:
        """Filters the tree view based on the content of the search entry (debounced)."""
        # Cancel any pending filter operation
        if hasattr(self, '_filter_job') and self._filter_job is not None:
            try:
                self.app.after_cancel(self._filter_job)
            except Exception:
                pass
        
        # Schedule the actual filter operation after a delay
        self._filter_job = self.app.after(150, self._execute_filter)
    
    def _execute_filter(self) -> None:
        """Actually performs the tree filtering operation."""
        if not self.file_tree: return
        search_term = self.search_entry.get().lower()
        for i in self.file_tree.get_children(): self.file_tree.delete(i)
        if self.app_state.opened_folder_path:
            self.populate_tree(self.app_state.opened_folder_path, "", filter_term=search_term)

    def _on_file_select(self, event: Optional[Any] = None) -> None:
        """Handles file selection in the tree, updating the app state."""
        if not self.file_tree: return
        selected_items = self.file_tree.selection()
        
        self.stage_btn.configure(state="normal" if selected_items else "disabled")
        if not selected_items: return
        
        item = selected_items[0]
        values = self.file_tree.item(item, "values")
        
        if values and os.path.isfile(values[0]):
            self.app_state.original_file_path = values[0]
            filename = os.path.basename(self.app_state.original_file_path)
            if self.app.assistant_controller:
                self.app.assistant_controller.set_target_file(filename)
            self.app.update_status(f"Selected: {filename}")
        else:
            self.app_state.original_file_path = None
            if self.app.assistant_controller:
                self.app.assistant_controller.set_target_file(None, is_dir=True)
        
        if self.app.assistant_controller:
            self.app.assistant_controller.update_contextual_actions()

    def stage_selected_files(self) -> None:
        """Adds the selected files from the tree to the set of staged files, with size checks.
        If a folder is selected, recursively stages all files within it and subfolders."""
        if not self.file_tree: return
        count = 0
        skipped = 0
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        
        def stage_file(fp: str) -> tuple[int, int]:
            """Stages a single file if valid. Returns (staged_count, skipped_count)."""
            nonlocal count, skipped
            if fp in self.app_state.staged_github_files:
                return (0, 0)
            try:
                if os.path.getsize(fp) > max_bytes:
                    filename = os.path.basename(fp)
                    self.app.show_toast(f"Skipped: {filename} > {MAX_FILE_SIZE_MB}MB", "warning")
                    return (0, 1)
            except OSError:
                return (0, 1)  # Skip files we can't get the size of
            
            self.app_state.staged_github_files.add(fp)
            return (1, 0)
        
        def stage_directory(dir_path: str) -> None:
            """Recursively stages all files in a directory and its subdirectories."""
            nonlocal count, skipped
            ignored_dirs = {".git", "__pycache__", ".vscode", "node_modules", "venv", ".env"}
            try:
                for root, dirs, files in os.walk(dir_path):
                    # Filter out ignored directories
                    dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
                    for filename in files:
                        if filename.startswith('.'):
                            continue
                        fp = os.path.join(root, filename)
                        staged, skip = stage_file(fp)
                        count += staged
                        skipped += skip
            except PermissionError:
                pass
        
        for item in self.file_tree.selection():
            values = self.file_tree.item(item, "values")
            item_text = self.file_tree.item(item, "text")
            
            if values and values[0]:
                # This is a file (has a path in values)
                fp = values[0]
                if os.path.isfile(fp):
                    staged, skip = stage_file(fp)
                    count += staged
                    skipped += skip
            elif item_text.startswith("📁"):
                # This is a folder - need to reconstruct its path
                # Walk up the tree to get the full path
                folder_parts = [item_text.replace("📁 ", "")]
                parent = self.file_tree.parent(item)
                while parent:
                    parent_text = self.file_tree.item(parent, "text")
                    folder_parts.insert(0, parent_text.replace("📁 ", ""))
                    parent = self.file_tree.parent(parent)
                
                if self.app_state.opened_folder_path:
                    folder_path = os.path.join(self.app_state.opened_folder_path, *folder_parts)
                    if os.path.isdir(folder_path):
                        stage_directory(folder_path)
        
        if count:
            self.app.update_staged_files_display()
            msg = f"Staged {count} file(s)."
            if skipped:
                msg += f" Skipped {skipped}."
            self.app.update_status(msg)
    
    def clear_staged_files(self) -> None:
        """Clears all files from the staging area."""
        self.app_state.staged_github_files.clear()
        self.app.update_staged_files_display()
        self.app.update_status("Cleared staged files.")
        
    def update_theme(self) -> None:
        """Updates the theme of all components in the sidebar."""
        if self.file_tree:
            self.file_tree.update_style()
        
        # Re-configure button colors
        self.open_folder_btn.configure(fg_color=self.ds.colors.primary, hover_color=self.ds.colors.primary_hover)
        self.stage_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
        self.clear_stage_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
        
        # Re-configure label colors
        self.current_folder_label.configure(text_color=self.ds.colors.text.secondary)
        
        # Re-configure empty state labels and context menu
        self.context_menu.configure(
            bg=self.ds.colors.surface.card, 
            fg=self.ds.colors.text.primary,
            activebackground=self.ds.colors.primary,
            activeforeground=self.ds.colors.text.on_primary,
            bd=0
        )
        for child in self.empty_state_frame.winfo_children():
            if isinstance(child, ctk.CTkLabel) and "Click 'Open Folder'" in child.cget("text"):
                child.configure(text_color=self.ds.colors.text.secondary)