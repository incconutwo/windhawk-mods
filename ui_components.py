import customtkinter as ctk
from tkinter import ttk, Text
import threading
import os
import diff_match_patch as dmp_module
from typing import Callable, Optional, Any, List

from utils import SyntaxHighlighter
from design_system import DS, CardFrame, ButtonWithHover, SuccessButton, DangerButton, SecondaryButton, PillButton

# =============================================================================
# --- CORE UI BUILDING BLOCKS ---
# =============================================================================
# =============================================================================
# --- ANIMATED FEEDBACK WIDGETS ---
# =============================================================================
class ConfirmationDialog(ctk.CTkToplevel):
    """A modal dialog for user confirmation with a custom message.
    Uses a scrollable area for long messages to ensure buttons stay visible."""

    # Maximum height for the message area before scrolling kicks in
    MAX_MESSAGE_HEIGHT = 400

    def __init__(self, master: Any, ds: DS, title: str, message: str, confirm_callback: Callable):
        super().__init__(master)
        self.ds = ds
        self.confirm_callback = confirm_callback
        self._animation_job: Optional[str] = None

        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)  # Allow resizing for better UX with long content
        self.attributes("-alpha", 0.0) # Start transparent
        
        # Set min and max sizes
        self.minsize(400, 200)
        self.maxsize(600, 700)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=self.ds.spacing.l, pady=self.ds.spacing.l)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)  # Message area expands

        # Use scrollable frame for the message content
        message_container = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        message_container.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        message_container.grid_columnconfigure(0, weight=1)
        
        message_label = ctk.CTkLabel(message_container, text=message, wraplength=450, justify="left", font=self.ds.typography.body, anchor="nw")
        message_label.pack(fill="both", expand=True)

        # Button frame - always at bottom
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, columnspan=2, sticky="e", padx=self.ds.spacing.m, pady=(self.ds.spacing.m, 0))

        cancel_btn = SecondaryButton(button_frame, self.ds, text="Cancel", command=self.close_dialog)
        cancel_btn.pack(side="right", padx=(self.ds.spacing.m, 0))

        confirm_btn = SuccessButton(button_frame, self.ds, text="Confirm", command=self._on_confirm)
        confirm_btn.pack(side="right")

        # Calculate appropriate dialog size based on message length
        self.update_idletasks()
        
        # Estimate height needed (rough: ~20px per line, assuming 50 chars per line)
        line_count = message.count('\n') + (len(message) // 50)
        estimated_height = min(self.MAX_MESSAGE_HEIGHT, max(150, line_count * 22))
        
        # Set dialog size - width stays fixed, height adapts
        dialog_width = 520
        dialog_height = estimated_height + 120  # Add space for buttons and padding
        dialog_height = min(dialog_height, 650)  # Cap maximum height
        
        self.geometry(f"{dialog_width}x{dialog_height}")
        
        # Center on parent
        x = master.winfo_rootx() + (master.winfo_width() // 2) - (dialog_width // 2)
        y = master.winfo_rooty() + (master.winfo_height() // 2) - (dialog_height // 2)
        self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        self._fade_in()

    def _fade_in(self) -> None:
        alpha = self.attributes('-alpha')
        if alpha < 1.0:
            self.attributes('-alpha', min(1.0, alpha + 0.25))
            self._animation_job = self.after(25, self._fade_in)

    def _fade_out(self, callback: Optional[Callable] = None) -> None:
        alpha = self.attributes('-alpha')
        if alpha > 0.0:
            self.attributes('-alpha', max(0.0, alpha - 0.25))
            self._animation_job = self.after(25, lambda: self._fade_out(callback))
        else:
            if callback: callback()
            super().destroy()

    def close_dialog(self) -> None:
        self._fade_out()

    def _on_confirm(self):
        self.confirm_callback()
        self.close_dialog()

    def destroy(self) -> None:
        """Safely cleanup animation and destroy the widget."""
        try:
            if self._animation_job:
                self.after_cancel(self._animation_job)
                self._animation_job = None
        except Exception:
            pass  # Widget may already be destroyed
        if self.winfo_exists():
            super().destroy()

class ToastNotification(ctk.CTkToplevel):
    """
    A professional toast notification with a smooth slide-in/fade-out animation
    that always stays within the screen bounds.
    """
    
    def __init__(self, master: Any, ds: DS, message: str, msg_type: str = 'info', duration: int = 3000):
        """
        Initializes a toast notification.

        Args:
            master: The parent widget.
            ds: The design system instance.
            message: The message to display.
            msg_type: Type of message ('info', 'success', 'warning', 'error').
            duration: How long the toast stays visible in milliseconds.
        """
        super().__init__(master)
        
        self.ds = ds
        self._animation_job: Optional[str] = None

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.0)
        
        color_map = {
            'info': (self.ds.colors.primary, self.ds.colors.text.on_primary),
            'success': (self.ds.colors.success, self.ds.colors.text.on_primary),
            'warning': (self.ds.colors.warning, self.ds.colors.text.on_primary),
            'error': (self.ds.colors.danger, self.ds.colors.text.on_primary)
        }
        bg_color, text_color = color_map.get(msg_type, color_map['info'])
        
        toast_frame = ctk.CTkFrame(self, corner_radius=8, fg_color=bg_color)
        toast_frame.pack(padx=2, pady=2)
        
        content_frame = ctk.CTkFrame(toast_frame, fg_color="transparent")
        content_frame.pack(padx=15, pady=10)
        
        icons = {'info': "ℹ", 'success': "✓", 'warning': "⚠", 'error': "✗"}
        icon = icons.get(msg_type, "")
        
        if icon:
            ctk.CTkLabel(content_frame, text=icon, font=self.ds.typography.h2, text_color=text_color).pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(content_frame, text=message, font=self.ds.typography.body, text_color=text_color).pack(side="left")
        
        self.duration = duration
        self.show()
    
    def show(self) -> None:
        """Positions and displays the toast notification."""
        if not self.master.winfo_exists(): return
        self.master.update_idletasks()
        master_x = self.master.winfo_x()
        master_y = self.master.winfo_y()
        master_w = self.master.winfo_width()
        screen_w = self.master.winfo_screenwidth()
        
        self.update_idletasks()
        toast_w = self.winfo_width()
        toast_h = self.winfo_height()
        
        # Calculate initial position to be centered horizontally and slightly off-screen vertically
        x = master_x + (master_w // 2) - (toast_w // 2)
        start_y = master_y - toast_h # Start above the master window
        self.end_y = master_y + 20   # Final position
        
        # Clamp x-position to stay within screen bounds
        x = max(0, min(x, screen_w - toast_w))
        
        self.geometry(f'+{x}+{start_y}')
        self.current_y = start_y
        self._animate_in()
    
    def _animate_in(self) -> None:
        """Animates the toast sliding in and fading in."""
        if not self.winfo_exists(): return
        alpha = self.attributes('-alpha')
        
        # Animate position with faster easing
        self.current_y += (self.end_y - self.current_y) * 0.35
        
        # Faster alpha animation
        if alpha < 0.95:
            alpha = min(1.0, alpha + 0.25)
            self.attributes('-alpha', alpha)
            
        self.geometry(f'+{int(self.geometry().split("+")[1])}+{int(self.current_y)}')

        if abs(self.current_y - self.end_y) > 1 or alpha < 1.0:
            self.after(20, self._animate_in)
        else:
            self.attributes('-alpha', 1.0)
            self.geometry(f'+{int(self.geometry().split("+")[1])}+{int(self.end_y)}')
            self.after(self.duration, self._fade_out)
    
    def _fade_out(self) -> None:
        """Animates the toast fading out."""
        if not self.winfo_exists(): return
        alpha = self.attributes('-alpha')
        if alpha > 0.05:
            alpha = max(0.0, alpha - 0.25)
            self.attributes('-alpha', alpha)
            self._animation_job = self.after(20, self._fade_out)
        else:
            self.destroy()
    
    def destroy(self) -> None:
        """Safely cleanup animation and destroy the widget."""
        try:
            if self._animation_job:
                self.after_cancel(self._animation_job)
                self._animation_job = None
        except Exception:
            pass  # Widget may already be destroyed
        if self.winfo_exists():
            super().destroy()

class ButtonSpinner:
    """Professional loading animation for buttons."""
    
    def __init__(self, button: ctk.CTkButton):
        """
        Initializes a loading spinner for a button.

        Args:
            button: The CTkButton widget to animate.
        """
        self.button = button
        self.original_text = button.cget("text")
        self.original_state = button.cget("state")
        self.animation_job: Optional[str] = None
        self.dots = 0
    
    def start(self) -> None:
        """Starts the loading animation."""
        self.button.configure(state="disabled")
        self.dots = 0
        self._animate()
    
    def _animate(self) -> None:
        """The animation loop that updates the button text."""
        self.dots = (self.dots + 1) % 4
        dots_text = "." * self.dots
        self.button.configure(text=f"Processing{dots_text:.<4}")
        self.animation_job = self.button.after(400, self._animate)
    
    def stop(self, state: Optional[str] = None) -> None:
        """
        Stops the loading animation and restores the button.

        Args:
            state: The final state for the button ('normal', 'disabled'). 
                   If None, restores the original state.
        """
        if self.animation_job:
            self.button.after_cancel(self.animation_job)
            self.animation_job = None
        
        final_state = state if state is not None else self.original_state
        self.button.configure(text=self.original_text, state=final_state)

# =============================================================================
# --- FILE EXPLORER AND DIFF VIEWER WIDGETS ---
# =============================================================================
class FileTreeView(ttk.Treeview):
    """A styled Treeview for the file explorer, themed by the Design System."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        super().__init__(master, style="Custom.Treeview", **kwargs)
        self.ds = ds
        self.style = ttk.Style()
        self.update_style()
    
    def update_style(self) -> None:
        """Applies Design System colors to the Treeview widget."""
        self.style.theme_use("default")
        self.style.configure("Custom.Treeview", 
                             background=self.ds.colors.surface.base, 
                             foreground=self.ds.colors.text.primary, 
                             fieldbackground=self.ds.colors.surface.base, 
                             borderwidth=0, 
                             rowheight=28)
        self.style.map('Custom.Treeview', background=[('selected', self.ds.colors.primary)])
        self.style.layout("Custom.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

class LineNumberCanvas(ctk.CTkCanvas):
    """Canvas widget for displaying line numbers alongside a Text widget."""
    def __init__(self, master: Any, text_widget: Text, ds: DS, **kwargs: Any):
        super().__init__(master, width=50, highlightthickness=0, **kwargs)
        self.text_widget = text_widget
        self.ds = ds
        self._redraw_scheduled = False
        self._last_redraw_time = 0
        self.update_theme()
        
        text_widget.bind("<Configure>", self.schedule_redraw, add=True)
        text_widget.bind("<KeyRelease>", self.schedule_redraw, add=True)
        text_widget.bind("<MouseWheel>", self.schedule_redraw, add=True)

    def update_theme(self) -> None:
        """Updates the background color based on the Design System."""
        self.configure(bg=self.ds.colors.surface.section)
        self._execute_redraw()  # Direct call for theme update
    
    def schedule_redraw(self, event: Optional[Any] = None) -> None:
        """Schedules a throttled redraw - limits redraws to every 50ms."""
        if not self._redraw_scheduled:
            self._redraw_scheduled = True
            self.after(50, self._execute_redraw)
    
    def redraw(self, event: Optional[Any] = None) -> None:
        """Redraws the line numbers (throttled wrapper)."""
        self.schedule_redraw(event)

    def _execute_redraw(self) -> None:
        """Actually performs the line number redraw."""
        self._redraw_scheduled = False
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(45, y + 2, anchor="ne", text=linenum, font=self.ds.typography.code, fill=self.ds.colors.text.secondary)
            i = self.text_widget.index(f"{i}+1line")

class DiffWindow(ctk.CTkToplevel):
    """Professional diff viewer with a side-by-side comparison and AI analysis."""
    
    CONTEXT_LINES = 3 # Number of unchanged lines to show around a change

    def __init__(self, master: Any, ds: DS, original_code: str, updated_code: str, file_path: str, save_callback: Optional[Callable[[str], None]], gemini_handler: Any, show_toast_callback: Callable[[str, str], None]):
        """
        Initializes the diff viewer window.

        Args:
            master: The parent widget.
            ds: The design system instance.
            original_code: The original code content.
            updated_code: The new, modified code content.
            file_path: The path of the file being changed.
            save_callback: Function to call with the updated code when 'Accept' is clicked.
            gemini_handler: An instance of GeminiHandler for AI analysis.
            show_toast_callback: Function to display toast notifications.
        """
        super().__init__(master)
        
        self.ds = ds
        self.title(f"Review Changes - {os.path.basename(file_path)}")
        self.geometry("1400x800")
        self.minsize(1000, 600)
        self.transient(master); self.grab_set()
        self.attributes("-alpha", 0.0) # Start transparent
        self._animation_job: Optional[str] = None
        
        self.original_code, self.updated_code, self.file_path, self.save_callback, self.gemini_handler, self.show_toast = original_code, updated_code, file_path, save_callback, gemini_handler, show_toast_callback
        self.spinner: Optional[ButtonSpinner] = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self._create_widgets()

        self.highlighter_original = SyntaxHighlighter(self.text_original, self.ds)
        self.highlighter_updated = SyntaxHighlighter(self.text_updated, self.ds)
        
        self._display_diff()
        
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        self._fade_in()
    
    def _fade_in(self) -> None:
        alpha = self.attributes('-alpha')
        if alpha < 1.0:
            self.attributes('-alpha', min(1.0, alpha + 0.25))
            self._animation_job = self.after(25, self._fade_in)

    def _fade_out(self, callback: Optional[Callable] = None) -> None:
        alpha = self.attributes('-alpha')
        if alpha > 0.0:
            self.attributes('-alpha', max(0.0, alpha - 0.25))
            self._animation_job = self.after(25, lambda: self._fade_out(callback))
        else:
            if callback: callback()
            super().destroy()

    def close_dialog(self) -> None:
        self._fade_out()

    def destroy(self) -> None:
        """Safely cleanup animation and destroy the widget."""
        try:
            if self._animation_job:
                self.after_cancel(self._animation_job)
                self._animation_job = None
        except Exception:
            pass  # Widget may already be destroyed
        if self.winfo_exists():
            super().destroy()

    def _create_widgets(self) -> None:
        """Creates and lays out all widgets in the diff window."""
        header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header_frame, text="📝 Code Review", font=self.ds.typography.h1).grid(row=0, column=0, padx=self.ds.spacing.l, pady=self.ds.spacing.m)

        stats_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_frame.grid(row=0, column=1, padx=self.ds.spacing.l, pady=self.ds.spacing.m)
        self.add_label = ctk.CTkLabel(stats_frame, text="➕ 0 additions", text_color=self.ds.colors.success, font=self.ds.typography.body)
        self.add_label.pack(side="left", padx=self.ds.spacing.m)
        self.del_label = ctk.CTkLabel(stats_frame, text="➖ 0 deletions", text_color=self.ds.colors.danger, font=self.ds.typography.body)
        self.del_label.pack(side="left", padx=self.ds.spacing.m)
        
        # Initial stats update
        self._update_stats()

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=self.ds.spacing.m, pady=self.ds.spacing.s)
        content_frame.grid_columnconfigure((0, 1), weight=1); content_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(content_frame, text="Original", font=self.ds.typography.h2).grid(row=0, column=0, pady=self.ds.spacing.s)
        ctk.CTkLabel(content_frame, text="Modified", font=self.ds.typography.h2).grid(row=0, column=1, pady=self.ds.spacing.s)

        self.text_original, self.linenum_original = self._create_text_pane(content_frame, 0)
        self.text_updated, self.linenum_updated = self._create_text_pane(content_frame, 1)

        shared_scrollbar = ctk.CTkScrollbar(content_frame, command=self._on_vertical_scroll)
        shared_scrollbar.grid(row=1, column=2, sticky="ns")

        self.text_original.configure(yscrollcommand=shared_scrollbar.set)
        self.text_updated.configure(yscrollcommand=shared_scrollbar.set)

        bottom_frame = CardFrame(self, self.ds); bottom_frame.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.m, pady=self.ds.spacing.m)
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(bottom_frame, text="AI Analysis", font=self.ds.typography.h2).grid(row=0, column=0, sticky="w", padx=self.ds.spacing.l, pady=(self.ds.spacing.l, self.ds.spacing.s))
        self.explanation_text = ctk.CTkTextbox(bottom_frame, height=80, font=self.ds.typography.body, wrap="word")
        self.explanation_text.grid(row=1, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.m))
        self.explanation_text.insert("1.0", "Click 'Analyze Changes' for an AI-powered summary.")
        self.explanation_text.configure(state="disabled")
        
        button_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent"); button_frame.grid(row=2, column=0, sticky="ew", padx=self.ds.spacing.l, pady=(0, self.ds.spacing.l))
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.analyze_btn = SecondaryButton(button_frame, self.ds, text="🔍 Analyze Changes", command=self._analyze_changes, height=40)
        self.analyze_btn.grid(row=0, column=0, padx=(0, self.ds.spacing.s), sticky="ew")
        
        self.accept_btn = SuccessButton(button_frame, self.ds, text="✓ Accept & Save", command=self._accept_changes, height=40)
        self.accept_btn.grid(row=0, column=1, padx=self.ds.spacing.s, sticky="ew")
        if not self.save_callback: self.accept_btn.configure(state="disabled")

        self.reject_btn = DangerButton(button_frame, self.ds, text="✗ Reject", command=self.close_dialog, height=40)
        self.reject_btn.grid(row=0, column=2, padx=(self.ds.spacing.s, 0), sticky="ew")

    def _on_vertical_scroll(self, *args: Any) -> None:
        """Synchronizes the vertical scrolling of both text panes."""
        self.text_original.yview(*args)
        self.text_updated.yview(*args)
        self.linenum_original.redraw()
        self.linenum_updated.redraw()

    def _create_text_pane(self, parent: ctk.CTkFrame, col: int) -> tuple[Text, LineNumberCanvas]:
        """Creates a frame containing a Text widget and its line numbers."""
        pane = ctk.CTkFrame(parent); pane.grid(row=1, column=col, sticky="nsew", padx=self.ds.spacing.s)
        pane.grid_columnconfigure(1, weight=1); pane.grid_rowconfigure(0, weight=1)
        
        text_widget = Text(pane, wrap="none", font=self.ds.typography.code, 
                           bg=self.ds.colors.surface.section, 
                           fg=self.ds.colors.text.primary,
                           insertbackground=self.ds.colors.text.primary, 
                           selectbackground=self.ds.colors.primary, 
                           borderwidth=0, highlightthickness=0)
        
        linenum = LineNumberCanvas(pane, text_widget, self.ds)
        linenum.grid(row=0, column=0, sticky="ns")
        
        scroll_x = ctk.CTkScrollbar(pane, orientation="horizontal", command=text_widget.xview); scroll_x.grid(row=1, column=1, sticky="ew")
        text_widget.configure(xscrollcommand=scroll_x.set)
        text_widget.grid(row=0, column=1, sticky="nsew")
        return text_widget, linenum

    def _count_changes(self) -> tuple[int, int]:
        """Counts the number of line additions and deletions, similar to git."""
        dmp = dmp_module.diff_match_patch()
        diffs = dmp.diff_main(self.original_code, self.updated_code)
        dmp.diff_cleanupSemantic(diffs)
        
        additions = 0
        deletions = 0
        for op, data in diffs:
            lines = data.splitlines()
            # Count the number of non-empty lines involved in the change
            num_lines = len([line for line in lines if line.strip()]) if not data.endswith('\n') else data.count('\n')

            if op == dmp.DIFF_INSERT:
                additions += num_lines
            elif op == dmp.DIFF_DELETE:
                deletions += num_lines
        return additions, deletions
    
    def _display_diff(self) -> None:
        """Calculates and displays a contextual side-by-side diff, mimicking GitHub."""
        self.text_original.configure(state="normal")
        self.text_updated.configure(state="normal")
        self.text_original.delete("1.0", "end")
        self.text_updated.delete("1.0", "end")

        dmp = dmp_module.diff_match_patch()
        diffs = dmp.diff_main(self.original_code, self.updated_code)
        dmp.diff_cleanupSemantic(diffs)

        # --- Configure Tags ---
        self.text_original.tag_config("delete", background=self.ds.colors.diff.delete)
        self.text_updated.tag_config("add", background=self.ds.colors.diff.add)
        self.text_original.tag_config("placeholder", background=self.ds.colors.diff.placeholder)
        self.text_updated.tag_config("placeholder", background=self.ds.colors.diff.placeholder)
        placeholder_font = (self.ds.typography.code[0], self.ds.typography.code[1] - 1)
        self.text_original.tag_config("placeholder_text", foreground=self.ds.colors.text.secondary, justify="center", font=placeholder_font)
        self.text_updated.tag_config("placeholder_text", foreground=self.ds.colors.text.secondary, justify="center", font=placeholder_font)

        # --- 1. Build the list of chunks to display ---
        display_chunks = []
        for i, (op, data) in enumerate(diffs):
            lines = data.splitlines(True)
            if not lines: continue

            if op == dmp.DIFF_EQUAL:
                # Check if this EQUAL block is surrounded by changes or is short
                is_context = (i > 0 and diffs[i-1][0] != dmp.DIFF_EQUAL) or \
                             (i < len(diffs) - 1 and diffs[i+1][0] != dmp.DIFF_EQUAL)

                if is_context or len(lines) <= self.CONTEXT_LINES * 2:
                    display_chunks.append((op, data)) # Show the whole chunk
                else:
                    # Collapse this large block
                    display_chunks.append((dmp.DIFF_EQUAL, "".join(lines[:self.CONTEXT_LINES])))
                    display_chunks.append(('placeholder', '...\n'))
                    display_chunks.append((dmp.DIFF_EQUAL, "".join(lines[-self.CONTEXT_LINES:])))
            else:
                display_chunks.append((op, data))

        # --- 2. Insert content and apply tags based on the generated chunks ---
        original_line_idx = 1
        updated_line_idx = 1
        for op, data in display_chunks:
            num_lines = data.count('\n')
            
            if op == dmp.DIFF_EQUAL:
                self.text_original.insert("end", data)
                self.text_updated.insert("end", data)
            elif op == dmp.DIFF_DELETE:
                self.text_original.insert("end", data, ("delete",))
                self.text_updated.insert("end", "\n" * num_lines, ("placeholder",))
            elif op == dmp.DIFF_INSERT:
                self.text_original.insert("end", "\n" * num_lines, ("placeholder",))
                self.text_updated.insert("end", data, ("add",))
            elif op == 'placeholder':
                self.text_original.insert("end", data, ("placeholder_text",))
                self.text_updated.insert("end", data, ("placeholder_text",))

        # --- 3. Finalize UI State ---
        self.text_original.configure(state="disabled")
        self.text_updated.configure(state="disabled")

        # Apply syntax highlighting to the now-visible text
        self.highlighter_original.highlight(file_path=self.file_path, code=self.text_original.get("1.0", "end-1c"))
        self.highlighter_updated.highlight(file_path=self.file_path, code=self.text_updated.get("1.0", "end-1c"))
        
        self.after(50, self.linenum_original.redraw)
        self.after(50, self.linenum_updated.redraw)

    def _update_stats(self) -> None:
        """Updates the addition/deletion counters."""
        additions, deletions = self._count_changes()
        if hasattr(self, 'add_label') and self.add_label.winfo_exists():
            self.add_label.configure(text=f"➕ {additions} additions")
            self.del_label.configure(text=f"➖ {deletions} deletions")

    def append_stream_chunk(self, chunk: str) -> None:
        """Appends a new chunk of generated code and schedules a diff refresh."""
        self.updated_code += chunk
        if not getattr(self, '_diff_scheduled', False):
            self._diff_scheduled = True
            self.after(250, self._perform_scheduled_diff)

    def finish_stream(self) -> None:
        """Called when streaming finishes to trigger a final diff calculation."""
        if getattr(self, '_diff_scheduled', False):
            # perform final instantly
            self.after_cancel(self._diff_scheduled)
            self._diff_scheduled = False
        self._display_diff()
        self._update_stats()
        self.accept_btn.configure(state="normal")
        self.app.update_status("Merge complete.")

    def _perform_scheduled_diff(self) -> None:
        self._diff_scheduled = False
        self._display_diff()
        self._update_stats()
    
    def _analyze_changes(self) -> None:
        """Starts the AI analysis of the code changes in a separate thread."""
        if not self.gemini_handler or not self.gemini_handler.is_configured(): self.show_toast("Model not configured", "error"); return
        self.spinner = ButtonSpinner(self.analyze_btn); self.spinner.start()
        threading.Thread(target=self._run_analysis, daemon=True).start()
    
    def _run_analysis(self) -> None:
        """Worker thread that calls the Gemini API for analysis."""
        try:
            if self.winfo_exists():
                self.after(0, self._prepare_analysis_text)
                
            def stream_cb(chunk: str):
                if self.winfo_exists():
                    self.after(0, lambda: self._append_analysis_chunk(chunk))
                    
            self.gemini_handler.analyze_code_changes(self.original_code, self.updated_code, stream_callback=stream_cb)
            
        except Exception as e:
            if self.winfo_exists(): # Check if window is still open
                self.after(0, lambda: self._append_analysis_chunk(f"\nError: {e}"))
        finally:
            if self.winfo_exists() and self.spinner: # Check if window is still open
                self.after(0, lambda: self.spinner.stop("normal"))
    
    def _prepare_analysis_text(self) -> None:
        """Prepares the explanation text box for streaming."""
        self.explanation_text.configure(state="normal")
        self.explanation_text.delete("1.0", "end")
        self.explanation_text.configure(state="disabled")

    def _append_analysis_chunk(self, chunk: str) -> None:
        """Appends a chunk of streaming text to the explanation text box."""
        self.explanation_text.configure(state="normal")
        self.explanation_text.insert("end", chunk)
        self.explanation_text.see("end")
        self.explanation_text.configure(state="disabled")
    
    def _accept_changes(self) -> None:
        """Handles the 'Accept & Save' button click."""
        if self.save_callback: self.save_callback(self.updated_code)
        self.close_dialog()

class PillButton(ctk.CTkButton):
    """A small button styled like a pill/tag, used for context files, with a dismiss icon."""
    def __init__(self, master: Any, ds: DS, text: str, **kwargs: Any):
        super().__init__(master, 
                         text=f"{text}  ✕",
                         font=("Segoe UI", 11),
                         fg_color=ds.colors.secondary,
                         hover_color=ds.colors.danger,
                         corner_radius=12,
                         height=24,
                         **kwargs)

class SearchableComboBox(ctk.CTkFrame):
    """A fully custom searchable dropdown widget.
    
    Built from scratch using CTkEntry + a floating Toplevel list.
    - Type to filter the dropdown values live.
    - The dropdown auto-opens when you start typing.
    - Click an item to select it.
    - Click outside or press Escape to close.
    """
    
    def __init__(self, master: Any, values: List[str] = None, width: int = 200, **kwargs: Any):
        # Remove keys that CTkFrame doesn't understand but CTkComboBox did
        kwargs.pop("state", None)
        self._command = kwargs.pop("command", None)
        
        super().__init__(master, fg_color="transparent", width=width, **kwargs)
        
        self._all_values: List[str] = list(values) if values else []
        self._filtered_values: List[str] = list(self._all_values)
        self._dropdown_open = False
        self._dropdown_window: Optional[ctk.CTkToplevel] = None
        self._item_buttons: List[ctk.CTkButton] = []
        
        # --- Entry + Arrow Button ---
        self.grid_columnconfigure(0, weight=1)
        
        self._entry = ctk.CTkEntry(self, width=width - 30)
        self._entry.grid(row=0, column=0, sticky="ew")
        
        self._arrow_btn = ctk.CTkButton(
            self, text="▾", width=28, height=28,
            fg_color="transparent", hover_color=("gray75", "gray30"),
            command=self._toggle_dropdown
        )
        self._arrow_btn.grid(row=0, column=1, padx=(2, 0))
        
        # --- Bindings ---
        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Escape>", lambda e: self._close_dropdown())
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<Down>", self._on_arrow_down)
    
    # ---- Public API (compatible with CTkComboBox) ----
    
    def get(self) -> str:
        """Returns the current text in the entry."""
        return self._entry.get()
    
    def set(self, value: str) -> None:
        """Sets the entry text."""
        self._entry.delete(0, "end")
        self._entry.insert(0, value)
    
    def configure(self, **kwargs):
        """Accepts 'values' kwarg for compatibility with CTkComboBox API."""
        if "values" in kwargs:
            new_vals = kwargs.pop("values")
            if new_vals != ["No match"]:
                self._all_values = list(new_vals) if new_vals else []
                self._filtered_values = list(self._all_values)
        if "state" in kwargs:
            state = kwargs.pop("state")
            self._entry.configure(state=state)
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if kwargs:
            super().configure(**kwargs)
    
    def cget(self, key: str):
        if key == "values":
            return self._all_values
        return super().cget(key)

    # ---- Internal logic ----
    
    def _on_key_release(self, event=None) -> None:
        """Filters values and opens the dropdown as the user types."""
        if event and event.keysym in (
            "Shift_L", "Shift_R", "Control_L", "Control_R",
            "Alt_L", "Alt_R", "Caps_Lock", "Tab",
            "Up", "Down", "Left", "Right", "Escape",
            "Return", "KP_Enter"
        ):
            return
        
        typed = self.get().strip().lower()
        if not typed:
            self._filtered_values = list(self._all_values)
        else:
            self._filtered_values = [v for v in self._all_values if typed in v.lower()]
        
        # Auto-open while typing
        if self._all_values:
            self._open_dropdown()
        elif self._dropdown_open:
            self._close_dropdown()
    
    def _on_enter(self, event=None) -> None:
        """Selects the first filtered item on Enter."""
        if self._filtered_values and self._filtered_values[0] != "No match":
            val = self._filtered_values[0]
            self.set(val)
        else:
            val = self.get()
        self._close_dropdown()
        if self._command:
            self._command(val)
    
    def _on_arrow_down(self, event=None) -> None:
        """Focuses the first item in the dropdown."""
        if not self._dropdown_open:
            self._open_dropdown()
        if self._item_buttons:
            self._item_buttons[0].focus_set()
    
    def _on_focus_out(self, event=None) -> None:
        """Closes dropdown after a short delay (allows click on dropdown items)."""
        self.after(150, self._check_focus_and_close)
    
    def _check_focus_and_close(self) -> None:
        """Only close if focus has truly left the widget and its dropdown."""
        try:
            focused = self.focus_get()
            # If focus is on the dropdown window or its children, don't close
            if self._dropdown_window and focused:
                try:
                    # Check if focused widget is a child of the dropdown
                    focused_str = str(focused)
                    dropdown_str = str(self._dropdown_window)
                    if focused_str.startswith(dropdown_str):
                        return
                except Exception:
                    pass
            # If focus is on the entry itself, don't close
            if focused == self._entry:
                return
        except KeyError:
            pass  # focus_get can raise if the widget was destroyed
        
        self._close_dropdown()
    
    def _toggle_dropdown(self) -> None:
        """Toggles the dropdown open/closed."""
        if self._dropdown_open:
            self._close_dropdown()
        else:
            self._filtered_values = list(self._all_values)
            self._open_dropdown()
    
    def _open_dropdown(self) -> None:
        """Creates and shows the floating dropdown list."""
        if self._dropdown_open and self._dropdown_window:
            # Just refresh content
            self._populate_dropdown()
            return
        
        self._close_dropdown()  # Clean up any stale window
        
        if not self._filtered_values:
            return
        
        self._dropdown_window = ctk.CTkToplevel(self)
        self._dropdown_window.overrideredirect(True)
        self._dropdown_window.attributes("-topmost", True)
        
        # Position below the entry
        self.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height() + 2
        entry_width = self._entry.winfo_width() + self._arrow_btn.winfo_width()
        
        # Scrollable frame for items
        max_visible = min(len(self._filtered_values), 8)
        item_height = 30
        dropdown_height = max_visible * item_height + 10
        
        self._dropdown_window.geometry(f"{entry_width}x{dropdown_height}+{x}+{y}")
        
        self._scroll_frame = ctk.CTkScrollableFrame(
            self._dropdown_window, 
            fg_color=("gray92", "gray17"),
            corner_radius=6
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=1, pady=1)
        self._scroll_frame.grid_columnconfigure(0, weight=1)
        
        self._dropdown_open = True
        self._populate_dropdown()
    
    def _populate_dropdown(self) -> None:
        """Fills the dropdown with filtered values."""
        if not self._dropdown_window or not hasattr(self, '_scroll_frame'):
            return
        
        # Clear old buttons
        for btn in self._item_buttons:
            btn.destroy()
        self._item_buttons.clear()
        
        items = self._filtered_values if self._filtered_values else ["No match"]
        
        for i, val in enumerate(items):
            btn = ctk.CTkButton(
                self._scroll_frame,
                text=val,
                anchor="w",
                height=28,
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                text_color=("gray10", "gray90"),
                corner_radius=4,
                command=lambda v=val: self._select_item(v)
            )
            btn.grid(row=i, column=0, sticky="ew", padx=2, pady=1)
            self._item_buttons.append(btn)
    
    def _select_item(self, value: str) -> None:
        """Handles selecting an item from the dropdown."""
        if value == "No match":
            return
        self.set(value)
        self._close_dropdown()
        if self._command:
            self._command(value)
    
    def _close_dropdown(self) -> None:
        """Destroys the dropdown window."""
        if self._dropdown_window:
            try:
                self._dropdown_window.destroy()
            except Exception:
                pass
            self._dropdown_window = None
        self._item_buttons.clear()
        self._dropdown_open = False

class CollapsibleFrame(ctk.CTkFrame):
    """A collapsible frame with a title button, used for displaying categorized results."""
    def __init__(self, master: Any, ds: DS, title: str, **kwargs: Any):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.ds = ds
        self.grid_columnconfigure(0, weight=1)
        self._is_expanded = False
        self._title = title
        self._item_count = 0

        self.title_button = ctk.CTkButton(self, text=f"▶ {self._title} (0)", command=self._toggle,
                                          font=ds.typography.body_bold, anchor="w",
                                          fg_color=ds.colors.surface.section,
                                          hover_color=ds.colors.surface.card)
        self.title_button.grid(row=0, column=0, sticky="ew")

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        # content_frame is not gridded initially

    def _toggle(self) -> None:
        """Toggles the visibility of the content frame."""
        if self._is_expanded:
            self.content_frame.grid_forget()
            self.title_button.configure(text=f"▶ {self._title} ({self._item_count})")
        else:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=(self.ds.spacing.l, 0), pady=self.ds.spacing.s)
            self.title_button.configure(text=f"▼ {self._title} ({self._item_count})")
        self._is_expanded = not self._is_expanded

    def update_widgets(self, items: List[str]) -> None:
        """Clears and repopulates the content frame with a list of items."""
        self._item_count = len(items)
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        for item in items:
            label = ctk.CTkLabel(self.content_frame, text=item, font=self.ds.typography.code)
            label.pack(anchor="w", fill="x", padx=self.ds.spacing.m, pady=(0, self.ds.spacing.s))
        
        prefix = "▼" if self._is_expanded else "▶"
        self.title_button.configure(text=f"{prefix} {self._title} ({self._item_count})")
        # If there are items, make the button active and optionally expand it
        if items:
            self.title_button.configure(state="normal")
        else:
            self.title_button.configure(state="disabled")
