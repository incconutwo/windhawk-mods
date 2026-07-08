---
name: "ForgeSync Git Integration"
description: "Handles git operations like push, sync, commit history, and file deletions using the ForgeSync CLI."
---

# ForgeSync Git Integration Skill

This skill allows the Antigravity agent to interface directly with the ForgeSync command-line tool (`cli.py`) to manage remote Git activities.

## Mandatory Pre-Execution Rules

### 1. Repository & Branch Validation (Strict Clarification)
Before running any subcommand (`push`, `sync`, `history`, `delete`), check if the repository URL and branch name have been specified by the user or are available in the conversation history.
*   **Settings Check**: If not specified, look in the workspace settings.
*   **User Clarification Prompt**: If the repository URL or branch name are still unknown/unconfigured, you **MUST** pause execution and ask the user directly in the chat for the exact repository URL and branch name. Do not assume or run commands with missing values.

### 2. Strict File Deletion Protection
File deletion is a destructive operation. Follow these rules strictly:
1.  **Do not auto-delete**: When asked to delete remote files, you must first compile a clear list of target file paths.
2.  **Display Warning & Confirm**: Present the list of files to be deleted to the user in the chat and ask: *"Are you sure you want to permanently delete these files from the repository? Please confirm."*
3.  **Execute with Force Flag**: Only after the user responds with explicit confirmation in the chat should you run the CLI delete command.
4.  **CLI Command Syntax**: You must append the `--force` flag to the command. Without `--force`, the CLI will block or exit without executing.

---

## Command Syntax Directory

All actions are executed using Python to run `cli.py` in the workspace directory.

### 1. Commit and Push Local Files
Use this to commit and push specific local files to GitHub.
```bash
python cli.py push --files <space_separated_list_of_relative_or_absolute_paths> --message "<commit_message>" [--repo <repo_url>] [--branch <branch>]
```

### 2. Synchronize Remote with Local Workspace
Use this to pull changes down from GitHub.
*   **Merge Mode** (Default - Smart AI conflict resolution & merge):
    ```bash
    python cli.py sync --mode merge [--instructions "<custom_instructions>"] [--repo <repo_url>] [--branch <branch>]
    ```
*   **Overwrite Mode** (Forces local files to match remote branch exactly):
    ```bash
    python cli.py sync --mode overwrite [--repo <repo_url>] [--branch <branch>]
    ```
*   *Note*: A ZIP backup is created automatically in `~/.gemini_code_assistant_backups` unless `--no-backup` is specified.

### 3. Remote File Deletion (Requires User Confirmation)
Use this to remove files from the remote GitHub branch.
```bash
python cli.py delete --files <space_separated_list_of_paths_relative_to_repo_root> --message "<commit_message>" --force [--repo <repo_url>] [--branch <branch>]
```

### 4. Fetch Commit History
Use this to retrieve a log of the last N commits.
```bash
python cli.py history [--limit <number>] [--repo <repo_url>] [--branch <branch>]
```
