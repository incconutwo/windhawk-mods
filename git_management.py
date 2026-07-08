import customtkinter as ctk
from tkinter import filedialog
import os
import threading
import shutil
import time
import traceback
import logging
from collections import deque
from typing import Optional, Any, Deque, Dict, List, Callable
from design_system import DS, CardFrame, ButtonWithHover, SuccessButton, DangerButton, SecondaryButton, WarningButton, GhostButton
from base_controller import BaseController
from ui_components import ConfirmationDialog, ButtonSpinner, SearchableComboBox

class GitTabsController(BaseController):
    """
    Manages the UI and logic for the consolidated 'GitHub GUI' tab.
    
    This controller implements a modern, single-tab interface for all Git-related
    functionalities. It contains four distinct views (Push, Sync, History, Delete) that
    are managed internally.
    """
    def __init__(self, app: 'CodeMergerApp', app_state: 'AppState', gemini_handler: 'GeminiHandler', github_handler: 'GitHubHandler', ds: DS):
        """
        Initializes the GitTabsController.
        """
        super().__init__(app)
        self.app_state = app_state
        self.gemini_handler = gemini_handler
        self.github_handler = github_handler
        self.ds = ds
        
        self.new_project_local_path: Optional[str] = None
        self.merge_queue: Deque[Dict[str, str]] = deque()
        self.current_view: Optional[ctk.CTkFrame] = None
        
        # Delete view state
        self.delete_file_checkboxes: Dict[str, ctk.CTkCheckBox] = {}

    def create_source_control_tab(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the consolidated 'GitHub GUI' tab with its internal view-switching mechanism."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(1, weight=1)

        nav_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        nav_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(self.ds.spacing.m, 0))
        nav_frame.grid_columnconfigure((0, 2), weight=1)
        
        self.segmented_button = ctk.CTkSegmentedButton(
            nav_frame, values=["Push", "Sync", "History", "Delete"],
            command=self._switch_view, font=self.ds.typography.button
        )
        self.segmented_button.grid(row=0, column=1, sticky="")

        self.views_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        self.views_container.grid(row=1, column=0, sticky="nsew")
        self.views_container.grid_columnconfigure(0, weight=1)
        self.views_container.grid_rowconfigure(0, weight=1)
        self.push_view_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.sync_view_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.history_view_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")
        self.delete_view_frame = ctk.CTkFrame(self.views_container, fg_color="transparent")

        self.push_view_frame.grid(row=0, column=0, sticky="nsew")
        self.sync_view_frame.grid(row=0, column=0, sticky="nsew")
        self.history_view_frame.grid(row=0, column=0, sticky="nsew")
        self.delete_view_frame.grid(row=0, column=0, sticky="nsew")

        # Track loaded states
        self._views_loaded = {
            "Push": False,
            "Sync": False,
            "History": False,
            "Delete": False
        }

        self.segmented_button.set("Push")
        self._switch_view("Push", is_initial_load=True)

    def _switch_view(self, view_name: str, is_initial_load: bool = False) -> None:
        """Handles switching between views with lazy loading."""
        view_map = {
            "Push": (self.push_view_frame, self._create_github_tab),
            "Sync": (self.sync_view_frame, self._create_sync_tab),
            "History": (self.history_view_frame, self._create_history_tab),
            "Delete": (self.delete_view_frame, self._create_delete_tab)
        }
        
        if view_name not in view_map:
            return
            
        target_view, creator_func = view_map[view_name]

        if target_view == self.current_view and not is_initial_load:
            return

        # Lazy load the content if not already created
        if not self._views_loaded.get(view_name, False):
            self.app.update_status(f"Loading {view_name} view...")
            self.app.update_idletasks() # Show immediate feedback
            creator_func(target_view)
            self._views_loaded[view_name] = True
            
            if not is_initial_load:
                self.app.update_status("Ready")

        target_view.lift()
        self.current_view = target_view
        
    def fetch_all_repos_background(self) -> None:
        """Fetches all repositories the user has access to in the background, updating caches and UI dropdowns."""
        token = self.app_state.settings_manager.get_github_token()
        if not token:
            return
            
        def worker():
            try:
                repos = self.github_handler.get_user_repos(token)
                if repos:
                    self.app_state.github_repos = repos
                    self.app_state.settings_manager.set('cached_github_repos', repos)
                    self.app.after(0, self._update_all_repo_menus, repos, False)
            except Exception as e:
                logging.error(f"Background repo fetch failed: {e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def get_branches_cached_or_refresh(self, repo_url: str, menu_widgets: List[ctk.CTkComboBox], custom_callback: Optional[Callable[[List[str]], None]] = None) -> None:
        """
        Retrieves branches for the given repo_url.
        If cached, populates the menus immediately.
        Refreshes from GitHub in the background and updates the menus/cache.
        """
        if not repo_url:
            return

        # 1. Check cache and populate immediately
        cached_branches = self.app_state.github_branches.get(repo_url)
        if cached_branches:
            for menu in menu_widgets:
                self._update_branch_menu(cached_branches, menu)
            if custom_callback:
                custom_callback(cached_branches)

        # 2. Refresh in the background
        token = self.app_state.settings_manager.get_github_token()
        if not token:
            return

        def worker():
            try:
                branches = self.github_handler.get_branches(token, repo_url)
                if branches:
                    # Save to cache
                    self.app_state.github_branches[repo_url] = branches
                    self.app_state.settings_manager.set('cached_github_branches', self.app_state.github_branches)
                    
                    # Update menus on main thread
                    def update_ui():
                        for menu in menu_widgets:
                            self._update_branch_menu(branches, menu)
                        if custom_callback:
                            custom_callback(branches)
                    self.app.after(0, update_ui)
            except Exception as e:
                logging.error(f"Background branch fetch failed for {repo_url}: {e}")
                
        threading.Thread(target=worker, daemon=True).start()

    def _update_all_repo_menus(self, repos: list, show_toast: bool = True) -> None:
        """Updates all comboboxes across the app with the new repos list."""
        self.app_state.github_repos = repos
        
        # Helper to update a single menu safely
        def safe_update_menu(menu_widget):
            if hasattr(self, menu_widget):
                widget = getattr(self, menu_widget)
                if isinstance(widget, SearchableComboBox):
                    current_val = widget.get()
                    widget.configure(values=repos if repos else [""])
                    if current_val in repos:
                        widget.set(current_val)
                    elif repos:
                        widget.set(repos[0])

        safe_update_menu("repo_entry")
        safe_update_menu("sync_repo_entry")
        safe_update_menu("delete_repo_entry")
        safe_update_menu("history_repo_entry")
        
        # Tools menus are on the tools controller, so we access them cleanly
        if hasattr(self.app, 'tools_controller'):
            if hasattr(self.app.tools_controller, 'sync_repo_url_entry') and isinstance(self.app.tools_controller.sync_repo_url_entry, SearchableComboBox):
                current_val = self.app.tools_controller.sync_repo_url_entry.get()
                self.app.tools_controller.sync_repo_url_entry.configure(values=repos if repos else [""])
                if current_val in repos: self.app.tools_controller.sync_repo_url_entry.set(current_val)
                elif repos: self.app.tools_controller.sync_repo_url_entry.set(repos[0])
                
            if hasattr(self.app.tools_controller, 'merger_repo_url_entry') and isinstance(self.app.tools_controller.merger_repo_url_entry, SearchableComboBox):
                current_val = self.app.tools_controller.merger_repo_url_entry.get()
                self.app.tools_controller.merger_repo_url_entry.configure(values=repos if repos else [""])
                if current_val in repos: self.app.tools_controller.merger_repo_url_entry.set(current_val)
                elif repos: self.app.tools_controller.merger_repo_url_entry.set(repos[0])
                
        if show_toast:
            self.app.show_toast(f"Fetched {len(repos)} repositories.", "success")

    def _on_push_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the Push tab."""
        self.app_state.settings_manager.set('github_repo_url', repo_url)
        self.get_branches_cached_or_refresh(repo_url, [self.branch_menu])

    def _on_sync_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the Sync tab."""
        self.get_branches_cached_or_refresh(repo_url, [self.sync_branch_menu])

    def _on_history_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the History tab."""
        self.get_branches_cached_or_refresh(repo_url, [self.history_branch_menu])

    def _on_delete_repo_change(self, repo_url: str) -> None:
        """Called when repository URL changes in the Delete tab."""
        self.get_branches_cached_or_refresh(repo_url, [self.delete_branch_menu])

    def _create_github_tab(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the content for the 'GitHub Push' view."""
        parent_frame.grid_columnconfigure(0, weight=1); parent_frame.grid_rowconfigure(2, weight=1)
        
        self.push_config_frame = CardFrame(parent_frame, self.ds)
        self.push_config_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        self.push_config_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.push_config_frame, text="Repository Settings", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0), sticky="w")
        ctk.CTkLabel(self.push_config_frame, text="Repository:", font=self.ds.typography.body).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.repo_entry = SearchableComboBox(self.push_config_frame, values=self.app_state.github_repos if self.app_state.github_repos else [""])
        self.repo_entry.grid(row=1, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        self.repo_entry.configure(command=self._on_push_repo_change)
        
        initial_repo = self.app_state.settings_manager.get('github_repo_url') or ""
        self.repo_entry.set(initial_repo)
        
        ctk.CTkLabel(self.push_config_frame, text="Branch:", font=self.ds.typography.body).grid(row=2, column=0, padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="w")
        self.branch_menu = ctk.CTkComboBox(self.push_config_frame, values=[self.app_state.settings_manager.get('github_branch', 'main')])
        self.branch_menu.grid(row=2, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")
        self.branch_menu.set(self.app_state.settings_manager.get('github_branch', 'main'))

        if initial_repo:
            self.get_branches_cached_or_refresh(initial_repo, [self.branch_menu])

        self.push_staged_frame = CardFrame(parent_frame, self.ds)
        self.push_staged_frame.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self.push_staged_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.push_staged_frame, text="Staged Files", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0))
        self.staged_files_text = ctk.CTkTextbox(self.push_staged_frame, height=120, font=self.ds.typography.code)
        self.staged_files_text.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m))
        self.update_staged_files_ui()
        
        self.push_commit_frame = CardFrame(parent_frame, self.ds)
        self.push_commit_frame.grid(row=2, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self.push_commit_frame.grid_rowconfigure(1, weight=1); self.push_commit_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.push_commit_frame, text="Commit Message", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0))
        self.commit_message_text = ctk.CTkTextbox(self.push_commit_frame, font=self.ds.typography.body, wrap="word", height=80)
        self.commit_message_text.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m))
        self.commit_message_text.insert("1.0", "feat: Update files via Gemini Assistant")
        
        self.push_btn = SuccessButton(parent_frame, self.ds, text="🚀 Push to GitHub", command=self.start_push_thread, height=45)
        self.push_btn.grid(row=3, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))

    def _create_sync_tab(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the content for the 'Local Sync' view."""
        parent_frame.grid_columnconfigure(0, weight=1); parent_frame.grid_rowconfigure(1, weight=1)

        self.sync_add_project_frame = CardFrame(parent_frame, self.ds)
        self.sync_add_project_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        self.sync_add_project_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.sync_add_project_frame, text="Add New Project", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=3, padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s), sticky="w")
        
        folder_frame = ctk.CTkFrame(self.sync_add_project_frame, fg_color="transparent")
        folder_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=self.ds.spacing.l, pady=self.ds.spacing.s); folder_frame.grid_columnconfigure(1, weight=1)
        self.sync_select_folder_btn = SecondaryButton(folder_frame, self.ds, text="Select Local Folder", command=self._select_sync_folder, width=150)
        self.sync_select_folder_btn.grid(row=0, column=0, sticky="w")
        self.new_project_path_label = ctk.CTkLabel(folder_frame, text="No folder selected", text_color=self.ds.colors.text.secondary, anchor="w")
        self.new_project_path_label.grid(row=0, column=1, padx=self.ds.spacing.m, sticky="ew")
        
        ctk.CTkLabel(self.sync_add_project_frame, text="GitHub Repo:").grid(row=2, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.sync_repo_entry = SearchableComboBox(self.sync_add_project_frame, values=self.app_state.github_repos if self.app_state.github_repos else [""])
        self.sync_repo_entry.grid(row=2, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        self.sync_repo_entry.configure(command=self._on_sync_repo_change)
        
        ctk.CTkLabel(self.sync_add_project_frame, text="Branch:").grid(row=3, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.sync_branch_menu = ctk.CTkComboBox(self.sync_add_project_frame, values=["main"])
        self.sync_branch_menu.grid(row=3, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        
        initial_repo = self.sync_repo_entry.get().strip()
        if initial_repo:
            self.get_branches_cached_or_refresh(initial_repo, [self.sync_branch_menu])
        
        self.sync_save_project_btn = SuccessButton(self.sync_add_project_frame, self.ds, text="💾 Save Project", command=self._save_sync_project, height=35)
        self.sync_save_project_btn.grid(row=4, column=0, columnspan=3, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, self.ds.spacing.l), sticky="ew")

        self.sync_saved_projects_container = CardFrame(parent_frame, self.ds)
        self.sync_saved_projects_container.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self.sync_saved_projects_container.grid_columnconfigure(0, weight=1); self.sync_saved_projects_container.grid_rowconfigure(1, weight=1)
        
        saved_header = ctk.CTkFrame(self.sync_saved_projects_container, fg_color="transparent")
        saved_header.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, 0))
        ctk.CTkLabel(saved_header, text="Saved Projects", font=self.ds.typography.h2).pack(side="left")
        self.restore_backup_btn = GhostButton(saved_header, self.ds, text="↩ Restore Backup", width=120, command=self._restore_last_backup, state="disabled")
        self.restore_backup_btn.pack(side="right")

        self.saved_projects_frame = ctk.CTkScrollableFrame(self.sync_saved_projects_container, fg_color="transparent")
        self.saved_projects_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.s, pady=self.ds.spacing.s)
        self._populate_saved_projects()
        self._check_backup_status()

    def _create_history_tab(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the content for the 'Git History' view."""
        parent_frame.grid_columnconfigure(0, weight=1); parent_frame.grid_rowconfigure(1, weight=1)

        self.history_controls_frame = CardFrame(parent_frame, self.ds)
        self.history_controls_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        self.history_controls_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.history_controls_frame, text="Repository:", font=self.ds.typography.body).grid(row=0, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.history_repo_entry = SearchableComboBox(self.history_controls_frame, values=self.app_state.github_repos if self.app_state.github_repos else [""])
        self.history_repo_entry.grid(row=0, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        self.history_repo_entry.configure(command=self._on_history_repo_change)
        initial_repo = self.app_state.settings_manager.get('github_repo_url') or ""
        self.history_repo_entry.set(initial_repo)
        
        ctk.CTkLabel(self.history_controls_frame, text="Branch:", font=self.ds.typography.body).grid(row=1, column=0, padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="w")
        self.history_branch_menu = ctk.CTkComboBox(self.history_controls_frame, values=[self.app_state.settings_manager.get('github_branch', 'main')])
        self.history_branch_menu.grid(row=1, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")
        self.history_branch_menu.set(self.app_state.settings_manager.get('github_branch', 'main'))

        if initial_repo:
            self.get_branches_cached_or_refresh(initial_repo, [self.history_branch_menu])

        # Container for the fetch history button to span neatly
        btn_container = ctk.CTkFrame(self.history_controls_frame, fg_color="transparent")
        btn_container.grid(row=2, column=0, columnspan=3, pady=(0, self.ds.spacing.m), sticky="ew")
        
        self.fetch_history_btn = ButtonWithHover(btn_container, self.ds, text="Fetch Commit History", command=self._start_fetch_history_thread)
        self.fetch_history_btn.pack(pady=self.ds.spacing.s)
        
        self.commit_history_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        self.commit_history_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self._show_history_empty_state()
        
        self.history_warning_frame = CardFrame(parent_frame, self.ds, border_color=self.ds.colors.warning)
        self.history_warning_frame.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        ctk.CTkLabel(self.history_warning_frame, text="⚠️ WARNING: Reverting to a commit is a destructive action that will permanently overwrite the remote branch history. This cannot be undone.", wraplength=800).pack(padx=self.ds.spacing.m, pady=self.ds.spacing.m)

    def _create_delete_tab(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the content for the 'Delete Files' view."""
        parent_frame.grid_columnconfigure(0, weight=1)
        parent_frame.grid_rowconfigure(2, weight=1)

        # Config Frame (Repo/Branch/Fetch)
        self.delete_config_frame = CardFrame(parent_frame, self.ds)
        self.delete_config_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        self.delete_config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.delete_config_frame, text="Delete Files from Repository", font=self.ds.typography.h2).grid(row=0, column=0, columnspan=2, padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0), sticky="w")
        
        ctk.CTkLabel(self.delete_config_frame, text="Repository:", font=self.ds.typography.body).grid(row=1, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.s, sticky="w")
        self.delete_repo_entry = SearchableComboBox(self.delete_config_frame, values=self.app_state.github_repos if self.app_state.github_repos else [""])
        self.delete_repo_entry.grid(row=1, column=1, columnspan=2, padx=(0, self.ds.spacing.l), pady=self.ds.spacing.s, sticky="ew")
        self.delete_repo_entry.configure(command=self._on_delete_repo_change)
        initial_repo = self.app_state.settings_manager.get('github_repo_url') or ""
        self.delete_repo_entry.set(initial_repo)
        
        ctk.CTkLabel(self.delete_config_frame, text="Branch:", font=self.ds.typography.body).grid(row=2, column=0, padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="w")
        self.delete_branch_menu = ctk.CTkComboBox(self.delete_config_frame, values=[self.app_state.settings_manager.get('github_branch', 'main')])
        self.delete_branch_menu.grid(row=2, column=1, padx=0, pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")
        self.delete_branch_menu.set(self.app_state.settings_manager.get('github_branch', 'main'))

        if initial_repo:
            self.get_branches_cached_or_refresh(initial_repo, [self.delete_branch_menu])

        self.delete_fetch_btn = SecondaryButton(self.delete_config_frame, self.ds, text="Load File List", command=self._fetch_files_for_deletion)
        self.delete_fetch_btn.grid(row=2, column=2, padx=(self.ds.spacing.m, self.ds.spacing.l), pady=(self.ds.spacing.s, self.ds.spacing.m), sticky="ew")

        # File List Frame
        self.delete_list_container = CardFrame(parent_frame, self.ds)
        self.delete_list_container.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self.delete_list_container.grid_columnconfigure(0, weight=1); self.delete_list_container.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.delete_list_container, text="Select Files to Delete", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0))
        
        self.delete_file_scroll = ctk.CTkScrollableFrame(self.delete_list_container, fg_color="transparent")
        self.delete_file_scroll.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.s)
        
        ctk.CTkLabel(self.delete_file_scroll, text="Click 'Load File List' to see files.", text_color=self.ds.colors.text.secondary).pack(pady=20)

        # Commit Frame
        self.delete_commit_frame = CardFrame(parent_frame, self.ds)
        self.delete_commit_frame.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))
        self.delete_commit_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.delete_commit_frame, text="Commit Message", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.m, 0))
        self.delete_commit_msg = ctk.CTkTextbox(self.delete_commit_frame, height=60, font=self.ds.typography.body, wrap="word")
        self.delete_commit_msg.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(self.ds.spacing.s, self.ds.spacing.m))
        self.delete_commit_msg.insert("1.0", "chore: Delete obsolete files")

        self.delete_btn = DangerButton(parent_frame, self.ds, text="🗑️ Delete Selected Files", command=self._start_delete_files_thread, height=45)
        self.delete_btn.grid(row=3, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.m))

    def _fetch_files_for_deletion(self) -> None:
        """Starts fetching the remote file list for deletion."""
        token = self.app_state.settings_manager.get_github_token()
        repo = self.delete_repo_entry.get().strip()
        branch = self.delete_branch_menu.get().strip()

        if not token or not repo or not branch:
            self.app.show_toast("Token, Repo URL, and Branch are required.", "warning")
            return

        spinner = ButtonSpinner(self.delete_fetch_btn)
        spinner.start()
        threading.Thread(target=self._run_fetch_files_for_deletion_threaded, args=(token, repo, branch, spinner), daemon=True).start()

    def _run_fetch_files_for_deletion_threaded(self, token: str, repo: str, branch: str, spinner: ButtonSpinner) -> None:
        """Worker thread that calls the GitHub handler to get remote file list."""
        try:
            files = self.github_handler.get_remote_tree_structure(token, repo, branch)
            self.app.after(0, self._populate_delete_list, files)
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"Error loading files: {e}", "error")
            logging.error(traceback.format_exc())
        finally:
            self.app.after(0, spinner.stop)

    def _populate_delete_list(self, files: List[str]) -> None:
        """Populates the checkbox list with remote files."""
        for widget in self.delete_file_scroll.winfo_children(): widget.destroy()
        self.delete_file_checkboxes.clear()

        if not files:
            ctk.CTkLabel(self.delete_file_scroll, text="No files found in this branch.", text_color=self.ds.colors.text.secondary).pack(pady=20)
            return

        for f in sorted(files):
            cb = ctk.CTkCheckBox(self.delete_file_scroll, text=f)
            cb.pack(anchor="w", padx=self.ds.spacing.m, pady=2)
            self.delete_file_checkboxes[f] = cb
    
    def _start_delete_files_thread(self) -> None:
        """Collects selected files and starts the deletion process."""
        token = self.app_state.settings_manager.get_github_token()
        repo = self.delete_repo_entry.get().strip()
        branch = self.delete_branch_menu.get().strip()
        msg = self.delete_commit_msg.get("1.0", "end-1c").strip()
        
        selected_files = [f for f, cb in self.delete_file_checkboxes.items() if cb.get() == 1]

        if not all([token, repo, branch, msg]):
            self.app.show_toast("All fields (Token, Repo, Branch, Message) are required.", "warning"); return
        
        if not selected_files:
            self.app.show_toast("No files selected for deletion.", "warning"); return

        ConfirmationDialog(
            self.app, self.ds, "Confirm Deletion",
            f"Are you sure you want to permanently delete {len(selected_files)} file(s) from '{branch}'?\n\nThis will create a new commit removing them.",
            lambda: self._execute_delete_thread(token, repo, branch, selected_files, msg)
        )

    def _execute_delete_thread(self, token: str, repo: str, branch: str, files: List[str], msg: str) -> None:
        """Starts the deletion worker thread."""
        self.delete_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_delete_files_threaded, args=(token, repo, branch, files, msg), daemon=True).start()

    def _run_delete_files_threaded(self, token: str, repo: str, branch: str, files: List[str], msg: str) -> None:
        """Worker thread that executes file deletion via GitHub handler."""
        try:
            success = self.github_handler.delete_files_from_repo(token, repo, branch, files, msg)
            if success:
                remaining_files = self.github_handler.get_remote_tree_structure(token, repo, branch)
                self.app.after(0, self._populate_delete_list, remaining_files)
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"Deletion failed: {e}", "error")
            logging.error(traceback.format_exc())
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.delete_btn.configure(state="normal"))

    def update_staged_files_ui(self) -> None:
        """Refreshes the text box displaying the list of staged files."""
        self.staged_files_text.configure(state="normal")
        self.staged_files_text.delete("1.0", "end")
        
        if not self.app_state.opened_folder_path:
            self.staged_files_text.insert("1.0", "Open a folder from the File Explorer to begin staging files for a commit.")
        elif not self.app_state.staged_github_files:
            self.staged_files_text.insert("1.0", "No files staged. Select files from the explorer and click 'Stage' to add them.")
        else:
            paths = [os.path.relpath(p, self.app_state.opened_folder_path).replace("\\", "/") for p in sorted(list(self.app_state.staged_github_files))]
            self.staged_files_text.insert("1.0", "\n".join(paths))
        self.staged_files_text.configure(state="disabled")

    def start_push_thread(self) -> None:
        """Validates inputs and shows a confirmation dialog before pushing to GitHub."""
        token = self.app_state.settings_manager.get_github_token()
        repo_url = self.repo_entry.get().strip()
        branch = self.branch_menu.get().strip()
        commit_msg = self.commit_message_text.get("1.0", "end-1c").strip()
        staged_files = self.app_state.staged_github_files
        opened_folder = self.app_state.opened_folder_path

        if not all([token, repo_url, branch, commit_msg, staged_files, opened_folder]):
            self.app.show_toast("Repo, Branch, Message, Token, Opened Folder & Staged Files required.", "error")
            return

        # Prepare confirmation message
        relative_paths = [os.path.relpath(p, opened_folder).replace("\\", "/") for p in sorted(list(staged_files))]
        files_str = "\n".join(f"- {p}" for p in relative_paths)
        
        confirmation_message = (
            f"You are about to push to:\n\nRepository: {repo_url}\nBranch: {branch}\n\n"
            f"Commit Message:\n\"{commit_msg}\"\n\nFiles ({len(relative_paths)}):\n{files_str}"
        )

        # Show confirmation dialog
        ConfirmationDialog(
            master=self.app,
            ds=self.ds,
            title="Confirm GitHub Push",
            message=confirmation_message,
            confirm_callback=lambda: self._execute_push(token, repo_url, branch, commit_msg)
        )

    def _execute_push(self, token: str, repo_url: str, branch: str, commit_msg: str) -> None:
        """Starts the GitHub push process in a new thread after confirmation."""
        self.app_state.settings_manager.set('github_repo_url', repo_url)
        self.app_state.settings_manager.set('github_branch', branch)
        self.push_btn.configure(state="disabled")
        self._start_long_process()
        threading.Thread(target=self._run_github_push_threaded, args=(token, repo_url, branch, commit_msg), daemon=True).start()

    def _run_github_push_threaded(self, token: str, repo_url: str, branch: str, commit_msg: str) -> None:
        """Worker thread that calls the GitHub handler to push files."""
        try:
            success = self.github_handler.run_github_push(token, repo_url, branch, commit_msg, self.app_state.staged_github_files, self.app_state.opened_folder_path)
            if success and self.app.sidebar_controller:
                self.app.after(0, self.app.sidebar_controller.clear_staged_files)
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"GitHub Push Failed: {e}", "error")
            logging.error(traceback.format_exc())
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.push_btn.configure(state="normal"))
            
    def _fetch_branches_for_history(self) -> None:
        """Starts a thread to fetch branches for the repository in the history tab."""
        token = self.app_state.settings_manager.get_github_token()
        repo_url = self.history_repo_entry.get().strip()
        if not token or not repo_url:
            self.app.show_toast("GitHub Token and Repo URL required.", "warning")
            return
        
        spinner = ButtonSpinner(self.history_fetch_branches_btn)
        spinner.start()
        threading.Thread(target=self._run_fetch_branches_threaded, args=(token, repo_url, self.history_branch_menu, spinner), daemon=True).start()

    def _fetch_branches_for_push(self) -> None:
        """Starts a thread to fetch branches for the repository in the push tab."""
        token = self.app_state.settings_manager.get_github_token()
        repo_url = self.repo_entry.get().strip()
        if not token or not repo_url:
            self.app.show_toast("GitHub Token and Repo URL required.", "warning")
            return
        
        spinner = ButtonSpinner(self.push_fetch_branches_btn)
        spinner.start()
        threading.Thread(target=self._run_fetch_branches_threaded, args=(token, repo_url, self.branch_menu, spinner), daemon=True).start()

    def _select_sync_folder(self) -> None:
        """Opens a directory dialog for selecting a new sync project folder."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.new_project_local_path = folder_path
            self.new_project_path_label.configure(text=folder_path, text_color=self.ds.colors.text.primary)

    def _fetch_branches_for_sync(self) -> None:
        """Starts a thread to fetch branches for the repository in the sync tab."""
        token = self.app_state.settings_manager.get_github_token()
        repo_url = self.sync_repo_entry.get().strip()
        if not token or not repo_url: self.app.show_toast("GitHub Token and Repo URL required.", "warning")

        spinner = ButtonSpinner(self.fetch_branches_btn)
        spinner.start()
        threading.Thread(target=self._run_fetch_branches_threaded, args=(token, repo_url, self.sync_branch_menu, spinner), daemon=True).start()

    def _run_fetch_branches_threaded(self, token: str, repo_url: str, menu_to_update: ctk.CTkComboBox, spinner: ButtonSpinner) -> None:
        """Worker thread that calls the GitHub handler to get branches."""
        try:
            branches = self.github_handler.get_branches(token, repo_url)
            self.app.after(0, self._update_branch_menu, branches, menu_to_update)
        except (ValueError, ConnectionError) as e:
            self.app.after(0, self.app.show_toast, f"Error fetching branches: {e}", "error")
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"An unexpected error occurred: {e}", "error")
        finally:
            self.app.after(0, spinner.stop)
    
    def _update_branch_menu(self, branches: List[str], menu: ctk.CTkComboBox) -> None:
        """Populates a branch combobox with a list of branch names."""
        if branches:
            current_val = menu.get()
            menu.configure(values=branches)
            if current_val in branches:
                menu.set(current_val)
            else:
                menu.set(branches[0])
        else:
            menu.configure(values=["main"]); menu.set("main")

    def _save_sync_project(self) -> None:
        """Saves a new sync project to the application settings."""
        repo_url = self.sync_repo_entry.get().strip(); branch = self.sync_branch_menu.get()
        if not all([self.new_project_local_path, repo_url, branch]):
            self.app.show_toast("All fields are required to save a project.", "warning"); return
        new_project = {'local_path': self.new_project_local_path, 'repo_url': repo_url, 'branch': branch}
        if any(p['local_path'] == self.new_project_local_path for p in self.app_state.saved_sync_projects):
            self.app.show_toast("A project with this local path already exists.", "warning"); return
        self.app_state.saved_sync_projects.append(new_project)
        self.app_state.settings_manager.set('saved_sync_projects', self.app_state.saved_sync_projects)
        self._populate_saved_projects()
        self.app.show_toast("Project saved successfully!", "success")
        self.new_project_local_path = None
        self.new_project_path_label.configure(text="No folder selected", text_color=self.ds.colors.text.secondary)
        self.sync_repo_entry.delete(0, 'end')

    def _populate_saved_projects(self) -> None:
        """Renders the list of saved sync projects with an edit button and full local path."""
        for widget in self.saved_projects_frame.winfo_children(): widget.destroy()
        if not self.app_state.saved_sync_projects:
            ctk.CTkLabel(self.saved_projects_frame, text="No projects saved yet.", text_color=self.ds.colors.text.secondary).pack(pady=self.ds.spacing.l)
        else:
            for project in self.app_state.saved_sync_projects:
                card = CardFrame(self.saved_projects_frame, self.ds); card.pack(fill="x", pady=(0, self.ds.spacing.m), padx=self.ds.spacing.s); card.grid_columnconfigure(0, weight=1)
                
                # Header: Name, Branch, Actions
                top_frame = ctk.CTkFrame(card, fg_color="transparent"); top_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(self.ds.spacing.s,0)); top_frame.grid_columnconfigure(0, weight=1)
                
                name_text = f"{os.path.basename(project['local_path'])} - {project['branch']}"
                ctk.CTkLabel(top_frame, text=name_text, font=self.ds.typography.body_bold, anchor="w").grid(row=0, column=0, sticky="ew")
                
                # Action Buttons
                edit_btn = ctk.CTkButton(top_frame, text="✏️", command=lambda p=project: self._edit_sync_project_path(p), width=30, fg_color="transparent", hover_color=self.ds.colors.secondary)
                edit_btn.grid(row=0, column=1, sticky="e")

                remove_btn = ctk.CTkButton(top_frame, text="🗑️", command=lambda p=project: self._remove_sync_project(p), width=30, fg_color="transparent", hover_color=self.ds.colors.danger)
                remove_btn.grid(row=0, column=2, sticky="e")

                # Detail: Repo URL
                ctk.CTkLabel(card, text=project['repo_url'], font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary, anchor="w").grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0,0))
                
                # Detail: Full Local Path (NEW)
                path_label = ctk.CTkLabel(card, text=f"Local: {project['local_path']}", font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary, anchor="w")
                path_label.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.s))
                
                # Sync Actions
                btn_frame = ctk.CTkFrame(card, fg_color="transparent"); btn_frame.grid(row=3, column=0, sticky="ew", padx=self.ds.spacing.m, pady=(self.ds.spacing.s,self.ds.spacing.m)); btn_frame.grid_columnconfigure((0,1), weight=1)
                overwrite_btn = WarningButton(btn_frame, self.ds, text="Pull & Overwrite")
                overwrite_btn.configure(command=lambda p=project, b=overwrite_btn: self._start_sync_thread(p, 'overwrite', b))
                overwrite_btn.grid(row=0, column=0, padx=(0,self.ds.spacing.s), sticky="ew")
                merge_btn = ButtonWithHover(btn_frame, self.ds, text="Pull & Merge")
                merge_btn.configure(command=lambda p=project, b=merge_btn: self._start_sync_thread(p, 'merge', b))
                merge_btn.grid(row=0, column=1, padx=(self.ds.spacing.s,0), sticky="ew")

    def _edit_sync_project_path(self, project: dict) -> None:
        """Opens a dialog to change the local path of a saved project."""
        new_path = filedialog.askdirectory(initialdir=project['local_path'], title=f"Select new location for {os.path.basename(project['local_path'])}")
        if new_path:
            # Update the project object in place
            project['local_path'] = new_path
            # Save all projects
            self.app_state.settings_manager.set('saved_sync_projects', self.app_state.saved_sync_projects)
            # Refresh UI
            self._populate_saved_projects()
            self.app.show_toast("Local project path updated.", "success")

    def _remove_sync_project(self, project_to_remove: dict) -> None:
        """Removes a saved sync project from settings."""
        self.app_state.saved_sync_projects = [p for p in self.app_state.saved_sync_projects if p['local_path'] != project_to_remove['local_path']]
        self.app_state.settings_manager.set('saved_sync_projects', self.app_state.saved_sync_projects)
        self._populate_saved_projects()
        self.app.show_toast("Project removed.", "info")

    # --- Backup & Restore Logic ---
    def _backup_project(self, local_path: str) -> None:
        """Creates a zip backup of the local project before modification."""
        try:
            timestamp = int(time.time())
            backup_dir = os.path.join(os.path.expanduser("~"), ".gemini_code_assistant_backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_name = f"{os.path.basename(local_path)}_backup_{timestamp}"
            archive_path = shutil.make_archive(os.path.join(backup_dir, backup_name), 'zip', local_path)
            
            self.app_state.last_sync_backup_path = archive_path
            self.app.update_status(f"Backup created: {os.path.basename(archive_path)}")
            self.app.after(0, self._check_backup_status)
        except Exception as e:
            print(f"Backup failed: {e}")
            self.app.show_toast(f"Backup failed: {e}", "warning")
            logging.error(traceback.format_exc())

    def _check_backup_status(self) -> None:
        """Updates the Restore button state based on backup availability."""
        if hasattr(self, 'restore_backup_btn'):
            state = "normal" if self.app_state.last_sync_backup_path and os.path.exists(self.app_state.last_sync_backup_path) else "disabled"
            self.restore_backup_btn.configure(state=state)

    def _restore_last_backup(self) -> None:
        """Restores the last created backup after confirmation."""
        if not self.app_state.last_sync_backup_path or not os.path.exists(self.app_state.last_sync_backup_path):
            self.app.show_toast("No backup found to restore.", "error"); return

        # Find which project this backup belongs to (heuristic based on filename)
        backup_filename = os.path.basename(self.app_state.last_sync_backup_path)
        target_project = None
        for project in self.app_state.saved_sync_projects:
            if os.path.basename(project['local_path']) in backup_filename:
                target_project = project
                break
        
        if not target_project:
            self.app.show_toast("Could not identify target project for this backup.", "error"); return

        ConfirmationDialog(self.app, self.ds, "Restore Backup", 
                           f"Are you sure you want to revert '{target_project['local_path']}' to the state before the last sync?\n\nCurrent files will be overwritten.",
                           lambda: self._execute_restore(target_project['local_path'], self.app_state.last_sync_backup_path))

    def _execute_restore(self, target_path: str, backup_path: str) -> None:
        try:
            shutil.unpack_archive(backup_path, target_path)
            self.app.show_toast("Backup restored successfully!", "success")
            self.app_state.last_sync_backup_path = None # Clear after restore
            self._check_backup_status()
        except Exception as e:
            self.app.show_toast(f"Restore failed: {e}", "error")
            logging.error(traceback.format_exc())

    # --- Modified Sync Logic ---
    def _start_sync_thread(self, project: dict, mode: str, button: ctk.CTkButton) -> None:
        """Starts the local sync process in a new thread."""
        token = self.app_state.settings_manager.get_github_token()
        if not token: self.app.show_toast("GitHub Token must be set in Settings.", "error"); return
        
        # New: Ask for instructions/options before starting
        dialog = ctk.CTkToplevel(self.app)
        dialog.title("Sync Options")
        dialog.geometry("500x350")
        dialog.transient(self.app)
        dialog.grab_set()
        
        # Center dialog
        x = self.app.winfo_x() + (self.app.winfo_width()//2) - 250
        y = self.app.winfo_y() + (self.app.winfo_height()//2) - 175
        dialog.geometry(f"+{x}+{y}")

        ctk.CTkLabel(dialog, text="Custom AI Instructions (Optional)", font=self.ds.typography.h2).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="e.g., 'Delete old log files', 'Only add .py files', 'Prioritize local config'").pack(pady=(0, 10))
        
        instr_text = ctk.CTkTextbox(dialog, height=80)
        instr_text.pack(padx=20, fill="x")
        
        backup_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(dialog, text="Create Local Backup (Recommended)", variable=backup_var).pack(pady=15)
        
        def on_confirm():
            instructions = instr_text.get("1.0", "end-1c").strip()
            do_backup = backup_var.get()
            dialog.destroy()
            
            button.configure(state="disabled")
            self._start_long_process()
            threading.Thread(target=self._run_sync_process_threaded, args=(project, mode, token, button, instructions, do_backup), daemon=True).start()

        SuccessButton(dialog, self.ds, text="Start Sync", command=on_confirm).pack(pady=10)

    def _run_sync_process_threaded(self, project: dict, mode: str, token: str, button: ctk.CTkButton, instructions: str, do_backup: bool) -> None:
        """Worker thread for running a local sync operation with advanced AI handling."""
        try:
            local_root = project['local_path']
            
            if do_backup:
                self.app.update_status("Creating backup...")
                self._backup_project(local_root)

            self.app.update_status(f"Fetching remote files from {project['branch']}...")
            remote_files = self.github_handler.get_remote_files(token, project['repo_url'], project['branch'])
            
            # --- OVERWRITE MODE ---
            if mode == 'overwrite':
                self.app.update_status(f"Overwriting {len(remote_files)} files...")
                for rel_path, content in remote_files.items():
                    local_path = os.path.join(local_root, rel_path)
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    if isinstance(content, bytes):
                        with open(local_path, 'wb') as f: f.write(content)
                    else:
                        with open(local_path, 'w', encoding='utf-8') as f: f.write(content)
                self.app.after(0, self.app.show_toast, "Overwrite complete!", "success")
            
            # --- MERGE / SMART SYNC MODE ---
            elif mode == 'merge':
                self.merge_queue.clear()
                self.app.update_status(f"AI evaluating additions/deletions...")
                
                # 1. Scan Local Files
                local_files_map = {}
                for root, dirs, files in os.walk(local_root):
                    # Filter hidden dirs
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__', 'node_modules']]
                    for file in files:
                        if file.startswith('.'): continue
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, local_root).replace("\\", "/")
                        try:
                            with open(abs_path, 'r', encoding='utf-8') as f:
                                local_files_map[rel_path] = f.read()
                        except (UnicodeDecodeError, LookupError):
                            continue # Skip binary/unreadable

                local_keys = set(local_files_map.keys())
                remote_keys = set(remote_files.keys())

                # 2. AI Decision for Add/Delete (if instructions provided)
                to_delete = []
                to_add = list(remote_keys - local_keys) # Default: Add all new remote files

                if instructions:
                    self.app.update_status(f"AI evaluating changes...")
                    decision = self.gemini_handler.evaluate_sync_changes(list(local_keys), list(remote_keys), instructions)
                    to_delete = decision.get("delete", [])
                    # AI might filter which remote files to add
                    if "add" in decision:
                        to_add = decision["add"]

                # 3. Execute Deletions
                for rel_path in to_delete:
                    full_path = os.path.join(local_root, rel_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        print(f"Deleted {rel_path}")

                # 4. Execute Additions
                for rel_path in to_add:
                    if rel_path in remote_files:
                        full_path = os.path.join(local_root, rel_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        content = remote_files[rel_path]
                        if isinstance(content, bytes):
                            with open(full_path, 'wb') as f: f.write(content)
                        else:
                            with open(full_path, 'w', encoding='utf-8') as f: f.write(content)

                # 5. Handle Conflicts (Common Files)
                common_files = local_keys & remote_keys
                for rel_path in common_files:
                    local_content = local_files_map[rel_path]
                    remote_content = remote_files[rel_path]
                    
                    if isinstance(remote_content, bytes):
                        continue

                    if local_content != remote_content:
                        self.app.update_status(f"Merging {rel_path} with AI...")
                        # Pass instructions to merge logic
                        merged_code = self.gemini_handler.run_ai_merge(local_content, remote_content, rel_path, custom_instructions=instructions)
                        
                        local_abs_path = os.path.join(local_root, rel_path)
                        self.merge_queue.append({'local_path': local_abs_path, 'local_code': local_content, 'merged_code': merged_code})

                if self.merge_queue:
                    self.app.after(0, self._stop_long_process)
                    self.app.after(0, lambda: button.configure(state="normal"))
                    self.app.after(0, self._process_merge_queue)
                else:
                    self.app.after(0, self.app.show_toast, "Sync complete.", "success")
                    self.app.after(0, self._stop_long_process)
                    self.app.after(0, lambda: button.configure(state="normal"))

        except Exception as e:
            self.app.after(0, self.app.show_toast, f"Sync Error: {e}", "error")
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: button.configure(state="normal"))
            logging.error(traceback.format_exc())

    def _process_merge_queue(self) -> None:
        """Interactively shows diff viewers for files in the merge queue."""
        if self.merge_queue:
            item = self.merge_queue.popleft()
            self.app.update_status(f"Review merge for {os.path.basename(item['local_path'])}...")
            # Chain the next call via the on_accept_callback.
            self.app.show_diff_viewer(
                original=item['local_code'], 
                updated=item['merged_code'], 
                file_path=item['local_path'], 
                on_accept_callback=self._process_merge_queue 
            )
        else:
            self.app.update_status("Ready")
            self.app.show_toast("Merge process complete!", "success")

    def _start_fetch_history_thread(self) -> None:
        """Starts a thread to fetch commit history for the selected repository and branch."""
        repo_url = self.history_repo_entry.get().strip()
        branch = self.history_branch_menu.get().strip()
        if not repo_url or not branch:
            self.app.show_toast("Repo URL and Branch are required.", "warning")
            return
            
        token = self.app_state.settings_manager.get_github_token()
        if not token: self.app.show_toast("GitHub Token must be set in Settings.", "error"); return
        
        spinner = ButtonSpinner(self.fetch_history_btn)
        spinner.start()
        threading.Thread(target=self._run_fetch_history_threaded, args=(token, repo_url, branch, spinner), daemon=True).start()

    def _run_fetch_history_threaded(self, token: str, repo_url: str, branch: str, spinner: ButtonSpinner) -> None:
        """Worker thread that calls the GitHub handler to get commit history."""
        try:
            history = self.github_handler.get_commit_history(token, repo_url, branch)
            self.app.after(0, self._populate_commit_history_frame, history, repo_url, branch)
        except (ValueError, ConnectionError) as e: self.app.after(0, self.app.show_toast, f"Failed to fetch history: {e}", "error")
        except Exception as e: self.app.after(0, self.app.show_toast, f"An unexpected error occurred: {e}", "error")
        finally: self.app.after(0, spinner.stop)
    
    def _show_history_empty_state(self) -> None:
        """Displays a message when no commit history has been fetched."""
        for widget in self.commit_history_frame.winfo_children(): widget.destroy()
        ctk.CTkLabel(self.commit_history_frame, text="🕒", font=("Segoe UI", 50)).pack(pady=(80, 10))
        ctk.CTkLabel(self.commit_history_frame, text="No History Fetched", font=self.ds.typography.h2).pack()
        ctk.CTkLabel(self.commit_history_frame, text="Select a project and fetch its history.", font=self.ds.typography.body, text_color=self.ds.colors.text.secondary).pack()
        
    def _populate_commit_history_frame(self, history: list[dict], repo_url: str, branch: str) -> None:
        """Renders the list of commits in the history tab."""
        for widget in self.commit_history_frame.winfo_children(): widget.destroy()
        if not history:
            ctk.CTkLabel(self.commit_history_frame, text="No commit history found for this branch.", text_color=self.ds.colors.text.secondary).pack(pady=20)
            return
        for commit in history:
            card = CardFrame(self.commit_history_frame, self.ds); card.pack(fill="x", pady=(0, self.ds.spacing.m), padx=self.ds.spacing.s); card.grid_columnconfigure(0, weight=1)
            info_frame = ctk.CTkFrame(card, fg_color="transparent"); info_frame.grid(row=0, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m); info_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(info_frame, text=commit['message'], font=self.ds.typography.body_bold, anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(info_frame, text=f"by {commit['author']} on {commit['date']}", font=self.ds.typography.body_small, text_color=self.ds.colors.text.secondary, anchor="w").grid(row=1, column=0, sticky="w")
            ctk.CTkLabel(info_frame, text=f"SHA: {commit['sha'][:7]}", font=self.ds.typography.code_small, text_color=self.ds.colors.text.secondary, anchor="w").grid(row=2, column=0, sticky="w", pady=(self.ds.spacing.s,0))
            action_frame = ctk.CTkFrame(card, fg_color="transparent"); action_frame.grid(row=0, column=1, sticky="e", padx=self.ds.spacing.m)
            revert_btn = DangerButton(action_frame, self.ds, text="Revert to this commit")
            revert_btn.configure(command=lambda r=repo_url, b=branch, c_sha=commit['sha']: self._confirm_and_revert_commit(r, b, c_sha))
            revert_btn.pack(pady=self.ds.spacing.m)

    def _confirm_and_revert_commit(self, repo_url: str, branch: str, commit_sha: str) -> None:
        """Shows a confirmation dialog before reverting a branch."""
        dialog = ctk.CTkInputDialog(text=f"This will overwrite the remote history for branch '{branch}' and cannot be undone.\n\nType 'overwrite' to confirm:", title="Confirm Destructive Action")
        dialog.geometry(f"+{self.app.winfo_rootx() + 200}+{self.app.winfo_rooty() + 200}")
        if dialog.get_input() == "overwrite":
            self.app.show_toast("Confirmation received. Starting revert...", "info")
            self.fetch_history_btn.configure(state="disabled")
            self._start_long_process()
            threading.Thread(target=self._run_revert_threaded, args=(repo_url, branch, commit_sha), daemon=True).start()
        else:
            self.app.show_toast("Revert cancelled.", "warning")

    def _run_revert_threaded(self, repo_url: str, branch: str, commit_sha: str) -> None:
        """Worker thread that calls the GitHub handler to force reset a branch."""
        try:
            token = self.app_state.settings_manager.get_github_token()
            if not token:
                raise ValueError("GitHub token not found.")
            self.github_handler.force_reset_branch(token, repo_url, branch, commit_sha)
            self.app.after(0, self.app.show_toast, f"Branch '{branch}' successfully reverted.", "success")
        except Exception as e:
            self.app.after(0, self.app.show_toast, f"Revert failed: {e}", "error")
            logging.error(traceback.format_exc())
        finally:
            self.app.after(0, self._stop_long_process)
            self.app.after(0, lambda: self.fetch_history_btn.configure(state="normal"))
            self.app.after(100, self._start_fetch_history_thread)

    def update_theme(self) -> None:
        """Updates the theme for all components in the GitHub GUI tab."""
        # --- Global ---
        self.segmented_button.configure(
            selected_color=self.ds.colors.primary,
            selected_hover_color=self.ds.colors.primary_hover,
            unselected_color=self.ds.colors.surface.base,
            unselected_hover_color=self.ds.colors.surface.card
        )

        # --- Push View ---
        if self._views_loaded.get("Push", False):
            self.push_config_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.push_staged_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.push_commit_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.push_fetch_branches_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.push_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
        
        # --- Sync View ---
        if self._views_loaded.get("Sync", False):
            self.sync_add_project_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.sync_saved_projects_container.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.sync_select_folder_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.fetch_branches_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.sync_save_project_btn.configure(fg_color=self.ds.colors.success, hover_color=self.ds.colors.success_hover)
            if hasattr(self, 'new_project_path_label') and "No folder selected" in self.new_project_path_label.cget("text"):
                self.new_project_path_label.configure(text_color=self.ds.colors.text.secondary)
            self._populate_saved_projects() # Re-draw projects with new theme

        # --- Delete View ---
        if self._views_loaded.get("Delete", False):
            self.delete_config_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.delete_list_container.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.delete_commit_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.delete_fetch_btn.configure(fg_color=self.ds.colors.secondary, hover_color=self.ds.colors.secondary_hover)
            self.delete_btn.configure(fg_color=self.ds.colors.danger, hover_color=self.ds.colors.danger_hover)

        # --- History View ---
        if self._views_loaded.get("History", False):
            self.history_controls_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.border)
            self.history_warning_frame.configure(fg_color=self.ds.colors.surface.card, border_color=self.ds.colors.warning)
            self.fetch_history_btn.configure(fg_color=self.ds.colors.primary, hover_color=self.ds.colors.primary_hover)
            if hasattr(self, 'commit_history_frame') and not self.commit_history_frame.winfo_children(): # Only re-draw empty state if it's visible
                self._show_history_empty_state()
            
            if hasattr(self, 'commit_history_frame') and self.commit_history_frame.winfo_children() and "No commit history" not in self.commit_history_frame.winfo_children()[0].cget("text"):
                self._start_fetch_history_thread()