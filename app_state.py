from typing import Optional, List, Set, Any, Dict

class AppState:
    """
    A centralized class to hold the application's shared state.
    
    This class acts as a single source of truth for data that needs to be
    accessed or modified by multiple controllers or UI components. This avoids
    prop drilling and simplifies state management.

    Attributes:
        settings_manager: An instance of SettingsManager for persistent settings.
        original_file_path: The absolute path of the currently selected target file.
        context_file_paths: A list of absolute paths for files used as context.
        original_code_backup: A string backup of the original file content before saving a change.
        original_file_path_for_undo: The path corresponding to the backup, used for the undo action.
        opened_folder_path: The root path of the folder opened in the file explorer.
        staged_github_files: A set of absolute file paths staged for a GitHub commit.
        change_history: A list of recent changes made, loaded from settings.
        saved_sync_projects: A list of saved local sync project configurations.
        last_sync_backup_path: The file path to the most recent zip backup created during sync.
    """
    
    def __init__(self, settings_manager: 'SettingsManager'):
        self.settings_manager = settings_manager
        
        # File and code state
        self.original_file_path: Optional[str] = None
        self.context_file_paths: List[str] = []
        self.original_code_backup: Optional[str] = None
        self.original_file_path_for_undo: Optional[str] = None # Track which file the backup belongs to
        self.opened_folder_path: Optional[str] = None
        
        # Git and sync state
        self.staged_github_files: Set[str] = set()
        self.last_sync_backup_path: Optional[str] = None
        
        # Cache for fetched github repos
        self.github_repos: List[str] = self.settings_manager.get('cached_github_repos', [])
        self.github_branches: Dict[str, List[str]] = self.settings_manager.get('cached_github_branches', {})
        
        # History and settings state, loaded from settings manager
        self.change_history: List[Dict[str, Any]] = self.settings_manager.get('change_history', [])
        self.saved_sync_projects: List[Dict[str, str]] = self.settings_manager.get('saved_sync_projects', [])