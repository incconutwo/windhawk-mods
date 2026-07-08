import customtkinter as ctk
from typing import Any, Optional

# =============================================================================
# --- DATA CLASSES FOR DESIGN SYSTEM ---
# =============================================================================

class ColorPalette:
    """Holds the color values for a specific theme (light or dark)."""
    def __init__(self, mode: str = 'dark'):
        if mode == 'dark':
            self.primary = "#3671FE"
            self.primary_hover = "#2C5ADF"
            self.success = "#28A745"
            self.success_hover = "#218838"
            self.warning = "#FFC107"
            self.warning_hover = "#E0A800"
            self.danger = "#DC3545"
            self.danger_hover = "#C82333"
            self.secondary = "#6C757D"
            self.secondary_hover = "#5A6268"
            
            self.surface = type('Surface', (), {'base': '#242424', 'section': '#2B2B2B', 'card': '#333333'})()
            self.text = type('Text', (), {'primary': '#F5F5F5', 'secondary': '#AAAAAA', 'on_primary': '#FFFFFF'})()
            self.border = "#444444"
            
            self.diff = type('Diff', (), {'add': '#143d14', 'delete': '#3d1414', 'placeholder': '#2e2e2e'})()
        else: # light
            self.primary = "#3671FE"
            self.primary_hover = "#2C5ADF"
            self.success = "#28A745"
            self.success_hover = "#218838"
            self.warning = "#FFC107"
            self.warning_hover = "#E0A800"
            self.danger = "#DC3545"
            self.danger_hover = "#C82333"
            self.secondary = "#6C757D"
            self.secondary_hover = "#5A6268"

            self.surface = type('Surface', (), {'base': '#E9ECEF', 'section': '#FFFFFF', 'card': '#FFFFFF'})()
            self.text = type('Text', (), {'primary': '#212121', 'secondary': '#616161', 'on_primary': '#FFFFFF'})()
            self.border = "#DEE2E6"
            
            self.diff = type('Diff', (), {'add': '#e6ffed', 'delete': '#ffebee', 'placeholder': '#f1f3f5'})()

class Typography:
    """Defines standard font styles used throughout the application."""
    h1 = ("Segoe UI", 24, "bold")
    h2 = ("Segoe UI", 16, "bold")
    body = ("Segoe UI", 13)
    body_bold = ("Segoe UI", 13, "bold")
    body_small = ("Segoe UI", 11)
    button = ("Segoe UI", 13, "bold")
    code = ("Consolas", 12)
    code_small = ("Consolas", 10)

class Spacing:
    """Defines standard spacing units for padding and margins."""
    s = 4
    m = 8
    l = 16
    xl = 24

class Animation:
    """Defines standard animation speeds."""
    speed_ms = 16 # Optimal for smooth UI animations

# =============================================================================
# --- MAIN DESIGN SYSTEM CLASS ---
# =============================================================================

class DS:
    """
    A singleton class that holds all design system values (colors, typography, etc.).
    This provides a single, consistent source for all styling in the application.
    """
    _instance = None
    
    def __new__(cls) -> 'DS':
        if cls._instance is None:
            cls._instance = super(DS, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self) -> None:
        """Initializes the design system with default values."""
        self.theme_mode: str = 'dark'
        self.colors: ColorPalette = ColorPalette(self.theme_mode)
        self.typography: Typography = Typography()
        self.spacing: Spacing = Spacing()
        self.animation: Animation = Animation()

    def set_theme(self, theme: str) -> None:
        """
        Sets the application's appearance mode and updates the color palette.

        Args:
            theme: The theme to set ('Light', 'Dark', 'System').
        """
        ctk.set_appearance_mode(theme)
        self.theme_mode = ctk.get_appearance_mode()
        self.colors = ColorPalette(self.theme_mode.lower())

# =============================================================================
# --- CUSTOM WIDGETS INCORPORATING THE DESIGN SYSTEM ---
# =============================================================================

class CardFrame(ctk.CTkFrame):
    """A pre-styled frame that acts as a card container, using styles from the Design System."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        kwargs.setdefault('fg_color', ds.colors.surface.card)
        kwargs.setdefault('border_color', ds.colors.border)
        kwargs.setdefault('border_width', 1)
        kwargs.setdefault('corner_radius', 8)
        super().__init__(master, **kwargs)

class AnimatedButton(ctk.CTkButton):
    """A CTkButton with press-and-release animation for tactile feedback."""
    def __init__(self, master: Any, **kwargs: Any):
        # Pop the command to handle it manually, preventing the default binding from firing.
        self._command = kwargs.pop('command', None)
        super().__init__(master, command=None, **kwargs)
        
        # Store the original font object AFTER the widget is initialized.
        self._original_font = self.cget("font")
        
        self.bind("<Button-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")

    def _on_press(self, event: Any) -> None:
        """On press, slightly shrink the font size for a visual effect."""
        font_obj = self.cget("font")
        original_size = font_obj.cget("size")
        self.configure(font=(font_obj.cget("family"), int(original_size * 0.95)))

    def _on_release(self, event: Any) -> None:
        """On release, restore the original font and fire the command."""
        self.configure(font=self._original_font)
        if self._command:
            self._command()

class ButtonWithHover(ctk.CTkButton):
    """A base button class that uses standard colors and styles from the Design System."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        self.ds = ds
        fg_color = kwargs.pop('fg_color', ds.colors.primary)
        hover_color = kwargs.pop('hover_color', ds.colors.primary_hover)
        text_color = kwargs.pop('text_color', ds.colors.text.on_primary)
        font = kwargs.pop('font', ds.typography.button)
        super().__init__(master, fg_color=fg_color, hover_color=hover_color, 
                         text_color=text_color, font=font, **kwargs)

# --- Button Subclasses for consistency ---
class SuccessButton(ButtonWithHover):
    """A button styled for success actions."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        super().__init__(master, ds, fg_color=ds.colors.success, hover_color=ds.colors.success_hover, **kwargs)

class DangerButton(ButtonWithHover):
    """A button styled for destructive or cancellation actions."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        super().__init__(master, ds, fg_color=ds.colors.danger, hover_color=ds.colors.danger_hover, **kwargs)

class WarningButton(ButtonWithHover):
    """A button styled for warning actions."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        super().__init__(master, ds, fg_color=ds.colors.warning, hover_color=ds.colors.warning_hover, text_color=ds.colors.text.primary, **kwargs)

class SecondaryButton(ButtonWithHover):
    """A button styled for secondary actions."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        super().__init__(master, ds, fg_color=ds.colors.secondary, hover_color=ds.colors.secondary_hover, **kwargs)

class GhostButton(ButtonWithHover):
    """A button with a transparent background that shows the primary color on hover. Great for clean UIs."""
    def __init__(self, master: Any, ds: DS, **kwargs: Any):
        text_color = kwargs.pop('text_color', ds.colors.text.primary)
        super().__init__(master, ds, fg_color="transparent", hover_color=ds.colors.surface.section, 
                         text_color=text_color, border_width=0, **kwargs)

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