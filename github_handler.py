import os
import re
import base64
from github import Github, InputGitTreeElement, ContentFile, GitCommit, GithubException, UnknownObjectException
import concurrent.futures
from typing import List, Dict, Set, Any, Callable, Union

class GitHubHandler:
    """
    Handles all interactions with the GitHub API via the PyGithub library.
    This includes fetching repository data, managing branches, and pushing commits.
    """
    def __init__(self, status_callback: Callable[[str], None], toast_callback: Callable[[str, str], None]):
        """
        Initializes the GitHubHandler.

        Args:
            status_callback: A function to update the application's status bar.
            toast_callback: A function to show toast notifications.
        """
        self.update_status = status_callback
        self.show_toast = toast_callback

    def _get_repo_from_url(self, g: Github, repo_url: str) -> Any:
        """
        Parses a GitHub URL to get a Repository object.

        Args:
            g: An authenticated Github instance.
            repo_url: The full URL of the repository.

        Returns:
            A PyGithub Repository object.

        Raises:
            ValueError: If the URL format is invalid or the repo is not found.
        """
        repo_name_match = re.search(r"github\.com/([^/]+/[^/]+)", repo_url)
        if not repo_name_match:
            raise ValueError("Invalid GitHub repository URL format. Expected '...github.com/user/repo'.")
        repo_name = repo_name_match.group(1).replace('.git', '')
        try:
            return g.get_repo(repo_name)
        except UnknownObjectException:
            raise ValueError(f"Repository '{repo_name}' not found or token lacks permissions.")
        except Exception as e:
            raise e

    def get_branches(self, token: str, repo_url: str) -> List[str]:
        """
        Fetches a list of branch names for a given repository.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.

        Returns:
            A list of branch names.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)
        branches = [b.name for b in repo.get_branches()]
        return branches

    def get_user_repos(self, token: str) -> List[str]:
        """
        Fetches all repositories the authenticated user has access to.

        Args:
            token: A GitHub personal access token.

        Returns:
            A list of repository HTML URLs (e.g., https://github.com/user/repo).
        """
        g = Github(token)
        repos = []
        try:
            # get_user().get_repos() returns repos owned by the user
            # plus repos they collaborate on or are in their orgs.
            for repo in g.get_user().get_repos():
                repos.append(repo.html_url)
        except Exception as e:
            self.show_toast(f"Error fetching accessible repositories: {e}", "warning")
            
        return sorted(repos, key=str.lower)

    def get_remote_files(self, token: str, repo_url: str, branch: str) -> Dict[str, Union[str, bytes]]:
        """
        Recursively fetches all file paths and their contents for a given branch using ThreadPoolExecutor.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.
            branch: The name of the branch.

        Returns:
            A dictionary mapping file paths to their string or bytes content.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)
        
        ref = repo.get_git_ref(f'heads/{branch}')
        head_sha = ref.object.sha
        tree = repo.get_git_tree(head_sha, recursive=True)
        
        remote_files: Dict[str, Union[str, bytes]] = {}
        blobs = [element for element in tree.tree if element.type == 'blob']
        
        def fetch_blob(element) -> tuple:
            full_path = element.path.replace("\\", "/")
            try:
                # Use get_contents to fetch file content
                content_file: ContentFile = repo.get_contents(full_path, ref=branch)
                
                if content_file.encoding == "base64":
                    try:
                        # Improved binary detection checking for null bytes
                        decoded = content_file.decoded_content.decode('utf-8')
                        if '\x00' in decoded:
                            return full_path, content_file.decoded_content # Return bytes
                        return full_path, decoded
                    except UnicodeDecodeError:
                        return full_path, content_file.decoded_content # Return bytes
                elif content_file.encoding is None or content_file.encoding == "none":
                    return full_path, ""
                else:
                    return full_path, None
            except Exception as e:
                self.update_status(f"Warning: Could not fetch content for {full_path}: {e}")
                return full_path, None

        # Conservative concurrency 5 for free tier
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_blob, element): element for element in blobs}
            for future in concurrent.futures.as_completed(futures):
                path, content = future.result()
                if content is not None:
                    remote_files[path] = content

        return remote_files
        
    def get_remote_tree_structure(self, token: str, repo_url: str, branch: str) -> List[str]:
        """
        Fetches a simple list of all file paths (blobs) in the remote branch.
        This is faster than get_remote_files as it doesn't fetch content.

        Args:
            token: GitHub token.
            repo_url: Repository URL.
            branch: Branch name.

        Returns:
            List of file paths.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)
        
        ref = repo.get_git_ref(f'heads/{branch}')
        head_sha = ref.object.sha
        tree = repo.get_git_tree(head_sha, recursive=True)
        
        # Only return blobs (files), ignoring subtrees (directories)
        return [element.path for element in tree.tree if element.type == 'blob']

    def get_commit_history(self, token: str, repo_url: str, branch: str) -> List[Dict[str, Any]]:
        """
        Fetches the last 50 commits from a branch's history.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.
            branch: The name of the branch.

        Returns:
            A list of dictionaries, each representing a commit.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)
        commits_paginated_list = repo.get_commits(sha=branch)
        
        history: List[Dict[str, Any]] = []
        # Get the last 50 commits for performance
        for i, commit in enumerate(commits_paginated_list):
            if i >= 50:
                break
            
            commit_data: GitCommit = commit.commit
            history.append({
                "sha": commit.sha,
                "message": commit_data.message.split('\n')[0], # First line only
                "author": commit_data.author.name,
                "date": commit_data.author.date.strftime("%Y-%m-%d %H:%M:%S")
            })
        return history

    def force_reset_branch(self, token: str, repo_url: str, branch: str, commit_sha: str) -> None:
        """
        Performs a hard reset on a remote branch to a specific commit SHA.
        This is a destructive operation.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.
            branch: The branch to reset.
            commit_sha: The commit SHA to reset the branch to.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)
        
        ref = repo.get_git_ref(f'heads/{branch}')
        ref.edit(sha=commit_sha, force=True)

    def run_github_push(self, token: str, repo_url: str, branch: str, commit_msg: str, staged_files: Set[str], opened_folder_path: str) -> bool:
        """
        Creates a new commit with the staged files and pushes it to the remote branch.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.
            branch: The branch to push to.
            commit_msg: The commit message.
            staged_files: A set of absolute paths to the files to be committed.
            opened_folder_path: The root path of the opened project.

        Returns:
            True on success, False on failure.
        """
        try:
            g = Github(token)
            repo = self._get_repo_from_url(g, repo_url)
            
            self.update_status("Creating tree...")
            elements: List[InputGitTreeElement] = []
            
            for fp in staged_files:
                try:
                    rel_path = os.path.relpath(fp, opened_folder_path).replace("\\", "/")
                    
                    # Read all files as binary first to determine how to handle them
                    with open(fp, 'rb') as f:
                        file_data = f.read()
                    
                    # Try to decode as UTF-8 to see if it's a text file
                    is_binary = False
                    text_content = None
                    try:
                        text_content = file_data.decode('utf-8')
                        if '\x00' in text_content:
                            is_binary = True
                    except UnicodeDecodeError:
                        is_binary = True

                    # 100KB limit for direct content in tree API. 
                    # If binary OR larger than 100KB, create a blob.
                    if is_binary or len(file_data) > 100 * 1024:
                        # Upload as blob (safe for images, videos, and large text files)
                        data_b64 = base64.b64encode(file_data).decode("utf-8")
                        blob = repo.create_git_blob(data_b64, "base64")
                        elements.append(InputGitTreeElement(path=rel_path, mode='100644', type='blob', sha=blob.sha))
                    else:
                        # Optimization: Use direct content for small text files
                        elements.append(InputGitTreeElement(path=rel_path, mode='100644', type='blob', content=text_content))

                except (IOError, OSError) as e:
                    self.show_toast(f"Skipping {os.path.basename(fp)}: {e}", "warning")
                    continue
                except Exception as e:
                    self.show_toast(f"Error processing {os.path.basename(fp)}: {e}", "warning")
                    continue
            
            if not elements:
                raise ValueError("No valid files to commit.")

            ref = repo.get_git_ref(f'heads/{branch}')
            latest_commit = repo.get_git_commit(ref.object.sha)
            base_tree = latest_commit.tree
            tree = repo.create_git_tree(elements, base_tree=base_tree)
            
            self.update_status("Committing...")
            parent_commit = [latest_commit]
            commit = repo.create_git_commit(commit_msg, tree, parent_commit)
            
            self.update_status("Pushing...")
            ref.edit(commit.sha)
            
            self.show_toast(f"Pushed to {repo.full_name} successfully!", "success")
            return True
        except (GithubException, ValueError) as e:
            self.show_toast(f"GitHub Push Failed: {e}", "error")
            return False

    def delete_files_from_repo(self, token: str, repo_url: str, branch: str, file_paths: List[str], commit_message: str) -> bool:
        """
        Deletes multiple files from a remote repository by creating a new tree that excludes them.

        Args:
            token: GitHub token.
            repo_url: Repository URL.
            branch: Branch name.
            file_paths: List of file paths (relative to repo root) to delete.
            commit_message: Commit message.

        Returns:
            True on success.
        """
        try:
            g = Github(token)
            repo = self._get_repo_from_url(g, repo_url)

            self.update_status("Fetching current tree...")
            ref = repo.get_git_ref(f'heads/{branch}')
            head_sha = ref.object.sha
            # Get full recursive tree to reconstruct it
            base_tree = repo.get_git_tree(head_sha, recursive=True)

            files_to_delete = set(file_paths)
            new_tree_elements = []

            # Rebuild the tree, keeping only blobs that are NOT in the delete list
            # We ignore 'tree' type elements to let Git reconstruct directories from blobs
            for element in base_tree.tree:
                if element.type == 'blob' and element.path not in files_to_delete:
                    new_tree_elements.append(InputGitTreeElement(path=element.path, mode=element.mode, type=element.type, sha=element.sha))
            
            if not new_tree_elements:
                 # This would mean deleting everything in the repo, creating an empty tree.
                 # Git usually allows this but it's a rare edge case.
                 pass

            self.update_status("Creating new tree...")
            # Create a completely new tree (no base_tree passed) to reflect deletions
            new_tree = repo.create_git_tree(new_tree_elements)

            self.update_status("Committing deletion...")
            parent_commit = repo.get_git_commit(head_sha)
            commit = repo.create_git_commit(commit_message, new_tree, [parent_commit])

            self.update_status("Updating ref...")
            ref.edit(commit.sha)

            self.show_toast(f"Deleted {len(file_paths)} file(s) successfully.", "success")
            return True

        except Exception as e:
            self.show_toast(f"Deletion failed: {e}", "error")
            return False

    def create_pull_request_with_changes(self, token: str, repo_url: str, base_branch: str, new_branch_name: str, files_content: Dict[str, str], pr_title: str, pr_body: str) -> str:
        """
        Creates a new branch from a base, commits files to it, and opens a pull request.

        Args:
            token: A GitHub personal access token.
            repo_url: The URL of the repository.
            base_branch: The branch to branch off from and merge back into (e.g., 'main').
            new_branch_name: The name for the new branch (e.g., 'ai-merge-feature-x').
            files_content: A dictionary of {file_path: content} for the final state of the repo.
            pr_title: The title for the pull request.
            pr_body: The body/description for the pull request.

        Returns:
            The URL of the newly created pull request.
        
        Raises:
            ValueError: If the new branch already exists.
        """
        g = Github(token)
        repo = self._get_repo_from_url(g, repo_url)

        # Check if branch already exists
        try:
            repo.get_branch(new_branch_name)
            raise ValueError(f"Branch '{new_branch_name}' already exists. Please delete it or choose a different name.")
        except UnknownObjectException:
            pass # Branch doesn't exist, which is good

        self.update_status(f"Getting ref for base branch '{base_branch}'...")
        base_ref = repo.get_git_ref(f'heads/{base_branch}')
        
        self.update_status(f"Creating new branch '{new_branch_name}'...")
        repo.create_git_ref(ref=f'refs/heads/{new_branch_name}', sha=base_ref.object.sha)
        
        self.update_status("Creating blobs for new file tree...")
        elements = [InputGitTreeElement(path=path, mode='100644', type='blob', content=content) for path, content in files_content.items()]
        
        self.update_status("Creating new git tree...")
        tree = repo.create_git_tree(elements)

        self.update_status("Creating commit on new branch...")
        base_commit = repo.get_git_commit(base_ref.object.sha)
        parents = [base_commit]
        commit = repo.create_git_commit(pr_title, tree, parents)

        self.update_status(f"Updating head of '{new_branch_name}'...")
        new_branch_ref = repo.get_git_ref(f'heads/{new_branch_name}')
        new_branch_ref.edit(commit.sha)

        self.update_status("Creating pull request...")
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=new_branch_name,
            base=base_branch
        )
        
        self.show_toast("Pull request created successfully!", "success")
        return pr.html_url