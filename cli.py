import argparse
import sys
import os
import shutil
import time
import hashlib
from typing import List, Set, Dict, Union

# Ensure the script directory is in the import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import SettingsManager
from github_handler import GitHubHandler
from gemini_handler import GeminiHandler

def status_callback(msg: str) -> None:
    print(f"[Status] {msg}")

def toast_callback(msg: str, level: str) -> None:
    print(f"[{level.upper()}] {msg}")

def prompt_for_config(repo_url: str, branch: str, settings: SettingsManager):
    """
    Prompts the user via CLI input for repo and branch if they are missing
    from arguments and saved settings.
    Checks if sys.stdin is a TTY to prevent hanging in non-interactive agent tasks.
    """
    if not repo_url:
        saved_repo = settings.get('github_repo_url')
        if saved_repo:
            repo_url = saved_repo
        else:
            if not sys.stdin.isatty():
                print("Error: Running in non-interactive environment, but GitHub repository URL is missing. Please specify it using --repo.")
                sys.exit(1)
            try:
                repo_url = input("GitHub Repository URL not specified. Please enter the repository URL: ").strip()
            except (IOError, EOFError):
                print("Error: Running in non-interactive environment, but GitHub repository URL is missing.")
                sys.exit(1)
            if not repo_url:
                print("Error: GitHub repository URL cannot be empty.")
                sys.exit(1)
            settings.set('github_repo_url', repo_url)

    if not branch:
        saved_branch = settings.get('github_branch')
        if saved_branch:
            branch = saved_branch
        else:
            if not sys.stdin.isatty():
                print("Error: Running in non-interactive environment, but branch name is missing. Please specify it using --branch.")
                sys.exit(1)
            try:
                branch = input("GitHub Branch name not specified (e.g. main). Enter branch name: ").strip()
            except (IOError, EOFError):
                print("Error: Running in non-interactive environment, but branch name is missing.")
                sys.exit(1)
            if not branch:
                branch = "main"
            settings.set('github_branch', branch)

    return repo_url, branch

def stage_and_filter_files(paths: List[str], work_dir: str, stage_all: bool = False) -> Set[str]:
    """
    Collects files from paths (supporting directories recursively) or all files in work_dir.
    Applies standard filters and reads .gitignore to filter out files.
    """
    opened_folder = os.path.abspath(work_dir)
    abs_files: Set[str] = set()

    if stage_all:
        for root, dirs, filenames in os.walk(opened_folder):
            # Ignore directory walking if they are standard ignores
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.astro', 'dist', 'venv', '__pycache__', '.idea', '.vscode'}]
            for filename in filenames:
                abs_files.add(os.path.join(root, filename))
    else:
        if not paths:
            return set()
        for fp in paths:
            abs_p = os.path.abspath(fp)
            if os.path.isdir(abs_p):
                for root, dirs, filenames in os.walk(abs_p):
                    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '.astro', 'dist', 'venv', '__pycache__', '.idea', '.vscode'}]
                    for filename in filenames:
                        abs_files.add(os.path.join(root, filename))
            elif os.path.isfile(abs_p):
                abs_files.add(abs_p)
            else:
                print(f"Warning: Path not found: {fp}")

    # Read .gitignore patterns
    ignore_patterns = {'.git', 'node_modules', '.astro', 'dist', '.env', 'venv', '__pycache__', '.idea', '.vscode'}
    gitignore_path = os.path.join(opened_folder, '.gitignore')
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as gf:
                for line in gf:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Normalize slash and strip slashes
                        pattern = line.replace('\\', '/').strip('/')
                        if pattern:
                            ignore_patterns.add(pattern)
        except Exception as e:
            print(f"[Warning] Failed to read .gitignore: {e}")

    filtered_files: Set[str] = set()
    for fp in abs_files:
        rel_p = os.path.relpath(fp, opened_folder).replace("\\", "/")
        parts = rel_p.split('/')
        should_ignore = False
        for pat in ignore_patterns:
            # Simple gitignore matching: match directory parts, prefix paths, or wildcards
            if pat in parts or any(part.startswith(pat) for part in parts) or rel_p.startswith(pat):
                should_ignore = True
                break
        if not should_ignore:
            filtered_files.add(fp)

    return filtered_files

def handle_push(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, branch = prompt_for_config(args.repo, args.branch, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured. Run ForgeSync GUI first to enter token.")
        sys.exit(1)

    opened_folder = os.path.abspath(args.work_dir)
    stage_all = getattr(args, 'all', False)
    files_arg = getattr(args, 'files', None)

    if not stage_all and not files_arg:
        print("Error: You must specify files to push using --files, or specify --all / -A to push all changes.")
        sys.exit(1)

    filtered_files = stage_and_filter_files(files_arg, opened_folder, stage_all)

    if not filtered_files:
        print("Error: No files staged to commit (or all files were filtered out by gitignore rules).")
        sys.exit(1)

    print(f"Syncing staged files: {[os.path.relpath(f, opened_folder) for f in filtered_files]}")
    success = github_handler.run_github_push(
        token=token,
        repo_url=repo_url,
        branch=branch,
        commit_msg=args.message,
        staged_files=filtered_files,
        opened_folder_path=opened_folder
    )
    if success:
        print("Successfully committed and pushed to GitHub.")
    else:
        print("Push failed.")
        sys.exit(1)

def handle_delete(args, settings: SettingsManager, github_handler: GitHubHandler):
    # Strict validation of delete commands
    if not args.force:
        print("="*60)
        print("STRICT DELETION PROTECTION WARNING")
        print("="*60)
        print(f"You requested deletion of {len(args.files)} file(s) from GitHub:")
        for f in args.files:
            print(f"  - {f}")
        print("\nTo confirm and execute this deletion, you must specify the --force flag.")
        print("="*60)
        sys.exit(1)

    repo_url, branch = prompt_for_config(args.repo, args.branch, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    print(f"Executing deletion of {len(args.files)} file(s) on branch '{branch}'...")
    success = github_handler.delete_files_from_repo(
        token=token,
        repo_url=repo_url,
        branch=branch,
        file_paths=args.files,
        commit_message=args.message
    )
    if success:
        print("Files deleted from remote branch successfully.")
    else:
        print("Deletion failed.")
        sys.exit(1)

def handle_history(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, branch = prompt_for_config(args.repo, args.branch, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    print(f"Fetching commit history for {repo_url} on branch '{branch}'...")
    try:
        history = github_handler.get_commit_history(token, repo_url, branch)
        limit = min(args.limit, len(history))
        print("\n" + "="*80)
        print(f"LAST {limit} COMMITS")
        print("="*80)
        print(f"{'SHA':<10} | {'DATE':<19} | {'AUTHOR':<15} | {'MESSAGE'}")
        print("-"*80)
        for i in range(limit):
            c = history[i]
            sha = c['sha'][:8]
            date = c['date']
            author = c['author'][:15]
            msg = c['message'][:30]
            print(f"{sha:<10} | {date:<19} | {author:<15} | {msg}")
        print("="*80)
    except Exception as e:
        print(f"Error fetching history: {e}")
        sys.exit(1)

def handle_files(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, branch = prompt_for_config(args.repo, args.branch, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    print(f"Fetching remote file list for {repo_url} on branch '{branch}'...")
    try:
        files = github_handler.get_remote_tree_structure(token, repo_url, branch)
        print("\n" + "="*80)
        print(f"REMOTE FILES ON BRANCH '{branch}' ({len(files)} total)")
        print("="*80)
        for f in sorted(files):
            print(f)
        print("="*80)
    except Exception as e:
        print(f"Error fetching remote files: {e}")
        sys.exit(1)

def handle_sync(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, branch = prompt_for_config(args.repo, args.branch, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    local_root = os.path.abspath(args.local_path)
    if not os.path.exists(local_root):
        print(f"Error: Local path does not exist: {local_root}")
        sys.exit(1)

    # 1. Create Local Backup
    if not args.no_backup:
        try:
            timestamp = int(time.time())
            backup_dir = os.path.join(os.path.expanduser("~"), ".gemini_code_assistant_backups")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"{os.path.basename(local_root)}_backup_{timestamp}"
            archive_path = shutil.make_archive(os.path.join(backup_dir, backup_name), 'zip', local_root)
            print(f"[Backup] Created archive: {archive_path}")
        except Exception as e:
            print(f"[Backup Warning] Failed to build backup: {e}")

    # 2. Fetch Remote Files
    print(f"Retrieving remote repository files from branch '{branch}'...")
    try:
        remote_files = github_handler.get_remote_files(token, repo_url, branch)
    except Exception as e:
        print(f"Error downloading remote files: {e}")
        sys.exit(1)

    # 3. Apply Overwrite or Merge
    if args.mode == 'overwrite':
        print(f"Overwriting local folder with {len(remote_files)} remote files...")
        for rel_path, content in remote_files.items():
            local_path = os.path.join(local_root, rel_path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            if isinstance(content, bytes):
                with open(local_path, 'wb') as f: f.write(content)
            else:
                with open(local_path, 'w', encoding='utf-8') as f: f.write(content)
        print("Overwrite synchronization completed.")

    elif args.mode == 'merge':
        print("Scanning local project files for smart merge...")
        local_files_map = {}
        for root, dirs, files in os.walk(local_root):
            # Ignore binary/hidden structures
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__', 'node_modules']]
            for file in files:
                if file.startswith('.'): continue
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, local_root).replace("\\", "/")
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        local_files_map[rel_path] = f.read()
                except (UnicodeDecodeError, LookupError):
                    continue

        local_keys = set(local_files_map.keys())
        remote_keys = set(remote_files.keys())

        to_delete = []
        to_add = list(remote_keys - local_keys)

        # AI decisions if instructions are provided
        gemini = GeminiHandler(settings, status_callback, toast_callback)
        
        if args.instructions:
            print("Applying AI rules to file structure additions/deletions...")
            try:
                decision = gemini.evaluate_sync_changes(list(local_keys), list(remote_keys), args.instructions)
                to_delete = decision.get("delete", [])
                if "add" in decision:
                    to_add = decision["add"]
            except Exception as e:
                print(f"[AI Warning] Decision evaluation failed, falling back to safe sync defaults: {e}")

        # Delete operations
        for rel_path in to_delete:
            full_path = os.path.join(local_root, rel_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                print(f"[Delete] Local file removed: {rel_path}")

        # Add operations
        for rel_path in to_add:
            if rel_path in remote_files:
                full_path = os.path.join(local_root, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                content = remote_files[rel_path]
                if isinstance(content, bytes):
                    with open(full_path, 'wb') as f: f.write(content)
                else:
                    with open(full_path, 'w', encoding='utf-8') as f: f.write(content)
                print(f"[Download] Added remote file: {rel_path}")

        # Merge conflicts
        common_files = local_keys & remote_keys
        for rel_path in common_files:
            local_content = local_files_map[rel_path]
            remote_content = remote_files[rel_path]

            if isinstance(remote_content, bytes):
                continue

            if local_content != remote_content:
                print(f"[AI Merge] Merging conflicting modifications for: {rel_path}...")
                try:
                    merged = gemini.run_ai_merge(local_content, remote_content, rel_path, custom_instructions=args.instructions or "")
                    full_path = os.path.join(local_root, rel_path)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(merged)
                    print(f"[AI Merge] Applied successfully: {rel_path}")
                except Exception as e:
                    print(f"[AI Merge Error] Could not merge {rel_path}: {e}")

        print("Smart sync process completed.")

def handle_pr(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, base_branch = prompt_for_config(args.repo, args.base, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    from github import Github
    g = Github(token)
    repo = github_handler._get_repo_from_url(g, repo_url)

    work_dir = getattr(args, 'work_dir', '.')
    stage_all = getattr(args, 'all', False)
    files_arg = getattr(args, 'files', None)

    if files_arg or stage_all:
        # Commit files to new head branch and open PR
        filtered_files = stage_and_filter_files(files_arg, work_dir, stage_all)
        if not filtered_files:
            print("Error: No files staged for PR creation.")
            sys.exit(1)

        files_content = {}
        for f in filtered_files:
            abs_p = os.path.abspath(f)
            rel_path = os.path.relpath(abs_p, os.path.abspath(work_dir)).replace("\\", "/")
            try:
                with open(abs_p, 'r', encoding='utf-8') as file_obj:
                    files_content[rel_path] = file_obj.read()
            except Exception as e:
                print(f"Error reading file {f}: {e}")
                sys.exit(1)
        
        print(f"Creating branch '{args.head}' and opening PR to '{base_branch}'...")
        try:
            pr_url = github_handler.create_pull_request_with_changes(
                token=token,
                repo_url=repo_url,
                base_branch=base_branch,
                new_branch_name=args.head,
                files_content=files_content,
                pr_title=args.title,
                pr_body=args.body
            )
            print(f"Pull Request created successfully! URL: {pr_url}")
        except Exception as e:
            print(f"Error creating PR with changes: {e}")
            sys.exit(1)
    else:
        print(f"Opening PR from existing branch '{args.head}' to '{base_branch}'...")
        try:
            pr = repo.create_pull(
                title=args.title,
                body=args.body,
                base=base_branch,
                head=args.head
            )
            print(f"Pull Request created successfully! URL: {pr.html_url}")
        except Exception as e:
            print(f"Error creating PR: {e}")
            sys.exit(1)

def handle_config(args, settings: SettingsManager):
    if args.set:
        for item in args.set:
            if "=" not in item:
                print(f"Error: Invalid configuration format: {item}. Expected key=value")
                sys.exit(1)
            key, value = item.split("=", 1)
            if value.lower() == 'true': value = True
            elif value.lower() == 'false': value = False
            settings.set(key, value)
            print(f"[Config] Saved setting: {key} = {value}")
        settings.flush()

    if args.set_token:
        settings.save_github_token(args.set_token)
        print("[Config] Saved GitHub Personal Access Token to secure keyring.")

    if args.set_key:
        settings.save_api_key(args.set_key)
        print("[Config] Saved Google Gemini API Key to secure keyring.")

    if args.show:
        print("\n" + "="*50)
        print("FORGESYNC SETTINGS")
        print("="*50)
        for key, val in sorted(settings.settings.items()):
            print(f"{key:<25} : {val}")
        print("="*50)

def handle_branch(args, settings: SettingsManager, github_handler: GitHubHandler):
    repo_url, base_branch = prompt_for_config(args.repo, args.base, settings)
    token = settings.get_github_token()
    if not token:
        print("Error: GitHub token is not configured.")
        sys.exit(1)

    from github import Github
    g = Github(token)
    repo = github_handler._get_repo_from_url(g, repo_url)

    if args.create:
        new_branch = args.create
        print(f"Creating branch '{new_branch}' from base '{base_branch}'...")
        try:
            base_ref = repo.get_git_ref(f'heads/{base_branch}')
            repo.create_git_ref(ref=f'refs/heads/{new_branch}', sha=base_ref.object.sha)
            print(f"Branch '{new_branch}' created successfully.")
        except Exception as e:
            print(f"Error creating branch: {e}")
            sys.exit(1)

    if args.list:
        print(f"Fetching branches for {repo_url}...")
        try:
            branches = github_handler.get_branches(token, repo_url)
            print("\n" + "="*50)
            print(f"BRANCHES ({len(branches)} total)")
            print("="*50)
            for b in branches:
                prefix = "* " if b == base_branch else "  "
                print(f"{prefix}{b}")
            print("="*50)
        except Exception as e:
            print(f"Error listing branches: {e}")
            sys.exit(1)

def handle_compare(args):
    dir_a = os.path.abspath(args.dir_a)
    dir_b = os.path.abspath(args.dir_b)

    if not os.path.exists(dir_a):
        print(f"Error: Folder A does not exist: {dir_a}")
        sys.exit(1)
    if not os.path.exists(dir_b):
        print(f"Error: Folder B does not exist: {dir_b}")
        sys.exit(1)

    print(f"Scanning Folder A: {dir_a}...")
    files_a = get_local_file_hashes(dir_a)
    print(f"Scanning Folder B: {dir_b}...")
    files_b = get_local_file_hashes(dir_b)

    set_a = set(files_a.keys())
    set_b = set(files_b.keys())

    only_in_a = sorted(list(set_a - set_b))
    only_in_b = sorted(list(set_b - set_a))
    common_files = set_a & set_b

    modified = []
    for file in sorted(list(common_files)):
        if files_a[file] != files_b[file]:
            modified.append(file)

    print("\n" + "="*80)
    print("FOLDER COMPARISON RESULTS")
    print("="*80)
    print(f"Folder A: {dir_a}")
    print(f"Folder B: {dir_b}\n")

    print(f"Files only in A ({len(only_in_a)}):")
    for f in only_in_a:
        print(f"  + {f}")
    if not only_in_a: print("  None")

    print(f"\nFiles only in B ({len(only_in_b)}):")
    for f in only_in_b:
        print(f"  + {f}")
    if not only_in_b: print("  None")

    print(f"\nModified Files ({len(modified)}):")
    for f in modified:
        print(f"  * {f}")
    if not modified: print("  None")
    print("="*80)

def get_local_file_hashes(start_path: str) -> Dict[str, str]:
    hashes = {}
    ignored_dirs = {".git", "__pycache__", ".vscode", "node_modules", "venv", ".env"}
    for dirpath, dirs, filenames in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
        for filename in filenames:
            if filename.startswith('.'): continue
            full_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(full_path, start_path).replace("\\", "/")
            try:
                sha256 = hashlib.sha256()
                with open(full_path, "rb") as f:
                    while chunk := f.read(8192):
                        sha256.update(chunk)
                hashes[relative_path] = sha256.hexdigest()
            except Exception:
                hashes[relative_path] = ""
    return hashes

def main():
    parser = argparse.ArgumentParser(description="ForgeSync Terminal CLI interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Push CLI Options
    push_p = subparsers.add_parser("push", help="Commit and push changes to remote GitHub repo")
    push_p.add_argument("--files", nargs="+", help="Space-separated list of files/directories to commit")
    push_p.add_argument("--all", "-A", action="store_true", help="Stage all files in working directory (similar to git add .)")
    push_p.add_argument("--message", required=True, help="Commit message description")
    push_p.add_argument("--repo", help="GitHub repo URL (overrides saved setting)")
    push_p.add_argument("--branch", help="Remote branch (overrides saved setting)")
    push_p.add_argument("--work-dir", default=".", help="Root working directory of the project")

    # Delete CLI Options
    del_p = subparsers.add_parser("delete", help="Strictly delete files from remote repository branch")
    del_p.add_argument("--files", nargs="+", required=True, help="List of file paths relative to repo root to delete")
    del_p.add_argument("--message", required=True, help="Commit message for deletions")
    del_p.add_argument("--repo", help="GitHub repo URL")
    del_p.add_argument("--branch", help="Remote branch")
    del_p.add_argument("--force", action="store_true", help="Confirm execution of destructive file deletions")

    # History CLI Options
    hist_p = subparsers.add_parser("history", help="Retrieve recent commit logs for repository branch")
    hist_p.add_argument("--repo", help="GitHub repo URL")
    hist_p.add_argument("--branch", help="Remote branch")
    hist_p.add_argument("--limit", type=int, default=10, help="Maximum commits to show (default 10)")

    # Sync CLI Options
    sync_p = subparsers.add_parser("sync", help="Synchronize remote repository files with local workspace")
    sync_p.add_argument("--local-path", default=".", help="Local project folder destination path")
    sync_p.add_argument("--repo", help="GitHub repo URL")
    sync_p.add_argument("--branch", help="Remote branch")
    sync_p.add_argument("--mode", choices=["overwrite", "merge"], default="merge", help="Conflict resolution strategy: overwrite or merge")
    sync_p.add_argument("--instructions", help="Custom natural language AI rules for filtering files and resolving conflict merges")
    sync_p.add_argument("--no-backup", action="store_true", help="Skip creating a ZIP backup archive of the folder")

    # Files CLI Options
    files_p = subparsers.add_parser("files", help="List all file paths in the remote repository branch")
    files_p.add_argument("--repo", help="GitHub repo URL")
    files_p.add_argument("--branch", help="Remote branch")

    # PR CLI Options
    pr_p = subparsers.add_parser("pr", help="Open a pull request on GitHub")
    pr_p.add_argument("--head", required=True, help="Head branch to merge from")
    pr_p.add_argument("--title", required=True, help="Pull Request title")
    pr_p.add_argument("--body", required=True, help="Pull Request description body")
    pr_p.add_argument("--base", help="Base branch to merge into")
    pr_p.add_argument("--files", nargs="+", help="Optional local files/directories to commit directly to the head branch first")
    pr_p.add_argument("--all", "-A", action="store_true", help="Commit all changes in work-dir directly to the head branch first")
    pr_p.add_argument("--repo", help="GitHub repo URL")
    pr_p.add_argument("--work-dir", default=".", help="Root working directory of the project")

    # Config CLI Options
    cfg_p = subparsers.add_parser("config", help="Manage application configurations and secrets")
    cfg_p.add_argument("--set", nargs="+", help="Space-separated list of key=value configurations to write")
    cfg_p.add_argument("--set-token", help="Update GitHub access token securely in the keyring")
    cfg_p.add_argument("--set-key", help="Update Google Gemini API key securely in the keyring")
    cfg_p.add_argument("--show", action="store_true", help="Show all configurations saved in setting file")

    # Branch CLI Options
    br_p = subparsers.add_parser("branch", help="List or create remote repository branches")
    br_p.add_argument("--list", action="store_true", help="List all remote branches")
    br_p.add_argument("--create", help="Create a new remote branch from base")
    br_p.add_argument("--base", help="Base branch to branch off of")
    br_p.add_argument("--repo", help="GitHub repo URL")

    # Compare CLI Options
    comp_p = subparsers.add_parser("compare", help="Compare file lists and checksum hashes of two local folders")
    comp_p.add_argument("--dir-a", required=True, help="Folder A directory path")
    comp_p.add_argument("--dir-b", required=True, help="Folder B directory path")

    args = parser.parse_args()

    settings = SettingsManager()
    github_handler = GitHubHandler(status_callback, toast_callback)

    if args.command == "push":
        handle_push(args, settings, github_handler)
    elif args.command == "delete":
        handle_delete(args, settings, github_handler)
    elif args.command == "history":
        handle_history(args, settings, github_handler)
    elif args.command == "sync":
        handle_sync(args, settings, github_handler)
    elif args.command == "files":
        handle_files(args, settings, github_handler)
    elif args.command == "pr":
        handle_pr(args, settings, github_handler)
    elif args.command == "config":
        handle_config(args, settings)
    elif args.command == "branch":
        handle_branch(args, settings, github_handler)
    elif args.command == "compare":
        handle_compare(args)

if __name__ == "__main__":
    main()
