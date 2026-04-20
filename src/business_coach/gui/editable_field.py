"""Editable field component with save and freeze toggle functionality.

Provides a unified interface for editable fields that can be:
- Toggled between read-only and editable modes
- Saved to database
- Marked as "frozen" to prevent further edits until unfrozen
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from nicegui import ui

logger = logging.getLogger(__name__)


class EditableField:
    """A field that can be edited, saved, and frozen.
    
    Args:
        value: Initial value of the field
        label: Label to display above the field
        readonly_label: Label to show when field is read-only (frozen)
        on_change: Optional callback when value changes
        on_save: Optional callback when save button is clicked
        is_frozen: Whether the field starts in frozen state (default False = editable initially)
        rows: Number of rows for textarea (default 6)
    
    When frozen, the field:
    - Shows as read-only markdown display with no Edit or Save buttons
    - Cannot be modified by user or LLM operations
    - Represents final content that user is satisfied with
    """
    
    def __init__(
        self,
        value: str = "",
        label: str = "Content",
        readonly_label: str = "Read-only content",
        on_change: Optional[Callable[[str], None]] = None,
        on_save: Optional[Callable[[str], None]] = None,
        is_frozen: bool = False,
        rows: int = 6,
    ):
        self._value = value
        self.label = label
        self.readonly_label = readonly_label
        self.on_change = on_change
        self.on_save = on_save
        self.is_frozen = is_frozen
        self.rows = rows
        
        self._editor_ref: Optional[ui.textarea] = None
        self._display_ref: Optional(ui.markdown) = None
        self._frozen_toggle: Optional[ui.checkbox] = None
        self._save_btn: Optional[ui.button] = None
        self._edit_btn: Optional[ui.button] = None
        
        self._container: Optional[Any] = None
        
    @property
    def value(self) -> str:
        """Get current value of the field."""
        if self._editor_ref and not self.is_frozen:
            return self._editor_ref.value
        return self._value
    
    @value.setter
    def value(self, new_value: str) -> None:
        """Set new value for the field."""
        self._value = new_value
        if self._editor_ref:
            self._editor_ref.value = new_value
        if self._display_ref:
            self._display_ref.content = new_value
    
    def toggle_freeze(self, is_frozen: bool) -> None:
        """Toggle between frozen and editable states."""
        self.is_frozen = is_frozen
        
        if not self._container:
            return
            
        # Capture current value before clearing refs when switching to editable
        if not is_frozen and self._display_ref:
            self._value = self._display_ref.content
        
        # Clear the container and rebuild
        self._editor_ref = None
        self._display_ref = None
        
        with self._container:
            self._container.clear()  # Clear existing elements in the container
            if is_frozen:
                self._build_readonly_view()
            else:
                self._build_editable_view()

    def save(self) -> None:
        """Save current value and notify."""
        # Don't allow saving when frozen
        if self.is_frozen:
            return
            
        current_value = self.value
        # Sync _value with editor's current value before rebuilding
        self._value = current_value
        
        if self.on_save:
            self.on_save(current_value)
        
        # Show notification before rebuilding (notification needs context)
        ui.notify("Changes saved", type="positive")
        
        # Rebuild as read-only view with rendered content
        if not self._container:
            return
        
        # Clear refs and rebuild read-only view
        self.is_frozen = True
        self._editor_ref = None
        self._display_ref = None
        
        with self._container:
            self._container.clear()
            self._build_readonly_view()
        
    def _build_editable_view(self) -> None:
        """Build the editable view with editor, freeze toggle, and save button."""
        # Get current value from textarea if it exists, otherwise use stored value
        current_value = self._editor_ref.value if self._editor_ref else self._value
        
        with self._container:
            ui.label(self.label).classes("text-subtitle2 font-semibold q-mb-sm")
            
            self._editor_ref = ui.textarea(
                value=current_value,
                label="Edit content",
            ).classes("w-full").props(f"outlined rows={self.rows}")
            
            if self.on_change:
                self._editor_ref.on("change", lambda e: self.on_change(e.value))
            
            with ui.row().classes("w-full items-center justify-between q-mt-sm"):
                self._frozen_toggle = ui.checkbox(
                    "Freeze (prevent changes until unchecked)",
                    value=self.is_frozen,
                ).props("color=warning")
                
                self._frozen_toggle.on(
                    "change", 
                    lambda e: self.toggle_freeze(e.value)
                )
                
                # Save button only visible when not frozen
                if not self.is_frozen:
                    self._save_btn = ui.button(
                        "Save",
                        icon="save",
                        on_click=self.save,
                    ).props("color=primary")
    
    def _build_readonly_view(self) -> None:
        """Build the read-only view with markdown display and edit toggle."""
        with self._container:
            ui.label(self.readonly_label).classes("text-subtitle2 font-semibold q-mb-sm")
            
            self._display_ref = ui.markdown(self._value).classes("w-full p-4 bg-grey-1 rounded")
            
            with ui.row().classes("w-full items-center justify-between q-mt-sm"):
                # Frozen toggle always shows True when in read-only
                self._frozen_toggle = ui.checkbox(
                    "Frozen (final state)",
                    value=True,
                ).props("color=warning disabled")
                
                # Edit button only visible when NOT frozen
                if not self.is_frozen:
                    self._edit_btn = ui.button(
                        "Edit",
                        icon="edit",
                        on_click=self._switch_to_editable,
                    ).props("color=secondary")
    
    def _switch_to_editable(self) -> None:
        """Switch from readonly to editable view."""
        self.is_frozen = False
        self.toggle_freeze(False)
    
    def render(self, container: Any) -> "EditableField":
        """Render the field in the given container and return self for chaining."""
        self._container = container
        
        with container:
            if hasattr(container, 'clear'):
                container.clear()
            
            if self.is_frozen:
                self._build_readonly_view()
            else:
                self._build_editable_view()
        
        return self


def create_editable_field(
    value: str = "",
    label: str = "Content",
    readonly_label: str = "Read-only content",
    on_change: Optional[Callable[[str], None]] = None,
    on_save: Optional[Callable[[str], None]] = None,
    is_frozen: bool = False,
    rows: int = 6,
) -> EditableField:
    """Factory function to create and render an EditableField.
    
    Args:
        value: Initial value
        label: Label for editable view
        readonly_label: Label for read-only view
        on_change: Callback when value changes
        on_save: Callback when saved
        is_frozen: Start in frozen state
        rows: Textarea rows
        
    Returns:
        Configured EditableField instance
    """
    field = EditableField(
        value=value,
        label=label,
        readonly_label=readonly_label,
        on_change=on_change,
        on_save=on_save,
        is_frozen=is_frozen,
        rows=rows,
    )
    return field
