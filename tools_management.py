import customtkinter as ctk
from tkinter import filedialog
import os
import threading
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import time
import logging
import uuid
from typing import Optional, Dict, List, Any, Callable
from PIL import Image
import concurrent.futures
import subprocess
try:
    from tkinterdnd2 import DND_FILES
except ImportError:
    DND_FILES = "DND_Files"

from design_system import (DS, CardFrame, ButtonWithHover, SecondaryButton, 
                           DangerButton, SuccessButton)
from base_controller import BaseController
from ui_components import CollapsibleFrame, ConfirmationDialog, SearchableComboBox, ButtonSpinner

logger = logging.getLogger(__name__)

class ToolsController(BaseController):
    """Manages the UI and logic for the 'Tools' tab, acting as a hub for various tools."""
    def __init__(self, app: 'CodeMergerApp', app_state: 'AppState', gemini_handler: 'GeminiHandler', github_handler: 'GitHubHandler', ds: DS):
        super().__init__(app)
        self.app = app
        self.app_state = app_state
        self.gemini_handler = gemini_handler
        self.github_handler = github_handler
        self.ds = ds
        self.selected_folder: Optional[str] = None
        self.file_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.current_view: Optional[ctk.CTkFrame] = None
        
        # State for Folder Comparator
        self.folder_a_path: Optional[str] = None
        self.folder_b_path: Optional[str] = None

        # State for Prompt Manager
        self.prompt_widgets: Dict[str, ctk.CTkButton] = {}
        self.selected_prompt_title: Optional[str] = None

        # State for Project Syncer
        self.sync_project_path: Optional[str] = None

        # State for Image Resizer
        self.image_resizer_source_path: Optional[str] = None
        self.image_resizer_output_dir: Optional[str] = None
        self.image_size_checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        # New State for Advanced Image Resizer
        self.resize_mode_var: Optional[ctk.StringVar] = None
        self.resize_width_var: Optional[ctk.StringVar] = None
        self.resize_height_var: Optional[ctk.StringVar] = None
        self.lock_aspect_ratio_var: Optional[ctk.BooleanVar] = None
        self.background_fill_var: Optional[ctk.BooleanVar] = None
        self.bg_color_mode_var: Optional[ctk.StringVar] = None
        self.bg_color_hex_var: Optional[ctk.StringVar] = None
        self.resize_percentage_var: Optional[ctk.DoubleVar] = None
        self.social_media_preset_vars: Dict[str, ctk.BooleanVar] = {}

        # State for Compare Images
        self.compare_img1_path: Optional[str] = None
        self.compare_img2_path: Optional[str] = None
        self.compare_mode_var: Optional[ctk.StringVar] = None
        self.compare_add_text_var: Optional[ctk.BooleanVar] = None
        self.compare_slider_pos: Optional[ctk.DoubleVar] = None
        self.compare_img1_pil: Optional[Image.Image] = None
        self.compare_img2_pil: Optional[Image.Image] = None

        # State for AI Branch Merger
        self.merger_log_text: Optional[ctk.CTkTextbox] = None

    def create_tab(self, tab_frame: ctk.CTkFrame) -> None:
        """Creates the main container and the different tool views within the 'Tools' tab."""
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)

        self.container = ctk.CTkFrame(tab_frame, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.tool_selection_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.extension_changer_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.folder_comparator_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.prompt_manager_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.project_syncer_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.branch_merger_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.image_resizer_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.compare_images_frame = ctk.CTkFrame(self.container, fg_color="transparent")

        self._create_tool_selection_view(self.tool_selection_frame)
        self.current_view = self.tool_selection_frame
        self.tool_selection_frame.grid(row=0, column=0, sticky="nsew")

        # Track which tools have been loaded
        self._tools_loaded = {
            self.extension_changer_frame: False,
            self.folder_comparator_frame: False,
            self.prompt_manager_frame: False,
            self.project_syncer_frame: False,
            self.branch_merger_frame: False,
            self.image_resizer_frame: False,
            self.compare_images_frame: False
        }

    def _switch_view(self, target_view: ctk.CTkFrame) -> None:
        """Handles the instantaneous transition between views, with lazy loading."""
        if target_view == self.current_view:
            return

        # Lazy load the tool content if not already created
        if target_view in self._tools_loaded and not self._tools_loaded[target_view]:
            self.app.update_status("Loading tool...")
            self.app.update_idletasks() # Show immediate feedback
            
            # Map frames to their creation methods
            creation_map = {
                self.extension_changer_frame: self._create_extension_changer_view,
                self.folder_comparator_frame: self._create_folder_comparator_view,
                self.prompt_manager_frame: self._create_prompt_manager_view,
                self.project_syncer_frame: self._create_project_syncer_view,
                self.branch_merger_frame: self._create_branch_merger_view,
                self.image_resizer_frame: self._create_image_resizer_view,
                self.compare_images_frame: self._create_compare_images_view
            }
            
            creator = creation_map.get(target_view)
            if creator:
                creator(target_view)
                self._tools_loaded[target_view] = True
            
            self.app.update_status("Ready")

        # Hide the old view if it exists
        if self.current_view is not None:
            self.current_view.grid_forget()

        # Show the new view
        target_view.grid(row=0, column=0, sticky="nsew")
        self.current_view = target_view

        # Trigger automatic background branch fetch for git-related tools
        if target_view == self.project_syncer_frame:
            repo_url = self.sync_repo_url_entry.get().strip()
            if repo_url and hasattr(self.app, 'git_controller'):
                self.app.git_controller.get_branches_cached_or_refresh(
                    repo_url, 
                    [],
                    custom_callback=self._update_syncer_branch_menu
                )
        elif target_view == self.branch_merger_frame:
            repo_url = self.merger_repo_url_entry.get().strip()
            if repo_url and hasattr(self.app, 'git_controller'):
                self.app.git_controller.get_branches_cached_or_refresh(
                    repo_url, 
                    [],
                    custom_callback=self._update_merger_branch_menus
                )
        


    def _create_tool_selection_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the main tool selection hub."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(parent_frame, text="Available Tools", font=self.ds.typography.h1).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.l)

        scroll_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        scroll_frame.grid_columnconfigure(0, weight=1)

        self.ext_changer_card = CardFrame(scroll_frame, self.ds)
        self.ext_changer_card.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.ext_changer_card.configure(cursor="hand2")
        self.ext_changer_card.bind("<Button-1>", lambda e: self._switch_view(self.extension_changer_frame))
        self.ext_changer_card.bind("<Enter>", lambda e: self.ext_changer_card.configure(border_color=self.ds.colors.primary))
        self.ext_changer_card.bind("<Leave>", lambda e: self.ext_changer_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.ext_changer_card, text="Multi-File Extension Changer", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.ext_changer_card, text="Batch rename file extensions in a folder using an AI assistant.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.folder_comp_card = CardFrame(scroll_frame, self.ds)
        self.folder_comp_card.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.folder_comp_card.configure(cursor="hand2")
        self.folder_comp_card.bind("<Button-1>", lambda e: self._switch_view(self.folder_comparator_frame))
        self.folder_comp_card.bind("<Enter>", lambda e: self.folder_comp_card.configure(border_color=self.ds.colors.primary))
        self.folder_comp_card.bind("<Leave>", lambda e: self.folder_comp_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.folder_comp_card, text="Folder Comparator", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.folder_comp_card, text="Compare the contents of two folders to find differences.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.prompt_lib_card = CardFrame(scroll_frame, self.ds)
        self.prompt_lib_card.grid(row=2, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.prompt_lib_card.configure(cursor="hand2")
        self.prompt_lib_card.bind("<Button-1>", lambda e: self._switch_view(self.prompt_manager_frame))
        self.prompt_lib_card.bind("<Enter>", lambda e: self.prompt_lib_card.configure(border_color=self.ds.colors.primary))
        self.prompt_lib_card.bind("<Leave>", lambda e: self.prompt_lib_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.prompt_lib_card, text="System Prompt Library", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.prompt_lib_card, text="Create, manage, and activate different system prompts for the AI.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.project_syncer_card = CardFrame(scroll_frame, self.ds)
        self.project_syncer_card.grid(row=3, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.project_syncer_card.configure(cursor="hand2")
        self.project_syncer_card.bind("<Button-1>", lambda e: self._switch_view(self.project_syncer_frame))
        self.project_syncer_card.bind("<Enter>", lambda e: self.project_syncer_card.configure(border_color=self.ds.colors.primary))
        self.project_syncer_card.bind("<Leave>", lambda e: self.project_syncer_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.project_syncer_card, text="Project Syncer", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.project_syncer_card, text="Destructively overwrite a local folder with a remote GitHub branch.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.branch_merger_card = CardFrame(scroll_frame, self.ds)
        self.branch_merger_card.grid(row=4, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.branch_merger_card.configure(cursor="hand2")
        self.branch_merger_card.bind("<Button-1>", lambda e: self._switch_view(self.branch_merger_frame))
        self.branch_merger_card.bind("<Enter>", lambda e: self.branch_merger_card.configure(border_color=self.ds.colors.primary))
        self.branch_merger_card.bind("<Leave>", lambda e: self.branch_merger_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.branch_merger_card, text="AI Branch Merger", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.branch_merger_card, text="Merge two branches in a GitHub repository, using AI to automatically resolve conflicts.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.image_resizer_card = CardFrame(scroll_frame, self.ds)
        self.image_resizer_card.grid(row=5, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.image_resizer_card.configure(cursor="hand2")
        self.image_resizer_card.bind("<Button-1>", lambda e: self._switch_view(self.image_resizer_frame))
        self.image_resizer_card.bind("<Enter>", lambda e: self.image_resizer_card.configure(border_color=self.ds.colors.primary))
        self.image_resizer_card.bind("<Leave>", lambda e: self.image_resizer_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.image_resizer_card, text="🖼️ Image Resizer", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.image_resizer_card, text="Resize images to multiple sizes at once. Includes Chrome extension icon presets.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        self.compare_images_card = CardFrame(scroll_frame, self.ds)
        self.compare_images_card.grid(row=6, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.compare_images_card.configure(cursor="hand2")
        self.compare_images_card.bind("<Button-1>", lambda e: self._switch_view(self.compare_images_frame))
        self.compare_images_card.bind("<Enter>", lambda e: self.compare_images_card.configure(border_color=self.ds.colors.primary))
        self.compare_images_card.bind("<Leave>", lambda e: self.compare_images_card.configure(border_color=self.ds.colors.border))
        ctk.CTkLabel(self.compare_images_card, text="🔍 Compare Images", font=self.ds.typography.h2, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        ctk.CTkLabel(self.compare_images_card, text="Compare two images side-by-side or with an interactive slider. Export comparisons effortlessly.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary, cursor="hand2").pack(anchor="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))


    def _create_extension_changer_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'Multi-File Extension Changer' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        main_scroll_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        main_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        main_scroll_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        back_btn = ButtonWithHover(header_frame, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120)
        back_btn.pack(side="left")

        self.extension_tool_card_inner = CardFrame(main_scroll_frame, self.ds)
        self.extension_tool_card_inner.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.extension_tool_card_inner.grid_columnconfigure(0, weight=1)
        self.extension_tool_card_inner.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.extension_tool_card_inner, text="Multi-File Extension Changer", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))

        folder_frame = ctk.CTkFrame(self.extension_tool_card_inner, fg_color="transparent")
        folder_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        folder_frame.grid_columnconfigure(1, weight=1)
        self.select_folder_btn = ButtonWithHover(folder_frame, self.ds, text="Select Folder...", command=self._select_folder)
        self.select_folder_btn.grid(row=0, column=0, sticky="w")
        self.folder_label = ctk.CTkLabel(folder_frame, text="No folder selected.", text_color=self.ds.colors.text.secondary)
        self.folder_label.grid(row=0, column=1, sticky="ew", padx=self.ds.spacing.m)

        # Toggle for including sub-folder files
        self.include_subfolders_var = ctk.BooleanVar(value=True)
        self.include_subfolders_cb = ctk.CTkCheckBox(
            folder_frame, 
            text="Rename also sub-folder files", 
            variable=self.include_subfolders_var,
            command=self._populate_file_list
        )
        self.include_subfolders_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(self.ds.spacing.s, 0))

        self.file_list_frame = ctk.CTkScrollableFrame(self.extension_tool_card_inner, fg_color="transparent", height=200)
        self.file_list_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        self._show_file_list_empty_state()

        self.ai_card = CardFrame(main_scroll_frame, self.ds)
        self.ai_card.grid(row=1, column=0, sticky="ew")
        self.ai_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.ai_card, text="AI Renaming Assistant", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        self.ai_chat_entry = ctk.CTkTextbox(self.ai_card, height=60, font=self.ds.typography.body, wrap="word")
        self.ai_chat_entry.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        self.ai_chat_entry.insert("1.0", "e.g., change all .py files to .txt")
        self.ai_apply_btn = SuccessButton(self.ai_card, self.ds, text="Run AI Rename", command=self._start_ai_rename_thread, height=40)
        self.ai_apply_btn.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

    def _select_folder(self) -> None:
        """Opens a dialog to select a folder and populates the file list."""
        path = filedialog.askdirectory()
        if path:
            self.selected_folder = path
            self.folder_label.configure(text=path, text_color=self.ds.colors.text.primary)
            self._populate_file_list()

    def _populate_file_list(self) -> None:
        """Scans the selected folder and lists files with checkboxes.
        Optimized to reuse existing widgets where possible."""
        if not self.selected_folder:
            self._show_file_list_empty_state()
            return

        try:
            files = []
            include_subfolders = self.include_subfolders_var.get()
            
            if include_subfolders:
                # Recursively walk through all subdirectories
                for dirpath, _, filenames in os.walk(self.selected_folder):
                    for filename in filenames:
                        full_path = os.path.join(dirpath, filename)
                        # Store relative path from selected folder
                        rel_path = os.path.relpath(full_path, self.selected_folder)
                        files.append(rel_path)
            else:
                # Only get files directly in the selected folder
                files = [f for f in os.listdir(self.selected_folder) if os.path.isfile(os.path.join(self.selected_folder, f))]
            
            if not files:
                # Clear existing widgets and show empty state
                for widget in self.file_list_frame.winfo_children():
                    widget.destroy()
                self.file_checkboxes.clear()
                ctk.CTkLabel(self.file_list_frame, text="No files found in this folder.", text_color=self.ds.colors.text.secondary).pack()
                return

            new_files_set = set(sorted(files))
            existing_files_set = set(self.file_checkboxes.keys())
            
            # Remove checkboxes for files that no longer exist
            files_to_remove = existing_files_set - new_files_set
            for filepath in files_to_remove:
                if filepath in self.file_checkboxes:
                    self.file_checkboxes[filepath].destroy()
                    del self.file_checkboxes[filepath]
            
            # Add checkboxes for new files (keep existing ones)
            files_to_add = new_files_set - existing_files_set
            for filepath in sorted(files_to_add):
                cb = ctk.CTkCheckBox(self.file_list_frame, text=filepath)
                cb.pack(anchor="w", padx=self.ds.spacing.m, pady=self.ds.spacing.s)
                cb.select()  # Select all by default
                self.file_checkboxes[filepath] = cb
                
        except Exception as e:
            self.app.show_toast(f"Error reading folder: {e}", "error")

    def _show_file_list_empty_state(self) -> None:
        """Displays a message when no folder is selected."""
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.file_list_frame, text="Select a folder to see files.", text_color=self.ds.colors.text.secondary).pack(pady=20)
    
    def _start_ai_rename_thread(self) -> None:
        """Validates inputs and starts the AI rename process in a thread."""
        command = self.ai_chat_entry.get("1.0", "end-1c").strip()
        if not self.selected_folder or not self.file_checkboxes:
            self.app.show_toast("Please select a folder with files first.", "warning"); return
        if not command or "e.g.," in command:
            self.app.show_toast("Please enter a command for the AI.", "warning"); return
        
        self.ai_apply_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_ai_rename_threaded, args=(command,), daemon=True).start()

    def _run_ai_rename_threaded(self, command: str) -> None:
        """Worker thread that calls Gemini to get rename instructions and applies them."""
        try:
            current_files = list(self.file_checkboxes.keys())
            self.app.update_status("Asking AI to interpret rename command...")
            rename_map_str = self.gemini_handler.interpret_file_rename_command(current_files, command)
            
            clean_json_str = rename_map_str.strip().replace("```json", "").replace("```", "")
            rename_map = json.loads(clean_json_str)

            self.app.update_status("Applying AI-suggested renames...")
            changed_count = 0
            for old_name, new_name in rename_map.items():
                if old_name in self.file_checkboxes and self.file_checkboxes[old_name].get() == 1:
                    if not self.selected_folder: continue
                    old_path = os.path.join(self.selected_folder, old_name)
                    new_path = os.path.join(self.selected_folder, new_name)

                    if old_path == new_path: continue

                    if os.path.exists(new_path):
                        self.app.after(0, self.app.show_toast, f"Skipping rename: '{new_name}' already exists.", "warning")
                        continue
                    
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
                        changed_count += 1
            
            self.app.after(0, self.app.show_toast, f"Successfully renamed {changed_count} file(s).", "success")
            self.app.after(0, self._populate_file_list)

        except json.JSONDecodeError:
            self.app.after(0, self.app.show_toast, "AI returned an invalid format. Please try again.", "error")
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An error occurred: {e}", "error")
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.ai_apply_btn.configure(state="normal"))

    def _create_folder_comparator_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'Folder Comparator' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        ButtonWithHover(header_frame, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120).pack(side="left")

        main_scroll = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        main_scroll.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        main_scroll.grid_columnconfigure(0, weight=1)

        # --- Selection Card ---
        self.comp_selection_card = CardFrame(main_scroll, self.ds)
        self.comp_selection_card.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        self.comp_selection_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.comp_selection_card, text="Select Folders to Compare", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        ButtonWithHover(self.comp_selection_card, self.ds, text="Select Folder A", command=self._select_folder_a).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.folder_a_label = ctk.CTkLabel(self.comp_selection_card, text="Not selected", text_color=self.ds.colors.text.secondary)
        self.folder_a_label.grid(row=1, column=1, padx=self.ds.spacing.m, sticky="ew")

        ButtonWithHover(self.comp_selection_card, self.ds, text="Select Folder B", command=self._select_folder_b).grid(row=2, column=0, padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="w")
        self.folder_b_label = ctk.CTkLabel(self.comp_selection_card, text="Not selected", text_color=self.ds.colors.text.secondary)
        self.folder_b_label.grid(row=2, column=1, padx=self.ds.spacing.m, sticky="ew")
        
        self.compare_btn = SuccessButton(self.comp_selection_card, self.ds, text="Compare Folders", command=self._start_folder_compare_thread, height=40)
        self.compare_btn.grid(row=3, column=0, columnspan=2, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        # --- Results Card ---
        self.results_card = CardFrame(main_scroll, self.ds)
        self.results_card.grid(row=1, column=0, sticky="ew")
        self.results_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.results_card, text="Comparison Results", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        self.results_frame = ctk.CTkFrame(self.results_card, fg_color="transparent")
        self.results_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))
        self.results_frame.grid_columnconfigure(0, weight=1)

        self.only_a_frame = CollapsibleFrame(self.results_frame, self.ds, title="Files only in Folder A")
        self.only_a_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.s))
        self.only_b_frame = CollapsibleFrame(self.results_frame, self.ds, title="Files only in Folder B")
        self.only_b_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.s))
        self.modified_frame = CollapsibleFrame(self.results_frame, self.ds, title="Modified Files")
        self.modified_frame.grid(row=2, column=0, sticky="ew", pady=(0, self.ds.spacing.s))
        
        self.no_diff_label = ctk.CTkLabel(self.results_frame, text="Select two folders and click Compare.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary)
        self.no_diff_label.grid(row=3, column=0, pady=self.ds.spacing.l)

    def _select_folder_a(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.folder_a_path = path
            self.folder_a_label.configure(text=path, text_color=self.ds.colors.text.primary)

    def _select_folder_b(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.folder_b_path = path
            self.folder_b_label.configure(text=path, text_color=self.ds.colors.text.primary)

    def _start_folder_compare_thread(self) -> None:
        if not self.folder_a_path or not self.folder_b_path:
            self.app.show_toast("Please select both Folder A and Folder B.", "warning")
            return
        self.compare_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_folder_compare_threaded, daemon=True).start()

    def _run_folder_compare_threaded(self) -> None:
        try:
            self.app.update_status("Scanning folders...")
            files_a = self._get_file_hashes(self.folder_a_path)
            files_b = self._get_file_hashes(self.folder_b_path)
            
            self.app.update_status("Comparing files...")
            set_a = set(files_a.keys())
            set_b = set(files_b.keys())
            
            only_in_a = sorted(list(set_a - set_b))
            only_in_b = sorted(list(set_b - set_a))
            common_files = set_a & set_b
            
            modified = []
            for file in sorted(list(common_files)):
                if files_a[file] != files_b[file]:
                    modified.append(file)
            
            self.app.after(0, self._display_comparison_results, only_in_a, only_in_b, modified)

        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An error occurred: {e}", "error")
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.compare_btn.configure(state="normal"))

    def _get_file_hashes(self, start_path: str) -> Dict[str, str]:
        """Recursively walks a directory and returns a dict of {relative_path: hash}.
        Uses parallel processing for improved performance on large directories."""
        files_to_hash = []
        ignored_dirs = {".git", "__pycache__", ".vscode", "node_modules", "venv", ".env"}
        for dirpath, dirs, filenames in os.walk(start_path):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                full_path = os.path.join(dirpath, filename)
                relative_path = os.path.relpath(full_path, start_path).replace("\\", "/")
                files_to_hash.append((relative_path, full_path))
        
        hashes = {}
        # Use ThreadPoolExecutor for parallel hashing (I/O bound operation)
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as executor:
            future_to_path = {
                executor.submit(self._calculate_file_hash, full_path): rel_path
                for rel_path, full_path in files_to_hash
            }
            for future in as_completed(future_to_path):
                rel_path = future_to_path[future]
                try:
                    hashes[rel_path] = future.result()
                except Exception:
                    hashes[rel_path] = ""
        return hashes

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculates the SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except (IOError, PermissionError):
            return ""

    def _display_comparison_results(self, only_a: list, only_b: list, modified: list) -> None:
        """Updates the UI with the comparison results."""
        self.only_a_frame.update_widgets(only_a)
        self.only_b_frame.update_widgets(only_b)
        self.modified_frame.update_widgets(modified)
        
        if not any([only_a, only_b, modified]):
            self.no_diff_label.configure(text="Folders are identical.", text_color=self.ds.colors.success)
            self.no_diff_label.grid()
        else:
            self.no_diff_label.grid_forget()
        self.app.show_toast("Comparison complete!", "success")
        
    def _create_prompt_manager_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'System Prompt Library' tool."""
        parent_frame.grid_columnconfigure(1, weight=3)
        parent_frame.grid_columnconfigure(0, weight=1, minsize=250)
        parent_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        ButtonWithHover(header_frame, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120).pack(side="left")
        
        # --- Left Panel: Prompt List ---
        list_card = CardFrame(parent_frame, self.ds)
        list_card.grid(row=1, column=0, sticky="nsew", padx=(self.ds.spacing.m, self.ds.spacing.s), pady=(0, self.ds.spacing.m))
        list_card.grid_rowconfigure(1, weight=1)
        list_card.grid_columnconfigure(0, weight=1)
        
        list_header = ctk.CTkFrame(list_card, fg_color="transparent")
        list_header.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        list_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(list_header, text="Prompts", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w")
        ButtonWithHover(list_header, self.ds, text="➕ New", width=60, command=self._new_prompt).grid(row=0, column=1, sticky="e")
        
        self.prompt_list_frame = ctk.CTkScrollableFrame(list_card, fg_color=self.ds.colors.surface.section)
        self.prompt_list_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.s, pady=(0, self.ds.spacing.s))
        self.prompt_list_frame.grid_columnconfigure(0, weight=1)

        # --- Editor ---
        editor_card = CardFrame(parent_frame, self.ds)
        editor_card.grid(row=1, column=1, sticky="nsew", padx=(self.ds.spacing.s, self.ds.spacing.m), pady=(0, self.ds.spacing.m))
        editor_card.grid_rowconfigure(2, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(editor_card, text="Prompt Title:", font=self.ds.typography.body_bold).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.m, pady=(self.ds.spacing.m, 0))
        self.prompt_title_entry = ctk.CTkEntry(editor_card, font=self.ds.typography.body)
        self.prompt_title_entry.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(self.ds.spacing.s, self.ds.spacing.m))
        
        self.prompt_content_text = ctk.CTkTextbox(editor_card, font=self.ds.typography.code, wrap="word")
        self.prompt_content_text.grid(row=2, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        
        actions_frame = ctk.CTkFrame(editor_card, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        actions_frame.grid_columnconfigure(3, weight=1)
        
        SuccessButton(actions_frame, self.ds, text="💾 Save", command=self._save_prompt).grid(row=0, column=0, padx=(0, self.ds.spacing.s))
        DangerButton(actions_frame, self.ds, text="🗑️ Delete", command=self._delete_prompt).grid(row=0, column=1, padx=(0, self.ds.spacing.s))
        SecondaryButton(actions_frame, self.ds, text="📋 Copy", command=self._copy_prompt).grid(row=0, column=2)
        ButtonWithHover(actions_frame, self.ds, text="🚀 Set as Active Prompt", command=self._set_active_prompt).grid(row=0, column=3, sticky="e")
        
        self._populate_prompt_list()
        self._new_prompt()

    def _populate_prompt_list(self) -> None:
        """Loads prompts from settings and displays them in the list."""
        for widget in self.prompt_list_frame.winfo_children():
            widget.destroy()
        self.prompt_widgets.clear()
        
        prompts = self.app_state.settings_manager.get('saved_system_prompts', [])
        for i, prompt in enumerate(prompts):
            title = prompt.get('title', 'Untitled')
            btn = ctk.CTkButton(self.prompt_list_frame, text=title, anchor="w", fg_color="transparent",
                                command=lambda t=title: self._on_prompt_select(t))
            btn.grid(row=i, column=0, sticky="ew", pady=(0, 2))
            self.prompt_widgets[title] = btn
    
    def _on_prompt_select(self, title: str) -> None:
        """Handles selection of a prompt from the list."""
        self.selected_prompt_title = title
        prompts = self.app_state.settings_manager.get('saved_system_prompts', [])
        prompt_data = next((p for p in prompts if p.get('title') == title), None)

        if prompt_data:
            self.prompt_title_entry.delete(0, "end")
            self.prompt_title_entry.insert(0, prompt_data.get('title', ''))
            self.prompt_content_text.delete("1.0", "end")
            self.prompt_content_text.insert("1.0", prompt_data.get('prompt', ''))
        
        for t, btn in self.prompt_widgets.items():
            btn.configure(fg_color=self.ds.colors.primary if t == title else "transparent")

    def _new_prompt(self) -> None:
        """Clears the editor for a new prompt."""
        self.selected_prompt_title = None
        self.prompt_title_entry.delete(0, "end")
        self.prompt_content_text.delete("1.0", "end")
        for btn in self.prompt_widgets.values():
            btn.configure(fg_color="transparent")
        self.prompt_title_entry.focus()

    def _save_prompt(self) -> None:
        """Saves the current prompt (new or existing)."""
        title = self.prompt_title_entry.get().strip()
        content = self.prompt_content_text.get("1.0", "end-1c").strip()

        if not title or not content:
            self.app.show_toast("Title and prompt content cannot be empty.", "warning")
            return
            
        prompts = self.app_state.settings_manager.get('saved_system_prompts', [])
        
        # Check if we are updating an existing prompt or creating a new one
        existing_prompt = next((p for p in prompts if p.get('title') == self.selected_prompt_title), None)
        
        if self.selected_prompt_title and not existing_prompt: # Renaming a prompt
            existing_prompt = next((p for p in prompts if p.get('title') == self.selected_prompt_title), None)

        if existing_prompt and title != self.selected_prompt_title and any(p['title'] == title for p in prompts):
             self.app.show_toast(f"A prompt with the title '{title}' already exists.", "error")
             return
        
        if existing_prompt:
            existing_prompt['title'] = title
            existing_prompt['prompt'] = content
        else: # New prompt
             if any(p['title'] == title for p in prompts):
                self.app.show_toast(f"A prompt with the title '{title}' already exists.", "error")
                return
             prompts.append({'title': title, 'prompt': content})
        
        self.app_state.settings_manager.set('saved_system_prompts', prompts)
        self._populate_prompt_list()
        self.selected_prompt_title = title # Update selection to new title
        self._on_prompt_select(title)
        self.app.show_toast("Prompt saved successfully!", "success")

    def _delete_prompt(self) -> None:
        """Deletes the currently selected prompt."""
        if not self.selected_prompt_title:
            self.app.show_toast("No prompt selected to delete.", "warning")
            return

        ConfirmationDialog(
            self.app, self.ds, "Delete Prompt",
            f"Are you sure you want to delete the prompt '{self.selected_prompt_title}'?",
            self._confirm_delete
        )

    def _confirm_delete(self) -> None:
        if not self.selected_prompt_title: return
        prompts = self.app_state.settings_manager.get('saved_system_prompts', [])
        prompts_after_delete = [p for p in prompts if p.get('title') != self.selected_prompt_title]
        self.app_state.settings_manager.set('saved_system_prompts', prompts_after_delete)
        
        self._populate_prompt_list()
        self._new_prompt()
        self.app.show_toast("Prompt deleted.", "info")

    def _set_active_prompt(self) -> None:
        """Sets the current prompt's content as the main system prompt."""
        content = self.prompt_content_text.get("1.0", "end-1c").strip()
        if not content:
            self.app.show_toast("Cannot set an empty prompt.", "warning")
            return
            
        self.app.update_system_prompt_text(content)
        self.app.tab_view.set("⚙️Settings")
        self.app.show_toast("System prompt updated in Settings!", "success")

    def _copy_prompt(self) -> None:
        """Copies the content of the prompt editor to the clipboard."""
        content = self.prompt_content_text.get("1.0", "end-1c")
        if content:
            self.app.clipboard_clear()
            self.app.clipboard_append(content)
            self.app.show_toast("Prompt copied to clipboard!", "success")
        else:
            self.app.show_toast("Nothing to copy.", "info")

    def _create_project_syncer_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'Project Syncer' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        ButtonWithHover(header_frame, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120).pack(side="left")

        main_scroll = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        main_scroll.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        main_scroll.grid_columnconfigure(0, weight=1)

        self.sync_card = CardFrame(main_scroll, self.ds)
        self.sync_card.grid(row=0, column=0, sticky="ew")
        self.sync_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.sync_card, text="Sync Local Folder from GitHub", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=3, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        ButtonWithHover(self.sync_card, self.ds, text="Select Local Folder", command=self._select_sync_project_folder).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.sync_project_path_label = ctk.CTkLabel(self.sync_card, text="Not selected", text_color=self.ds.colors.text.secondary)
        self.sync_project_path_label.grid(row=1, column=1, columnspan=2, padx=self.ds.spacing.m, sticky="ew")

        ctk.CTkLabel(self.sync_card, text="GitHub Repo URL:").grid(row=2, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.sync_repo_url_entry = SearchableComboBox(self.sync_card, values=self.app_state.github_repos if self.app_state.github_repos else [""], command=self._on_syncer_repo_change)
        self.sync_repo_url_entry.grid(row=2, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")

        ctk.CTkLabel(self.sync_card, text="Branch:").grid(row=3, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.sync_branch_menu = ctk.CTkComboBox(self.sync_card, values=["main"])
        self.sync_branch_menu.grid(row=3, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")

        warning_frame = ctk.CTkFrame(self.sync_card, fg_color=self.ds.colors.surface.section, corner_radius=self.ds.spacing.s)
        warning_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        ctk.CTkLabel(warning_frame, text="⚠️ WARNING: This action will overwrite local files that also exist in the remote repository. Files that only exist locally will not be deleted.", text_color=self.ds.colors.warning, wraplength=500).pack(padx=self.ds.spacing.m, pady=self.ds.spacing.m)

        self.sync_project_btn = SuccessButton(self.sync_card, self.ds, text="Sync and Update Local Project", command=self._start_sync_project_thread, height=40)
        self.sync_project_btn.grid(row=5, column=0, columnspan=3, sticky="ew", padx=self.ds.spacing.l, pady=(self.ds.spacing.m, self.ds.spacing.l))

    def _select_sync_project_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.sync_project_path = path
            self.sync_project_path_label.configure(text=path, text_color=self.ds.colors.text.primary)

    def _on_syncer_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the Project Syncer."""
        repo_url = repo_url.strip()
        if repo_url and hasattr(self.app, 'git_controller'):
            self.app.git_controller.get_branches_cached_or_refresh(
                repo_url, 
                [],
                custom_callback=self._update_syncer_branch_menu
            )

    def _update_syncer_branch_menu(self, branches: List[str]) -> None:
        if branches:
            current_val = self.sync_branch_menu.get()
            self.sync_branch_menu.configure(values=branches)
            if current_val in branches:
                self.sync_branch_menu.set(current_val)
            else:
                self.sync_branch_menu.set(branches[0])
        else:
            self.sync_branch_menu.configure(values=["main"])
            self.sync_branch_menu.set("main")

    def _start_sync_project_thread(self) -> None:
        local_path = self.sync_project_path
        repo_url = self.sync_repo_url_entry.get().strip()
        branch = self.sync_branch_menu.get().strip()
        token = self.app_state.settings_manager.get_github_token()

        if not all([local_path, repo_url, branch, token]):
            self.app.show_toast("Local Folder, Repo URL, Branch, and GitHub Token (in Settings) are all required.", "warning")
            return
            
        ConfirmationDialog(
            self.app, self.ds, "Confirm Project Sync",
            f"This will update your local folder '{os.path.basename(local_path)}' with the content from the '{branch}' branch. Any local files that also exist in the repo will be overwritten.\n\nAre you sure you want to proceed?",
            self._execute_sync_project_thread
        )

    def _execute_sync_project_thread(self) -> None:
        self.sync_project_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_sync_project_threaded, daemon=True).start()
        
    def _run_sync_project_threaded(self) -> None:
        local_path = self.sync_project_path
        repo_url = self.sync_repo_url_entry.get().strip()
        branch = self.sync_branch_menu.get().strip()
        token = self.app_state.settings_manager.get_github_token()

        if not all([local_path, repo_url, branch, token]): return

        try:
            self.app.update_status(f"Fetching remote files from '{branch}'...")
            remote_files = self.github_handler.get_remote_files(token, repo_url, branch)

            self.app.update_status(f"Updating {len(remote_files)} files in local folder...")
            for rel_path, content in remote_files.items():
                new_local_path = os.path.join(local_path, rel_path)
                os.makedirs(os.path.dirname(new_local_path), exist_ok=True)
                with open(new_local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.app.after(0, self.app.show_toast, "Project sync completed successfully!", "success")

        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An error occurred during sync: {e}", "error")
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.sync_project_btn.configure(state="normal"))

    def _create_branch_merger_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'AI Branch Merger' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        ButtonWithHover(header_frame, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120).pack(side="left")

        main_scroll = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        main_scroll.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        main_scroll.grid_columnconfigure(0, weight=1)
        main_scroll.grid_rowconfigure(2, weight=1) # Make log frame expand

        # --- Repo Card ---
        repo_card = CardFrame(main_scroll, self.ds)
        repo_card.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        repo_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(repo_card, text="Repository & Branches", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=3, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        ctk.CTkLabel(repo_card, text="GitHub Repo URL:").grid(row=1, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.merger_repo_url_entry = SearchableComboBox(repo_card, values=self.app_state.github_repos if self.app_state.github_repos else [""], command=self._on_merger_repo_change)
        self.merger_repo_url_entry.grid(row=1, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")

        ctk.CTkLabel(repo_card, text="Source Branch:").grid(row=2, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.merger_source_branch_menu = ctk.CTkComboBox(repo_card, values=["dev"])
        self.merger_source_branch_menu.grid(row=2, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        
        ctk.CTkLabel(repo_card, text="Destination Branch:").grid(row=3, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.merger_dest_branch_menu = ctk.CTkComboBox(repo_card, values=["main"])
        self.merger_dest_branch_menu.grid(row=3, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")

        # --- Options Card ---
        options_card = CardFrame(main_scroll, self.ds)
        options_card.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.l))
        options_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(options_card, text="Merge Options", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        priority_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        priority_frame.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        ctk.CTkLabel(priority_frame, text="Conflict Priority:", font=self.ds.typography.body).pack(side="left")
        self.merger_priority_selector = ctk.CTkSegmentedButton(priority_frame, values=["Source", "Destination"])
        self.merger_priority_selector.pack(side="left", padx=self.ds.spacing.m)
        self.merger_priority_selector.set("Source")

        ctk.CTkLabel(options_card, text="Pull Request Details:", font=self.ds.typography.body).grid(row=2, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        self.merger_pr_details_text = ctk.CTkTextbox(options_card, height=80, font=self.ds.typography.body, wrap="word")
        self.merger_pr_details_text.grid(row=3, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        self.merger_pr_details_text.insert("1.0", "feat: Merge branch 'source' into 'destination' with AI conflict resolution\n\nThis PR was generated by the AI Branch Merger tool.")

        self.start_merge_btn = DangerButton(options_card, self.ds, text="🚀 Create Merge Pull Request", command=self._start_branch_merge_thread, height=40)
        self.start_merge_btn.grid(row=4, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

        # --- Log Card ---
        log_card = CardFrame(main_scroll, self.ds)
        log_card.grid(row=2, column=0, sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1); log_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_card, text="Merge Log", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        self.merger_log_text = ctk.CTkTextbox(log_card, font=self.ds.typography.code_small, wrap="word", state="disabled")
        self.merger_log_text.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

    def _add_merger_log(self, message: str):
        """Appends a message to the merger log text box in a thread-safe way."""
        def append_log():
            self.merger_log_text.configure(state="normal")
            self.merger_log_text.insert("end", f"{message}\n")
            self.merger_log_text.configure(state="disabled")
            self.merger_log_text.see("end")
        self.app.after(0, append_log)

    def _on_merger_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the AI Branch Merger."""
        repo_url = repo_url.strip()
        if repo_url and hasattr(self.app, 'git_controller'):
            self.app.git_controller.get_branches_cached_or_refresh(
                repo_url, 
                [],
                custom_callback=self._update_merger_branch_menus
            )

    def _update_merger_branch_menus(self, branches: List[str]) -> None:
        if branches:
            # Source menu
            current_source = self.merger_source_branch_menu.get()
            self.merger_source_branch_menu.configure(values=branches)
            if current_source in branches: self.merger_source_branch_menu.set(current_source)
            else: self.merger_source_branch_menu.set(branches[0] if branches else "")
            
            # Destination menu
            current_dest = self.merger_dest_branch_menu.get()
            self.merger_dest_branch_menu.configure(values=branches)
            if current_dest in branches: self.merger_dest_branch_menu.set(current_dest)
            elif len(branches) > 1: self.merger_dest_branch_menu.set(branches[1])
            elif branches: self.merger_dest_branch_menu.set(branches[0])
            else: self.merger_dest_branch_menu.set("")
        else:
            self.merger_source_branch_menu.configure(values=[])
            self.merger_dest_branch_menu.configure(values=[])

    def _start_branch_merge_thread(self) -> None:
        repo_url = self.merger_repo_url_entry.get().strip()
        source_branch = self.merger_source_branch_menu.get()
        dest_branch = self.merger_dest_branch_menu.get()
        token = self.app_state.settings_manager.get_github_token()

        if not all([repo_url, source_branch, dest_branch, token]):
            self.app.show_toast("Repo URL, branches, and GitHub Token are required.", "warning")
            return
        if source_branch == dest_branch:
            self.app.show_toast("Source and destination branches cannot be the same.", "warning")
            return

        ConfirmationDialog(
            self.app, self.ds, "Confirm AI Branch Merge",
            f"This will create a new branch and open a pull request from '{source_branch}' to '{dest_branch}'.\n\nNo changes will be merged directly. You will be able to review the changes in the pull request.\n\nAre you sure you want to proceed?",
            self._execute_branch_merge_thread
        )
    
    def _execute_branch_merge_thread(self) -> None:
        self.start_merge_btn.configure(state="disabled")
        self.merger_log_text.configure(state="normal"); self.merger_log_text.delete("1.0", "end"); self.merger_log_text.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_branch_merge_threaded, daemon=True).start()

    def _run_branch_merge_threaded(self) -> None:
        repo_url = self.merger_repo_url_entry.get().strip()
        source_branch = self.merger_source_branch_menu.get()
        dest_branch = self.merger_dest_branch_menu.get()
        priority = self.merger_priority_selector.get().lower()
        pr_details = self.merger_pr_details_text.get("1.0", "end-1c").strip()
        token = self.app_state.settings_manager.get_github_token()
        
        if not all([repo_url, source_branch, dest_branch, priority, token]): return

        if not pr_details:
            self.app.after(0, self.app.show_toast, "Pull Request details cannot be empty.", "error")
            self._add_merger_log("\nERROR: Pull Request details cannot be empty.")
            return

        pr_lines = pr_details.split('\n')
        pr_title = pr_lines[0]
        pr_body = '\n'.join(pr_lines[1:]).strip()
        
        try:
            self._add_merger_log(f"Starting merge of '{source_branch}' into '{dest_branch}'...")
            
            self._add_merger_log(f"Fetching files from source branch: {source_branch}...")
            source_files = self.github_handler.get_remote_files(token, repo_url, source_branch)
            self._add_merger_log(f"Found {len(source_files)} files in source.")

            self._add_merger_log(f"Fetching files from destination branch: {dest_branch}...")
            dest_files = self.github_handler.get_remote_files(token, repo_url, dest_branch)
            self._add_merger_log(f"Found {len(dest_files)} files in destination.")

            final_files = dest_files.copy() # Start with destination files, then update
            source_keys = set(source_files.keys())
            dest_keys = set(dest_files.keys())

            new_files = source_keys - dest_keys
            deleted_files = dest_keys - source_keys
            common_files = source_keys & dest_keys

            self._add_merger_log(f"\nAnalysis complete:")
            self._add_merger_log(f"- {len(new_files)} new file(s) to add.")
            self._add_merger_log(f"- {len(deleted_files)} file(s) to delete.")
            self._add_merger_log(f"- {len(common_files)} common file(s) to check for conflicts.")

            # Add new files
            for path in new_files:
                final_files[path] = source_files[path]
            
            # Remove deleted files
            for path in deleted_files:
                del final_files[path]

            # Resolve conflicts in common files
            conflict_count = 0
            for path in common_files:
                if source_files[path] != dest_files[path]:
                    conflict_count += 1
                    self._add_merger_log(f"  - Conflict detected in '{path}'. Resolving with AI...")
                    
                    merged_code = self.gemini_handler.run_ai_branch_merge(
                        source_code=source_files[path],
                        destination_code=dest_files[path],
                        file_path=path,
                        priority=priority
                    )
                    final_files[path] = merged_code
                    self._add_merger_log(f"  - AI resolution for '{path}' complete.")
            
            if conflict_count == 0 and not new_files and not deleted_files:
                self.app.after(0, self.app.show_toast, "Branches are already in sync.", "info")
                self._add_merger_log("\nBranches are already in sync. No merge needed.")
                return

            new_branch_name = f"ai-merge/{source_branch}-into-{dest_branch}/{int(time.time())}"
            self._add_merger_log(f"\nPreparing to create pull request from new branch '{new_branch_name}'...")
            
            pr_url = self.github_handler.create_pull_request_with_changes(
                token, repo_url, dest_branch, new_branch_name, final_files, pr_title, pr_body
            )
            
            if pr_url:
                self.app.after(0, self.app.show_toast, "AI Merge PR created!", "success")
                self._add_merger_log(f"\nSUCCESS: Pull request created.")
                self._add_merger_log(f"View it here: {pr_url}")
            else:
                self._add_merger_log(f"\nERROR: Failed to create pull request. Check toast notifications for details.")

        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An unexpected error occurred: {e}", "error")
            self._add_merger_log(f"\nFATAL ERROR: {e}")
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.start_merge_btn.configure(state="normal"))

    def update_theme(self) -> None:
        """Updates the theme for all components in the Tools tab."""
        # --- Tool Selection View ---
        if hasattr(self, 'ext_changer_card'):
            self.ext_changer_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            for child in self.ext_changer_card.winfo_children():
                if isinstance(child, ctk.CTkLabel) and "Batch rename" in child.cget("text"):
                     child.configure(text_color=self.ds.colors.text.secondary)
        if hasattr(self, 'folder_comp_card'):
            self.folder_comp_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            for child in self.folder_comp_card.winfo_children():
                if isinstance(child, ctk.CTkLabel) and "Compare the contents" in child.cget("text"):
                     child.configure(text_color=self.ds.colors.text.secondary)
        if hasattr(self, 'prompt_lib_card'):
            self.prompt_lib_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            for child in self.prompt_lib_card.winfo_children():
                if isinstance(child, ctk.CTkLabel) and "Create, manage, and activate" in child.cget("text"):
                     child.configure(text_color=self.ds.colors.text.secondary)

        if hasattr(self, 'project_syncer_card'):
            self.project_syncer_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            for child in self.project_syncer_card.winfo_children():
                if isinstance(child, ctk.CTkLabel) and "Destructively overwrite" in child.cget("text"):
                     child.configure(text_color=self.ds.colors.text.secondary)

        if hasattr(self, 'branch_merger_card'):
            self.branch_merger_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            for child in self.branch_merger_card.winfo_children():
                if isinstance(child, ctk.CTkLabel) and "Merge two branches" in child.cget("text"):
                    child.configure(text_color=self.ds.colors.text.secondary)


        # --- Extension Changer View ---
        if hasattr(self, 'extension_tool_card_inner'):
            self.extension_tool_card_inner.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.ai_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.select_folder_btn.configure(fg_color=self.ds.colors.primary, hover_color=self.ds.colors.primary_hover)
            self.ai_apply_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
            if "No folder selected" in self.folder_label.cget("text"):
                self.folder_label.configure(text_color=self.ds.colors.text.secondary)

        # --- Folder Comparator View ---
        if hasattr(self, 'comp_selection_card'):
            self.comp_selection_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.folder_a_label.configure(text_color=self.ds.colors.text.secondary if "Not selected" in self.folder_a_label.cget("text") else self.ds.colors.text.primary)
            self.folder_b_label.configure(text_color=self.ds.colors.text.secondary if "Not selected" in self.folder_b_label.cget("text") else self.ds.colors.text.primary)
            self.compare_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
            
            self.results_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            if self.no_diff_label.winfo_exists() and self.no_diff_label.grid_info():
                if "identical" in self.no_diff_label.cget("text"):
                    self.no_diff_label.configure(text_color=self.ds.colors.success)
                else:
                    self.no_diff_label.configure(text_color=self.ds.colors.text.secondary)
        
        # --- Prompt Manager View ---
        if hasattr(self, 'prompt_list_frame'):
            self.prompt_list_frame.configure(fg_color=self.ds.colors.surface.section)
            for t, btn in self.prompt_widgets.items():
                if t == self.selected_prompt_title:
                    btn.configure(fg_color=self.ds.colors.primary)
                else:
                    btn.configure(fg_color="transparent")
        
        if hasattr(self, 'prompt_title_entry'):
            self.prompt_title_entry.configure(fg_color=self.ds.colors.surface.primary, text_color=self.ds.colors.text.primary)
            
        if hasattr(self, 'prompt_content_text'):
            self.prompt_content_text.configure(fg_color=self.ds.colors.surface.primary, text_color=self.ds.colors.text.primary)

        # --- Project Syncer View ---
        if hasattr(self, 'sync_project_btn'):
            self.sync_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.sync_project_path_label.configure(text_color=self.ds.colors.text.secondary if "Not selected" in self.sync_project_path_label.cget("text") else self.ds.colors.text.primary)
            self.sync_project_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
            
            warning_frame = self.sync_card.grid_slaves(row=4, column=0)[0]
            warning_frame.configure(fg_color=self.ds.colors.surface.section)
            warning_label = warning_frame.winfo_children()[0]
            warning_label.configure(text_color=self.ds.colors.warning)
        
        # --- AI Branch Merger View ---
        if hasattr(self, 'merger_repo_url_entry'):
            repo_card = self.merger_repo_url_entry.master.master
            repo_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)

            options_card = self.merger_priority_selector.master.master
            options_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)

            log_card = self.merger_log_text.master
            log_card.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            
            self.start_merge_btn.configure(fg_color=self.ds.colors.danger, hover_color=self.ds.colors.danger_hover)

    # =============================================================================
    # --- IMAGE RESIZER TOOL ---
    # =============================================================================
    
    def _create_image_resizer_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'Image Resizer' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        # Initialize StringVars and BooleanVars if not already initialized
        if not self.resize_mode_var:
            self.resize_mode_var = ctk.StringVar(value="By Size")
            self.resize_width_var = ctk.StringVar(value="")
            self.resize_height_var = ctk.StringVar(value="")
            self.lock_aspect_ratio_var = ctk.BooleanVar(value=True)
            self.background_fill_var = ctk.BooleanVar(value=False)
            self.bg_color_mode_var = ctk.StringVar(value="color")
            self.bg_color_hex_var = ctk.StringVar(value="#000000")
            self.resize_percentage_var = ctk.DoubleVar(value=100.0)

        # --- Header ---
        header = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        
        SecondaryButton(header, self.ds, text="← Back", command=lambda: self._switch_view(self.tool_selection_frame), width=80).pack(side="left")
        ctk.CTkLabel(header, text="🖼️ Image Resizer", font=self.ds.typography.h1).pack(side="left", padx=self.ds.spacing.l)

        # --- Main Content ---
        scroll_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        scroll_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.s)
        scroll_frame.grid_columnconfigure(0, weight=1)

        # --- Source Image Card ---
        source_card = CardFrame(scroll_frame, self.ds)
        source_card.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        source_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(source_card, text="Source Image", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        source_inner = ctk.CTkFrame(source_card, fg_color="transparent")
        source_inner.grid(row=1, column=0, columnspan=2, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        source_inner.grid_columnconfigure(0, weight=1)

        out_frame = ctk.CTkFrame(source_inner, fg_color="transparent")
        out_frame.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(out_frame, text="Source Image", font=self.ds.typography.body_bold).pack(anchor="w")
        self.image_resizer_source_label = ctk.CTkLabel(out_frame, text="Drag & Drop or Browse...", text_color=self.ds.colors.text.secondary)
        self.image_resizer_source_label.pack(anchor="w")

        btn_frame = ctk.CTkFrame(source_inner, fg_color="transparent")
        btn_frame.pack(side="right")
        SecondaryButton(btn_frame, self.ds, text="Browse...", command=self._browse_source_image).pack()
        
        # Bind Drag and Drop if available natively
        try:
            source_card.drop_target_register(DND_FILES)
            source_card.dnd_bind('<<Drop>>', self._on_image_drop)
            self.image_resizer_source_label.drop_target_register(DND_FILES)
            self.image_resizer_source_label.dnd_bind('<<Drop>>', self._on_image_drop)
        except Exception as e:
            logger.warning(f"Drag and drop setup failed (TkinterDnD might be missing): {e}")

        # --- Image Preview ---
        self.image_preview_label = ctk.CTkLabel(source_card, text="", width=128, height=128)
        self.image_preview_label.grid(row=2, column=0, columnspan=2, pady=self.ds.spacing.m)

        # --- Output Directory Card ---
        output_card = CardFrame(scroll_frame, self.ds)
        output_card.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        output_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(output_card, text="Output Directory", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        self.image_resizer_output_label = ctk.CTkLabel(output_card, text="Same as source (default)", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary)
        self.image_resizer_output_label.grid(row=1, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.s)
        
        SecondaryButton(output_card, self.ds, text="Change...", command=self._browse_output_directory).grid(row=1, column=1, sticky="e", padx=self.ds.spacing.l, pady=self.ds.spacing.s)

        # --- Target Sizes Card ---
        sizes_card = CardFrame(scroll_frame, self.ds)
        sizes_card.grid(row=2, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        sizes_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sizes_card, text="Resize Settings", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        self.resize_mode_segmented = ctk.CTkSegmentedButton(
            sizes_card, 
            values=["By Size", "As Percentage", "Social Media"],
            variable=self.resize_mode_var,
            command=self._on_resize_mode_change
        )
        self.resize_mode_segmented.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)

        # Container for the different modes
        self.resize_mode_container = ctk.CTkFrame(sizes_card, fg_color="transparent")
        self.resize_mode_container.grid(row=2, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))
        self.resize_mode_container.grid_columnconfigure(0, weight=1)

        # --- 1. By Size Frame ---
        self.by_size_frame = ctk.CTkFrame(self.resize_mode_container, fg_color="transparent")
        self.by_size_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Width/Height Inputs
        wh_frame = ctk.CTkFrame(self.by_size_frame, fg_color="transparent")
        wh_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, self.ds.spacing.m))
        wh_frame.grid_columnconfigure((0, 1), weight=1)

        w_frame = ctk.CTkFrame(wh_frame, fg_color="transparent")
        w_frame.grid(row=0, column=0, sticky="ew", padx=(0, self.ds.spacing.s))
        ctk.CTkLabel(w_frame, text="Width", font=self.ds.typography.body_bold).pack(anchor="w")
        self.width_entry = ctk.CTkEntry(w_frame, textvariable=self.resize_width_var, placeholder_text="Enter Width")
        self.width_entry.pack(fill="x", pady=(self.ds.spacing.s, 0))
        self.width_entry.bind("<KeyRelease>", lambda e: self._on_dimension_change("width"))

        h_frame = ctk.CTkFrame(wh_frame, fg_color="transparent")
        h_frame.grid(row=0, column=1, sticky="ew", padx=(self.ds.spacing.s, 0))
        unit_frame = ctk.CTkFrame(h_frame, fg_color="transparent")
        unit_frame.pack(fill="x")
        ctk.CTkLabel(unit_frame, text="Height", font=self.ds.typography.body_bold).pack(side="left")
        ctk.CTkLabel(unit_frame, text="px ▾", font=self.ds.typography.body).pack(side="right")
        self.height_entry = ctk.CTkEntry(h_frame, textvariable=self.resize_height_var, placeholder_text="Enter Height")
        self.height_entry.pack(fill="x", pady=(self.ds.spacing.s, 0))
        self.height_entry.bind("<KeyRelease>", lambda e: self._on_dimension_change("height"))

        # Lock Aspect Ratio
        self.lock_aspect_cb = ctk.CTkCheckBox(self.by_size_frame, text="Lock Aspect Ratio", variable=self.lock_aspect_ratio_var, command=self._on_lock_aspect_ratio_toggle)
        self.lock_aspect_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=(self.ds.spacing.m, self.ds.spacing.m))

        # Background Fill inner frame
        self.bg_fill_frame = ctk.CTkFrame(self.by_size_frame, fg_color="transparent", border_width=1, border_color=self.ds.colors.border, corner_radius=self.ds.spacing.s)
        self.bg_fill_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.bg_fill_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkCheckBox(self.bg_fill_frame, text="Background Fill", variable=self.background_fill_var, command=self._toggle_bg_fill_controls).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        ctk.CTkLabel(self.bg_fill_frame, text="(?)", text_color=self.ds.colors.text.secondary).grid(row=0, column=1, sticky="e", padx=self.ds.spacing.l, pady=self.ds.spacing.m)

        # Color picker options
        self.color_picker_radio = ctk.CTkRadioButton(self.bg_fill_frame, text="Pick a color", variable=self.bg_color_mode_var, value="color")
        self.color_picker_radio.grid(row=1, column=0, sticky="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        
        # Color hex and preview
        color_preview_frame = ctk.CTkFrame(self.bg_fill_frame, fg_color="transparent")
        color_preview_frame.grid(row=1, column=1, sticky="e", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        
        self.bg_hex_entry = ctk.CTkEntry(color_preview_frame, textvariable=self.bg_color_hex_var, width=80)
        self.bg_hex_entry.pack(side="left", padx=(0, self.ds.spacing.s))
        self.bg_hex_entry.bind("<KeyRelease>", self._update_bg_color_preview)

        self.color_preview_box = ctk.CTkFrame(color_preview_frame, width=20, height=20, corner_radius=4, fg_color=self.bg_color_hex_var.get())
        self.color_preview_box.pack(side="left")

        self.transparent_radio = ctk.CTkRadioButton(self.bg_fill_frame, text="Transparent", variable=self.bg_color_mode_var, value="transparent")
        self.transparent_radio.grid(row=2, column=0, sticky="w", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        ctk.CTkLabel(self.bg_fill_frame, text="(?)", text_color=self.ds.colors.text.secondary).grid(row=2, column=1, sticky="e", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))

        self._toggle_bg_fill_controls() # Set initial state

        # --- 2. As Percentage Frame ---
        self.as_percentage_frame = ctk.CTkFrame(self.resize_mode_container, fg_color="transparent")
        self.as_percentage_frame.grid_columnconfigure(0, weight=1)

        slider_frame = ctk.CTkFrame(self.as_percentage_frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=self.ds.spacing.m)
        slider_frame.grid_columnconfigure(0, weight=1)

        self.percent_slider = ctk.CTkSlider(slider_frame, from_=10, to=500, variable=self.resize_percentage_var, command=self._on_percent_slider_change)
        self.percent_slider.grid(row=0, column=0, sticky="ew", padx=(0, self.ds.spacing.m))
        
        self.percent_label = ctk.CTkLabel(slider_frame, text="100%", font=self.ds.typography.body_bold)
        self.percent_label.grid(row=0, column=1)

        self.percent_summary_label = ctk.CTkLabel(self.as_percentage_frame, text="Make my image 100% of original size", text_color=self.ds.colors.text.secondary)
        self.percent_summary_label.pack(anchor="w", pady=(0, self.ds.spacing.m))
        
        # --- 3. Social Media Frame ---
        self.social_media_frame = ctk.CTkFrame(self.resize_mode_container, fg_color="transparent")
        self.social_media_frame.grid_columnconfigure((0, 1), weight=1)

        self.social_media_preset_vars.clear()

        # Chrome Presets
        chrome_label = ctk.CTkLabel(self.social_media_frame, text="Chrome Extension Icons:", font=self.ds.typography.body_bold, text_color=self.ds.colors.text.secondary)
        chrome_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, self.ds.spacing.s))
        chrome_sizes = [16, 32, 48, 128]
        chrome_preset_frame = ctk.CTkFrame(self.social_media_frame, fg_color="transparent")
        chrome_preset_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, self.ds.spacing.m))
        for size in chrome_sizes:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(chrome_preset_frame, text=f"{size}x{size}", variable=var, font=self.ds.typography.body)
            cb.pack(side="left", padx=(0, self.ds.spacing.l))
            self.social_media_preset_vars[f"chrome_{size}"] = var

        # Common Presets
        common_label = ctk.CTkLabel(self.social_media_frame, text="Common Sizes:", font=self.ds.typography.body_bold, text_color=self.ds.colors.text.secondary)
        common_label.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, self.ds.spacing.s))
        common_sizes = [64, 96, 192, 256, 512]
        common_preset_frame = ctk.CTkFrame(self.social_media_frame, fg_color="transparent")
        common_preset_frame.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, self.ds.spacing.m))
        for size in common_sizes:
            var = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(common_preset_frame, text=f"{size}x{size}", variable=var, font=self.ds.typography.body)
            cb.pack(side="left", padx=(0, self.ds.spacing.l))
            self.social_media_preset_vars[f"common_{size}"] = var

        quick_frame = ctk.CTkFrame(self.social_media_frame, fg_color="transparent")
        quick_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(self.ds.spacing.m, 0))
        SecondaryButton(quick_frame, self.ds, text="Select All", command=lambda: self._toggle_all_social(True), width=100).pack(side="left", padx=(0, self.ds.spacing.s))
        SecondaryButton(quick_frame, self.ds, text="Deselect All", command=lambda: self._toggle_all_social(False), width=100).pack(side="left", padx=(0, self.ds.spacing.s))

        # Show initial mode
        self._on_resize_mode_change(self.resize_mode_var.get())

        # --- Action Button ---
        action_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", pady=self.ds.spacing.m)
        
        self.resize_button = SuccessButton(action_frame, self.ds, text="✨ Resize Image", command=self._start_resize_images, height=45)
        self.resize_button.pack(fill="x")

        # --- Status/Results Card ---
        results_card = CardFrame(scroll_frame, self.ds)
        results_card.grid(row=4, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        
        ctk.CTkLabel(results_card, text="Output Log", font=self.ds.typography.h2).pack(anchor="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        
        self.resize_log_text = ctk.CTkTextbox(results_card, height=120, font=self.ds.typography.code, state="disabled")
        self.resize_log_text.pack(fill="x", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))

    def _browse_source_image(self) -> None:
        """Opens a file dialog to select the source image."""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.ico *.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.image_resizer_source_path = file_path
            self.image_resizer_source_label.configure(text=os.path.basename(file_path), text_color=self.ds.colors.text.primary)
            
            # Set default output dir to source directory
            if not self.image_resizer_output_dir:
                self.image_resizer_output_dir = os.path.dirname(file_path)
            
            # Load and display preview, and set initial dimensions
            try:
                img = Image.open(file_path)
                self.resize_width_var.set(str(img.width))
                self.resize_height_var.set(str(img.height))
                # Save original aspect ratio for locking
                self._original_aspect_ratio = img.width / img.height
            except Exception:
                pass
                
            self._update_image_preview(file_path)

    def _on_image_drop(self, event) -> None:
        """Handles a drag-and-drop file insertion."""
        # event.data might contain braces if the path has spaces on Windows
        file_path = event.data.strip('{}')
        if not file_path:
            return
            
        # Verify it looks like an image extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp"]:
             self.image_resizer_source_path = file_path
             self.image_resizer_source_label.configure(text=os.path.basename(file_path), text_color=self.ds.colors.text.primary)
             
             if not self.image_resizer_output_dir:
                 self.image_resizer_output_dir = os.path.dirname(file_path)
             
             try:
                 img = Image.open(file_path)
                 self.resize_width_var.set(str(img.width))
                 self.resize_height_var.set(str(img.height))
                 self._original_aspect_ratio = img.width / img.height
             except Exception:
                 pass
                 
             self._update_image_preview(file_path)

    def _update_image_preview(self, file_path: str) -> None:
        """Updates the preview thumbnail of the selected image."""
        try:
            img = Image.open(file_path)
            img.thumbnail((128, 128), Image.Resampling.LANCZOS)
            
            # Convert to CTkImage for display
            from PIL import ImageTk
            preview_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
            self.image_preview_label.configure(image=preview_img, text="")
            self.image_preview_label._image = preview_img  # Keep reference
        except Exception as e:
            self.image_preview_label.configure(text=f"Preview error: {e}", image=None)

    def _browse_output_directory(self) -> None:
        """Opens a folder dialog to select the output directory."""
        folder_path = filedialog.askdirectory(title="Select Output Directory")
        if folder_path:
            self.image_resizer_output_dir = folder_path
            self.image_resizer_output_label.configure(text=folder_path, text_color=self.ds.colors.text.primary)

    def _update_bg_color_preview(self, event=None) -> None:
        """Validates hex and updates preview box."""
        hex_val = self.bg_color_hex_var.get()
        if len(hex_val) == 7 and hex_val.startswith("#"):
            try:
                self.color_preview_box.configure(fg_color=hex_val)
            except Exception:
                pass

    def _toggle_bg_fill_controls(self) -> None:
        """Enables or disables background fill controls based on checkbox."""
        state = "normal" if self.background_fill_var.get() else "disabled"
        self.color_picker_radio.configure(state=state)
        self.transparent_radio.configure(state=state)
        self.bg_hex_entry.configure(state=state)
        if not self.background_fill_var.get():
             self.color_preview_box.configure(fg_color="transparent")
        else:
             self._update_bg_color_preview()

    def _on_resize_mode_change(self, mode: str) -> None:
        """Switches the UI frame based on the segmented button mode."""
        self.by_size_frame.grid_forget()
        self.as_percentage_frame.grid_forget()
        self.social_media_frame.grid_forget()

        if mode == "By Size":
            self.by_size_frame.grid(row=0, column=0, sticky="nsew")
        elif mode == "As Percentage":
            self.as_percentage_frame.grid(row=0, column=0, sticky="nsew")
        elif mode == "Social Media":
            self.social_media_frame.grid(row=0, column=0, sticky="nsew")

    def _on_percent_slider_change(self, value) -> None:
        """Updates the slider label when moved."""
        int_val = int(value)
        self.percent_label.configure(text=f"{int_val}%")
        self.percent_summary_label.configure(text=f"Make my image {int_val}% of original size")

    def _on_dimension_change(self, changed: str) -> None:
        """Automatically updates the other dimension if aspect ratio is locked."""
        if not self.lock_aspect_ratio_var.get() or not hasattr(self, '_original_aspect_ratio'):
            return
            
        try:
            if changed == "width":
                w = float(self.resize_width_var.get() or 0)
                if w > 0:
                    self.resize_height_var.set(str(int(w / self._original_aspect_ratio)))
            elif changed == "height":
                h = float(self.resize_height_var.get() or 0)
                if h > 0:
                    self.resize_width_var.set(str(int(h * self._original_aspect_ratio)))
        except ValueError:
            pass

    def _on_lock_aspect_ratio_toggle(self) -> None:
        """When turning lock back on, adjust height based on current width."""
        self._on_dimension_change("width")

    def _toggle_all_social(self, select: bool) -> None:
        """Selects or deselects all social media checkboxes."""
        for var in self.social_media_preset_vars.values():
            var.set(select)

    def _log_resize_message(self, message: str) -> None:
        """Appends a message to the resize log."""
        self.resize_log_text.configure(state="normal")
        self.resize_log_text.insert("end", message + "\n")
        self.resize_log_text.see("end")
        self.resize_log_text.configure(state="disabled")

    def _start_resize_images(self) -> None:
        """Starts the image resize operation."""
        if not self.image_resizer_source_path:
            self.app.show_toast("Please select a source image first.", "warning")
            return
        
        mode = self.resize_mode_var.get()
        sizes = []
        width, height, percent = 0, 0, 0
        
        if mode == "Social Media":
            for key, var in self.social_media_preset_vars.items():
                if var.get():
                    size = int(key.split("_")[1])
                    sizes.append(size)
            sizes = sorted(sizes)
            if not sizes:
                self.app.show_toast("Please select at least one social media size.", "warning")
                return
        elif mode == "By Size":
            try:
                width = int(float(self.resize_width_var.get() or 0))
                height = int(float(self.resize_height_var.get() or 0))
                if width <= 0 or height <= 0:
                    raise ValueError
            except ValueError:
                self.app.show_toast("Please enter valid width and height greater than 0.", "warning")
                return
        elif mode == "As Percentage":
            percent = self.resize_percentage_var.get()
            if percent <= 0:
                self.app.show_toast("Percentage must be greater than 0.", "warning")
                return
        
        output_dir = self.image_resizer_output_dir or os.path.dirname(self.image_resizer_source_path)
        
        # Clear log
        self.resize_log_text.configure(state="normal")
        self.resize_log_text.delete("1.0", "end")
        self.resize_log_text.configure(state="disabled")
        
        self.resize_button.configure(state="disabled")
        self.spinner = ButtonSpinner(self.resize_button)
        self.spinner.start()
        
        threading.Thread(
            target=self._run_resize_thread,
            args=(self.image_resizer_source_path, mode, sizes, width, height, percent, output_dir),
            daemon=True
        ).start()

    def _run_resize_thread(self, source_path: str, mode: str, sizes: List[int], target_w: int, target_h: int, percent: float, output_dir: str) -> None:
        """Worker thread for resizing images based on dynamic modes."""
        try:
            img = Image.open(source_path)
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            ext = os.path.splitext(source_path)[1].lower()
            
            # Use PNG for transparency support if original is PNG/ICO or if transparent bg is requested
            output_ext = ext
            if ext in [".png", ".ico", ".gif"]:
                output_ext = ".png"
            elif self.background_fill_var.get() and self.bg_color_mode_var.get() == "transparent":
                output_ext = ".png"
            
            self.app.after(0, self._log_resize_message, f"Original size: {img.width}x{img.height}")
            self.app.after(0, self._log_resize_message, f"Mode: {mode}")
            self.app.after(0, self._log_resize_message, f"Output directory: {output_dir}")
            self.app.after(0, self._log_resize_message, "-" * 40)
            
            success_count = 0
            
            def save_image(resized_img: Image.Image, out_name: str):
                out_path = os.path.join(output_dir, out_name)
                if output_ext == ".ico":
                    resized_img.save(out_path, format="ICO", sizes=[(resized_img.width, resized_img.height)])
                elif output_ext in [".jpg", ".jpeg"]:
                    if resized_img.mode == "RGBA":
                        # If saving as JPEG, blend transparent with white instead of black artifacts
                        bg = Image.new("RGB", resized_img.size, (255, 255, 255))
                        bg.paste(resized_img, mask=resized_img.split()[3]) # 3 is alpha channel
                        resized_img = bg
                    elif resized_img.mode != "RGB":
                        resized_img = resized_img.convert("RGB")
                    resized_img.save(out_path, format="JPEG", quality=95)
                else:
                    resized_img.save(out_path, format="PNG")
                return out_path
                
            if mode == "Social Media":
                for size in sizes:
                    try:
                        resized = img.copy()
                        resized.thumbnail((size, size), Image.Resampling.LANCZOS)
                        
                        if resized.width != size or resized.height != size:
                            canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                            x = (size - resized.width) // 2
                            y = (size - resized.height) // 2
                            if resized.mode != "RGBA":
                                resized = resized.convert("RGBA")
                            canvas.paste(resized, (x, y))
                            resized = canvas
                        
                        out_name = f"{base_name}_{size}x{size}{output_ext}"
                        save_image(resized, out_name)
                        
                        self.app.after(0, self._log_resize_message, f"✓ Created: {out_name}")
                        success_count += 1
                        
                    except Exception as e:
                        self.app.after(0, self._log_resize_message, f"✗ Failed {size}x{size}: {e}")

            elif mode == "By Size":
                try:
                    resized = img.copy()
                    
                    if self.background_fill_var.get() and not self.lock_aspect_ratio_var.get():
                        # Fit inside target_w x target_h, pad the rest
                        resized.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                        
                        bg_color = (0, 0, 0, 0)
                        if self.bg_color_mode_var.get() == "color":
                            hex_val = self.bg_color_hex_var.get().lstrip('#')
                            if len(hex_val) == 6:
                                bg_color = tuple(int(hex_val[i:i+2], 16) + (255,))
                        
                        canvas = Image.new("RGBA", (target_w, target_h), bg_color)
                        x = (target_w - resized.width) // 2
                        y = (target_h - resized.height) // 2
                        if resized.mode != "RGBA":
                            resized = resized.convert("RGBA")
                        canvas.paste(resized, (x, y))
                        resized = canvas
                    else:
                        # Either aspect ratio is locked (so W/H are already proportional),
                        # or it's unlocked with no bg fill (stretch).
                        if self.lock_aspect_ratio_var.get():
                            resized = resized.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        else:
                            # Stretch without background fill
                            resized = resized.resize((target_w, target_h), Image.Resampling.LANCZOS)
                            
                    out_name = f"{base_name}_{target_w}x{target_h}{output_ext}"
                    save_image(resized, out_name)
                    
                    self.app.after(0, self._log_resize_message, f"✓ Created: {out_name}")
                    success_count += 1
                except Exception as e:
                     self.app.after(0, self._log_resize_message, f"✗ Failed By Size {target_w}x{target_h}: {e}")

            elif mode == "As Percentage":
                 try:
                     target_w = max(1, int(img.width * (percent / 100.0)))
                     target_h = max(1, int(img.height * (percent / 100.0)))
                     resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                     
                     out_name = f"{base_name}_{int(percent)}pct_{target_w}x{target_h}{output_ext}"
                     save_image(resized, out_name)
                     
                     self.app.after(0, self._log_resize_message, f"✓ Created: {out_name}")
                     success_count += 1
                 except Exception as e:
                     self.app.after(0, self._log_resize_message, f"✗ Failed Scale {percent}%: {e}")
            
            self.app.after(0, self._log_resize_message, "-" * 40)
            self.app.after(0, self._log_resize_message, f"Done! {success_count} images created.")
            self.app.after(0, self.app.show_toast, f"Resized successfully!", "success")
            
        except Exception as e:
            self.app.after(0, self._log_resize_message, f"Error: {e}")
            self.app.after(0, self.app.show_toast, f"Resize failed: {e}", "error")
        finally:
            self.app.after(0, lambda: self.spinner.stop("normal") if self.spinner else None)

    # =========================================================================
    # Compare Images Tool Methods
    # =========================================================================

    def _create_compare_images_view(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the UI for the 'Compare Images' tool."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        if not self.compare_mode_var:
            self.compare_mode_var = ctk.StringVar(value="Split")
            self.compare_add_text_var = ctk.BooleanVar(value=True)
            self.compare_slider_pos = ctk.DoubleVar(value=0.5)

        # --- Header ---
        header = ctk.CTkFrame(parent_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        ButtonWithHover(header, self.ds, text="← Back to Tools", command=lambda: self._switch_view(self.tool_selection_frame), width=120).pack(side="left")

        # --- Main Layout ---
        main_content = ctk.CTkFrame(parent_frame, fg_color="transparent")
        main_content.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        main_content.grid_columnconfigure(0, weight=1)
        main_content.grid_rowconfigure(2, weight=1) # preview gets remaining space

        # 1. Image Selectors
        selectors_frame = ctk.CTkFrame(main_content, fg_color="transparent")
        selectors_frame.grid(row=0, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        selectors_frame.grid_columnconfigure((0, 1), weight=1, uniform="a")

        # Before Card
        self.img1_card = CardFrame(selectors_frame, self.ds)
        self.img1_card.grid(row=0, column=0, sticky="nsew", padx=(0, self.ds.spacing.s))
        ctk.CTkLabel(self.img1_card, text="Image 1 (Before)", font=self.ds.typography.body_bold).pack(pady=(self.ds.spacing.m, 0))
        self.img1_label = ctk.CTkLabel(self.img1_card, text="Drag & Drop or Browse...", text_color=self.ds.colors.text.secondary)
        self.img1_label.pack(pady=self.ds.spacing.s)
        SecondaryButton(self.img1_card, self.ds, text="Browse...", command=lambda: self._browse_compare_image(1)).pack(pady=(0, self.ds.spacing.m))

        # After Card
        self.img2_card = CardFrame(selectors_frame, self.ds)
        self.img2_card.grid(row=0, column=1, sticky="nsew", padx=(self.ds.spacing.s, 0))
        ctk.CTkLabel(self.img2_card, text="Image 2 (After)", font=self.ds.typography.body_bold).pack(pady=(self.ds.spacing.m, 0))
        self.img2_label = ctk.CTkLabel(self.img2_card, text="Drag & Drop or Browse...", text_color=self.ds.colors.text.secondary)
        self.img2_label.pack(pady=self.ds.spacing.s)
        SecondaryButton(self.img2_card, self.ds, text="Browse...", command=lambda: self._browse_compare_image(2)).pack(pady=(0, self.ds.spacing.m))

        try:
            self.img1_card.drop_target_register(DND_FILES)
            self.img1_card.dnd_bind('<<Drop>>', lambda e: self._on_compare_image_drop(e, 1))
            self.img2_card.drop_target_register(DND_FILES)
            self.img2_card.dnd_bind('<<Drop>>', lambda e: self._on_compare_image_drop(e, 2))
        except Exception:
            logger.warning("TkinterDnD not available for Compare Images")

        # 2. Controls
        controls_frame = ctk.CTkFrame(main_content, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, self.ds.spacing.m))
        ctk.CTkSegmentedButton(
            controls_frame, 
            values=["Split", "Slider"], 
            variable=self.compare_mode_var,
            command=self._on_compare_mode_change
        ).pack(side="left")
        
        self.export_btn = SuccessButton(controls_frame, self.ds, text="Export PNG", command=self._compare_export_png)
        self.export_btn.pack(side="right")
        self.export_text_cb = ctk.CTkCheckBox(controls_frame, text="Add 'Before / After' labels above image", variable=self.compare_add_text_var)
        self.export_text_cb.pack(side="right", padx=self.ds.spacing.l)

        # 3. Preview Area
        self.preview_card = CardFrame(main_content, self.ds)
        self.preview_card.grid(row=2, column=0, sticky="nsew")
        self.preview_card.grid_columnconfigure(0, weight=1)
        self.preview_card.grid_rowconfigure(0, weight=1)
        
        # A canvas to draw the custom slider on, or just a label for split
        self.preview_canvas = ctk.CTkCanvas(self.preview_card, bg=self.ds.colors.surface.base, highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        self.preview_canvas.bind("<Configure>", lambda e: self._schedule_preview_update())
        self.preview_canvas.bind("<B1-Motion>", self._on_compare_slider_drag)
        self.preview_canvas.bind("<Button-1>", self._on_compare_slider_drag)

        self._pending_preview_job = None

    def _browse_compare_image(self, target: int) -> None:
        file_path = filedialog.askopenfilename(title=f"Select Image {target}", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp")])
        if file_path:
            self._load_compare_image(file_path, target)

    def _on_compare_image_drop(self, event, target: int) -> None:
        file_path = event.data.strip('{}')
        if os.path.isfile(file_path):
            self._load_compare_image(file_path, target)

    def _load_compare_image(self, path: str, target: int) -> None:
        try:
            img = Image.open(path)
            if target == 1:
                self.compare_img1_path = path
                self.compare_img1_pil = img
                self.img1_label.configure(text=os.path.basename(path), text_color=self.ds.colors.text.primary)
            else:
                self.compare_img2_path = path
                self.compare_img2_pil = img
                self.img2_label.configure(text=os.path.basename(path), text_color=self.ds.colors.text.primary)
            
            self._update_compare_preview()
        except Exception as e:
            self.app.show_toast(f"Failed to load image: {e}", "error")

    def _on_compare_mode_change(self, mode: str) -> None:
        self._update_compare_preview()

    def _schedule_preview_update(self) -> None:
        if self._pending_preview_job:
            self.app.after_cancel(self._pending_preview_job)
        self._pending_preview_job = self.app.after(50, self._update_compare_preview)

    def _update_compare_preview(self) -> None:
        self.preview_canvas.delete("all")
        if not self.compare_img1_pil and not self.compare_img2_pil:
            self.preview_canvas.create_text(
                self.preview_canvas.winfo_width() / 2, 
                self.preview_canvas.winfo_height() / 2, 
                text="Load two images to see preview.", 
                fill=self.ds.colors.text.secondary, font=("Inter", 14)
            )
            return

        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        if w <= 1 or h <= 1:
            return

        if self.compare_mode_var.get() == "Split":
            self._draw_split_preview(w, h)
        else:
            self._draw_slider_preview(w, h)

    def _draw_split_preview(self, w: int, h: int) -> None:
        """Draws two images side by side scaled to fit the canvas."""
        half_w = w // 2
        
        def render_half(img, x_offset):
            if not img: return
            
            # Scale to fit half screen
            ratio = min(half_w / img.width, h / img.height)
            new_size = (max(1, int(img.width * ratio)), max(1, int(img.height * ratio)))
            resized = img.copy()
            resized.thumbnail(new_size, Image.Resampling.LANCZOS)
            
            from PIL import ImageTk
            tk_img = ImageTk.PhotoImage(resized)
            
            center_x = x_offset + (half_w // 2)
            center_y = h // 2
            
            idx = self.preview_canvas.create_image(center_x, center_y, anchor="center", image=tk_img)
            # Keep reference
            if not hasattr(self, '_preview_refs'): self._preview_refs = []
            self._preview_refs.append(tk_img)

        self._preview_refs = []
        render_half(self.compare_img1_pil, 0)
        
        # Add a visual divider
        self.preview_canvas.create_line(half_w, 0, half_w, h, fill=self.ds.colors.border, width=2)
        
        render_half(self.compare_img2_pil, half_w)

    def _draw_slider_preview(self, w: int, h: int) -> None:
        """Overlays images with a draggable slider."""
        if not self.compare_img1_pil or not self.compare_img2_pil:
            self.preview_canvas.create_text(w/2, h/2, text="Both images required for Slider mode.", fill=self.ds.colors.text.secondary)
            return

        # Ensure we scale both images to exact same fitted dimension to avoid disjointed overlap
        img1 = self.compare_img1_pil
        img2 = self.compare_img2_pil
        
        # Just use img1's size ratio to fit the canvas
        ratio = min(w / img1.width, h / img1.height)
        fit_w, fit_h = max(1, int(img1.width * ratio)), max(1, int(img1.height * ratio))
        
        r1 = img1.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
        r2 = img2.resize((fit_w, fit_h), Image.Resampling.LANCZOS)

        slider_x = int(fit_w * self.compare_slider_pos.get())
        
        # Base canvas is background (Image 2)
        from PIL import ImageTk
        
        self._preview_refs = []
        
        # Draw background (Right Image)
        tk_img2 = ImageTk.PhotoImage(r2)
        center_x, center_y = w // 2, h // 2
        img_start_x = center_x - (fit_w // 2)
        img_start_y = center_y - (fit_h // 2)
        
        self.preview_canvas.create_image(img_start_x, img_start_y, anchor="nw", image=tk_img2)
        self._preview_refs.append(tk_img2)
        
        # Crop foreground (Left Image) to slider
        if slider_x > 0:
            crop1 = r1.crop((0, 0, slider_x, fit_h))
            tk_img1 = ImageTk.PhotoImage(crop1)
            self.preview_canvas.create_image(img_start_x, img_start_y, anchor="nw", image=tk_img1)
            self._preview_refs.append(tk_img1)
            
        # Draw slider line
        abs_slider_x = img_start_x + slider_x
        self.preview_canvas.create_line(abs_slider_x, img_start_y, abs_slider_x, img_start_y + fit_h, fill="#FFFFFF", width=3)
        # Thumb
        self.preview_canvas.create_oval(abs_slider_x-10, center_y-10, abs_slider_x+10, center_y+10, fill="#FFFFFF", outline="#000000")
        self.preview_canvas.create_line(abs_slider_x-4, center_y-4, abs_slider_x-4, center_y+4, fill="#000000")
        self.preview_canvas.create_line(abs_slider_x+4, center_y-4, abs_slider_x+4, center_y+4, fill="#000000")

    def _on_compare_slider_drag(self, event) -> None:
        """Handles slider drag logic."""
        if self.compare_mode_var.get() != "Slider" or not self.compare_img1_pil:
             return
             
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        
        img1 = self.compare_img1_pil
        ratio = min(w / img1.width, h / img1.height)
        fit_w = int(img1.width * ratio)
        
        img_start_x = (w - fit_w) // 2
        
        # Calculate local pos
        local_x = event.x - img_start_x
        pos = max(0.0, min(1.0, local_x / fit_w))
        
        self.compare_slider_pos.set(pos)
        self._update_compare_preview()

    def _compare_export_png(self) -> None:
        """Exports the split view as a wide PNG with optional text labels."""
        if not self.compare_img1_pil or not self.compare_img2_pil:
             self.app.show_toast("Please load both images to export.", "warning")
             return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".png", 
            filetypes=[("PNG file", "*.png")],
            title="Export Comparison"
        )
        if not out_path:
             return

        try:
            # We will scale the second image to match the height of the first one if necessary
            img1 = self.compare_img1_pil
            img2 = self.compare_img2_pil
            
            if img1.height != img2.height:
                ratio = img1.height / img2.height
                new_w = int(img2.width * ratio)
                img2 = img2.resize((new_w, img1.height), Image.Resampling.LANCZOS)
                
            padding_top = 0
            if self.compare_add_text_var.get():
                padding_top = 80 # Space for text

            total_w = img1.width + img2.width
            total_h = img1.height + padding_top
            
            # Base Canvas
            canvas = Image.new("RGBA", (total_w, total_h), (30, 30, 30, 255))
            
            if self.compare_add_text_var.get():
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(canvas)
                try:
                    # Attempt to load a default font
                    font = ImageFont.truetype("arial.ttf", 40)
                except IOError:
                    font = ImageFont.load_default()
                    
                # Centers
                w1_c = img1.width // 2
                w2_c = img1.width + (img2.width // 2)
                
                # Pillow drawing fallback
                try:
                    draw.text((w1_c, 40), "Before : ", fill="white", font=font, anchor="mm")
                    draw.text((w2_c, 40), " After : ", fill="white", font=font, anchor="mm")
                except Exception:
                    # Fallback if anchor is not supported on old Pillow versions
                    draw.text((10, 10), "Before : ", fill="white")
                    draw.text((img1.width + 10, 10), " After : ", fill="white")
            
            # Paste images
            canvas.paste(img1, (0, padding_top))
            canvas.paste(img2, (img1.width, padding_top))
            
            canvas.save(out_path, format="PNG")
            self.app.show_toast(f"Exported to {os.path.basename(out_path)} successfully!", "success")
        except Exception as e:
            self.app.show_toast(f"Export failed: {e}", "error")

