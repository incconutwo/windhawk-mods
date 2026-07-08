from google import genai
from google.genai import types
from google.genai import errors
import re
import os
import time
from typing import Optional, List, Callable, Any, Dict
import json

class GeminiHandler:
    """
    Handles all interactions with the Google Gemini API using the correct Python SDK.
    This class is responsible for configuring the API, constructing prompts,
    and processing responses for various tasks like code merging and analysis.
    """
    def __init__(self, settings_manager: 'SettingsManager', status_callback: Callable[[str], None], toast_callback: Callable[[str, str], None]):
        """
        Initializes the GeminiHandler.

        Args:
            settings_manager: An instance of the SettingsManager.
            status_callback: A function to update the application's status bar.
            toast_callback: A function to show toast notifications.
        """
        self.settings_manager = settings_manager
        self.update_status = status_callback
        self.show_toast = toast_callback
        self._is_configured = False
        self.client: Optional[genai.Client] = None

    def is_configured(self) -> bool:
        """Checks if the Gemini API client has been successfully configured."""
        return self._is_configured

    def configure_gemini(self, api_key: str, is_startup: bool = False) -> bool:
        """
        Configures the Gemini API client with the provided key and validates it.

        Args:
            api_key: The Google Gemini API key.
            is_startup: A flag to suppress notifications during initial app launch.

        Returns:
            True if configuration was successful, False otherwise.
        """
        if not api_key:
            if not is_startup: self.show_toast("Please enter your Gemini API key.", "warning")
            return False
        try:
            self.client = genai.Client(api_key=api_key)
            
            # Validate the key with a lightweight, temporary call based on current settings
            model_name = self.settings_manager.get('gemini_model')
            self.client.models.count_tokens(
                model=model_name,
                contents="test"
            ) # Low-cost validation call
            
            self._is_configured = True
            self.settings_manager.save_api_key(api_key)
            
            msg = "Gemini API configured successfully."
            if not is_startup: self.show_toast(msg, "success")
            else: self.update_status(msg)
            return True
        except errors.APIError as e:
            self._is_configured = False
            self.client = None
            if e.code == 403:
                if not is_startup: self.show_toast("API Error: Invalid API Key.", "error")
            else:
                error_message = f"API Error: {e.message}"
                if not is_startup: self.show_toast(error_message, "error")
            return False
        except Exception as e:
            self._is_configured = False
            self.client = None
            error_message = f"API Configuration Failed: {e}"
            if "not found" in str(e).lower() or "permission" in str(e).lower():
                 error_message = f"API Error: Model '{self.settings_manager.get('gemini_model')}' not found or you lack access."
            if not is_startup: self.show_toast(error_message, "error")
            return False
            
    def _call_gemini_api(self, prompt: str, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        A centralized method for calling the Gemini API with robust error handling,
        retry logic, and optional streaming support.

        Args:
            prompt: The complete prompt to send to the model.
            stream_callback: Optional callback to receive streaming chunks.

        Returns:
            The generated text from the model.

        Raises:
            Exception: If the API call fails after retries.
        """
        if not self.is_configured():
            api_key = self.settings_manager.get_api_key()
            if not api_key or not self.configure_gemini(api_key, is_startup=True):
                  raise Exception("Gemini API is not configured. Please check your API key in Settings.")

        max_retries = 3
        base_delay = 2
        current_model_name = self.settings_manager.get('gemini_model')

        for attempt in range(max_retries):
            try:
                # Set temperature to 0.0 to prevent repetition loops
                config = types.GenerateContentConfig(temperature=0.0)
                
                if stream_callback:
                    response = self.client.models.generate_content_stream(
                        model=current_model_name,
                        contents=prompt,
                        config=config
                    )
                    full_text = ""
                    for chunk in response:
                        if chunk.text:
                            full_text += chunk.text
                            stream_callback(chunk.text)
                    updated_code = full_text
                else:
                    response = self.client.models.generate_content(
                        model=current_model_name,
                        contents=prompt,
                        config=config
                    )
                    
                    # Check for safety blocks
                    if not response.candidates:
                        if response.prompt_feedback and response.prompt_feedback.block_reason:
                            finish_reason = getattr(response.prompt_feedback.block_reason, 'name', str(response.prompt_feedback.block_reason))
                            self.show_toast(f"Response was blocked: {finish_reason}", "error")
                            raise Exception(f"Generation stopped due to {finish_reason}")
                        else:
                            raise Exception("No candidates returned from Gemini API.")
                    
                    candidate = response.candidates[0]
                    finish_reason = None
                    if candidate.finish_reason:
                        finish_reason = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))
                    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
                        self.show_toast(f"Response was blocked: {finish_reason}", "error")
                        raise Exception(f"Generation stopped due to {finish_reason}")
                    
                    updated_code = response.text
                
                # Clean up markdown code blocks if the model includes them
                updated_code = re.sub(r'^\s*```[a-zA-Z]*\n?|\n?```\s*$', '', updated_code, flags=re.MULTILINE)
                return updated_code
                
            except errors.APIError as e:
                if attempt < max_retries - 1 and e.code in (429, 503):
                    delay = base_delay * (2 ** attempt)
                    status_msg = "Rate limited" if e.code == 429 else "API unavailable"
                    self.update_status(f"{status_msg}. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                if e.code == 429:
                    self.show_toast("API Error: Rate Limit Exceeded after retries.", "error")
                else:
                    self.show_toast(f"Google API Error: {e.message}", "error")
                raise Exception(f"Google API Error: {e.message}")
            except Exception as e:
                # Catching other potential API errors
                self.show_toast(f"An unexpected API error occurred: {e}", "error")
                raise Exception(f"An unexpected API error occurred: {e}")

    def run_merge_process(self, original_file_path: str, original_code: str, context_file_paths: List[str], snippet: str, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Constructs a prompt and calls the Gemini API to merge a snippet into code.

        Args:
            original_file_path: The path of the primary file being modified.
            original_code: The original content of the primary file.
            context_file_paths: A list of paths to context files.
            snippet: The code snippet or instructions to apply.
            stream_callback: Optional callback to stream the process.

        Returns:
            The full, updated code content as returned by the model.
        """
        context_parts = []
        for p in context_file_paths:
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    context_parts.append(f"\n--- CONTEXT FILE: {os.path.basename(p)} ---\n{f.read()}")
            except Exception:
                # Silently ignore files that can't be read
                continue
        context = "".join(context_parts)
            
        prompt = (f"{self.settings_manager.get('custom_prompt')}\n{context}\n"
                  f"--- PRIMARY TARGET FILE: {os.path.basename(original_file_path)} ---\n{original_code}\n"
                  f"---\nNEW CODE SNIPPET/INSTRUCTIONS TO APPLY:\n---\n{snippet}\n"
                  f"---\nProvide the full, updated file content of the primary target file now:")
            
        return self._call_gemini_api(prompt, stream_callback=None)
        
    def analyze_code_changes(self, original_code: str, new_code: str, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Asks the Gemini API to provide a high-level summary of code changes.

        Args:
            original_code: The original version of the code.
            new_code: The new version of the code.
            stream_callback: Optional callback to stream the text analysis.

        Returns:
            A text analysis of the changes.
        """
        prompt = f"""Analyze the code changes below. Provide a concise, high-level summary of the purpose of the change.
        --- ORIGINAL CODE ---\n{original_code}\n--- NEW CODE ---\n{new_code}"""
        return self._call_gemini_api(prompt, stream_callback=stream_callback)
        
    def run_ai_merge(self, local_code: str, remote_code: str, file_path: str, custom_instructions: str = "") -> str:
        """
        Asks the Gemini API to perform an intelligent merge of two code versions.
        Accepts optional custom instructions to guide the merge strategy.

        Args:
            local_code: The user's local version of the file.
            remote_code: The remote (e.g., GitHub) version of the file.
            file_path: The path of the file being merged.
            custom_instructions: Optional instructions to guide the merge.

        Returns:
            The full, merged code content.
        """
        instruction_text = ""
        if custom_instructions:
            instruction_text = f"\nCUSTOM INSTRUCTIONS FOR MERGE:\n{custom_instructions}\nPlease follow these instructions strictly when resolving conflicts or combining features.\n"

        prompt = f"""You are an expert code merging tool. Your task is to intelligently merge two versions of a file.

The 'LOCAL' version contains the user's current work. The 'REMOTE' version is from a GitHub repository.

Your goal is to merge the changes from the 'REMOTE' version into the 'LOCAL' version. 
{instruction_text}
You must:
1. Preserve the user's local changes where possible.
2. Intelligently combine changes if both versions have been modified in the same area.
3. Your output must be only the complete, merged file content. Do not add any commentary, explanations, or markdown formatting.

--- LOCAL FILE: {os.path.basename(file_path)} ---
{local_code}

--- REMOTE VERSION ---
{remote_code}

---
Provide the full, merged file content now:
"""
        return self._call_gemini_api(prompt, stream_callback=None)

    def evaluate_sync_changes(self, local_unique_files: List[str], remote_unique_files: List[str], instructions: str) -> Dict[str, List[str]]:
        """
        Asks AI to decide which local-only files to delete and which remote-only files to add based on instructions.
        
        Args:
            local_unique_files: Files present locally but missing on remote.
            remote_unique_files: Files present on remote but missing locally.
            instructions: Natural language instructions guiding the sync decision.

        Returns: A JSON dict: {"delete": ["file1"], "add": ["file2"]}
        """
        if not instructions:
            # Default behavior if no instructions: Keep local files (safe), Add remote files (sync)
            return {"delete": [], "add": remote_unique_files}

        prompt = f"""You are an intelligent project synchronization assistant. 
You are syncing a Local folder with a Remote GitHub repository.

Here is the situation:
1. "Local Only Files": Files present locally but missing on remote.
2. "Remote Only Files": Files present on remote but missing locally.

USER INSTRUCTIONS: "{instructions}"

Based on the user instructions, decide:
1. Which "Local Only Files" should be DELETED? (e.g. if user says "clean up old files").
2. Which "Remote Only Files" should be ADDED? (e.g. if user says "get new features").

LISTS:
- Local Only Files: {json.dumps(local_unique_files)}
- Remote Only Files: {json.dumps(remote_unique_files)}

OUTPUT FORMAT:
Return a raw JSON object with two keys: "delete" (list of local files to remove) and "add" (list of remote files to download).
Do not include markdown formatting.
"""
        response = self._call_gemini_api(prompt, stream_callback=None)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback safe mode
            return {"delete": [], "add": remote_unique_files}

    def interpret_file_rename_command(self, file_list: List[str], command: str) -> str:
        """
        Asks the Gemini API to convert a natural language command into a map of file renames.

        Args:
            file_list: A list of current filenames in the directory.
            command: The user's natural language command (e.g., "change py to txt").

        Returns:
            A JSON string representing a dictionary of { "old_name": "new_name" }.
        """
        prompt = f"""You are an intelligent file renaming bot. Your task is to interpret a user's command and apply it to a given list of files.

RULES:
1. Your output MUST be a valid JSON object.
2. The JSON object should be a map where keys are the original filenames and values are the new filenames.
3. Only include files in the JSON object that should actually be renamed.
4. Do not rename files that are not affected by the command.
5. Do not add any explanations or markdown formatting like ```json.

USER COMMAND: "{command}"

FILE LIST:
{json.dumps(file_list, indent=2)}

Provide the JSON object now:
"""
        return self._call_gemini_api(prompt, stream_callback=None)

    def run_ai_branch_merge(self, source_code: str, destination_code: str, file_path: str, priority: str) -> str:
        """
        Asks the Gemini API to merge two versions of a file with a specified priority.

        Args:
            source_code: The version of the code from the source branch.
            destination_code: The version of the code from the destination branch.
            file_path: The path of the file being merged.
            priority: The branch to prioritize ('source' or 'destination').

        Returns:
            The full, merged code content.
        """
        if priority == 'source':
            priority_code = source_code
            other_code = destination_code
            other_name = 'destination'
        else:
            priority_code = destination_code
            other_code = source_code
            other_name = 'source'

        prompt = f"""You are an expert code merging tool. Your task is to intelligently merge two conflicting versions of a file.

The '{priority.upper()}' version contains the changes that should be prioritized. The '{other_name.upper()}' version is the base.

Your goal is to merge the changes, but when there's a direct conflict, you MUST favor the implementation from the '{priority.upper()}' version. You should still try to include non-conflicting changes from the '{other_name.upper()}' version.

Your output must be only the complete, merged file content. Do not add any commentary, explanations, or markdown formatting.

--- FILE PATH: {os.path.basename(file_path)} ---

--- {priority.upper()} VERSION (PRIORITY) ---
{priority_code}

--- {other_name.upper()} VERSION ---
{other_code}

---
Provide the full, merged file content now:
"""
        return self._call_gemini_api(prompt, stream_callback=None)
