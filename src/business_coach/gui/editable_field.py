"""Editable field component with VIEW/EDIT/FROZEN state machine.

Provides a unified interface for editable fields with:
- VIEW state: rendered markdown + Edit button + Freeze toggle
- EDIT state: textarea + Save button + Freeze toggle
- FROZEN state: rendered markdown only, no buttons

Includes a dedicated FeedbackField (always-editable textarea without freeze toggle)
and a Redo button that passes (content, feedback) to a callback.
"""

from __future__ import annotations

import enum
import logging
from typing import Any, Callable, Optional

from nicegui import ui

logger = logging.getLogger(__name__)


class FieldState(enum.Enum):
    """State machine states for EditableField."""

    VIEW = "view"
    EDIT = "edit"
    FROZEN = "frozen"


class EditableField:
    """Editable field with markdown view/edit toggle and freeze behavior.

    States:
        VIEW: Rendered markdown display + Edit button + Freeze toggle
        EDIT: Textarea + Save button + Freeze toggle
        FROZEN: Rendered markdown display only (no Edit/Save/Redo buttons)

    State transitions:
        VIEW → EDIT (Edit click)
        EDIT → VIEW (Save click)
        VIEW → FROZEN (Freeze on)
        FROZEN → VIEW (Freeze off)
        EDIT → FROZEN (auto-save then freeze)

    Args:
        value: Initial value of the main content field.
        label: Label displayed above the field.
        on_save: Optional callback when content is saved, receives the content string.
        on_freeze: Optional callback when freeze state changes, receives bool (is_frozen).
        on_redo: Optional callback for redo action, receives (content, feedback).
        is_frozen: Whether the field starts in FROZEN state.
        show_feedback: Whether to show the feedback textarea.
        rows: Number of rows for the main textarea in EDIT mode.
    """

    def __init__(
        self,
        value: str = "",
        label: str = "Content",
        on_save: Callable[[str], None] | None = None,
        on_freeze: Callable[[bool], None] | None = None,
        on_redo: Callable[[str, str], None] | None = None,
        is_frozen: bool = False,
        show_feedback: bool = True,
        rows: int = 6,
    ):
        self._value = value
        self._feedback_value = ""
        self.label = label
        self.on_save = on_save
        self.on_freeze = on_freeze
        self.on_redo = on_redo
        self.show_feedback = show_feedback
        self.rows = rows

        # Determine initial state
        if is_frozen:
            self._state = FieldState.FROZEN
        else:
            self._state = FieldState.VIEW

        # UI element references
        self._container: Optional[Any] = None
        self._editor_ref: Optional[ui.textarea] = None
        self._display_ref: Optional[ui.markdown] = None
        self._feedback_ref: Optional[ui.textarea] = None
        self._freeze_toggle_ref: Optional[ui.switch] = None

    @property
    def state(self) -> FieldState:
        """Get the current state of the field."""
        return self._state

    @property
    def is_frozen(self) -> bool:
        """Whether the field is currently in FROZEN state."""
        return self._state == FieldState.FROZEN

    @property
    def value(self) -> str:
        """Get current value of the main content field."""
        if self._state == FieldState.EDIT and self._editor_ref is not None:
            return self._editor_ref.value or ""
        return self._value

    @value.setter
    def value(self, new_value: str) -> None:
        """Set new value for the main content field.

        If the field is in FROZEN state, the change is rejected silently.
        This prevents programmatic changes from AI generation workflows.
        """
        if self._state == FieldState.FROZEN:
            logger.debug("Rejected programmatic value change: field is FROZEN")
            return

        self._value = new_value
        if self._editor_ref is not None:
            self._editor_ref.value = new_value
        if self._display_ref is not None:
            self._display_ref.set_content(new_value)

    @property
    def feedback_value(self) -> str:
        """Get current value of the feedback field."""
        if self._feedback_ref is not None:
            return self._feedback_ref.value or ""
        return self._feedback_value

    @feedback_value.setter
    def feedback_value(self, new_value: str) -> None:
        """Set new value for the feedback field."""
        self._feedback_value = new_value
        if self._feedback_ref is not None:
            self._feedback_ref.value = new_value

    def _transition_to(self, new_state: FieldState) -> None:
        """Execute a state transition and rebuild the UI."""
        old_state = self._state
        logger.debug(f"State transition: {old_state.value} → {new_state.value}")

        # Capture current editor value before transition if leaving EDIT
        if old_state == FieldState.EDIT and self._editor_ref is not None:
            self._value = self._editor_ref.value or ""

        # Capture feedback value before rebuild
        if self._feedback_ref is not None:
            self._feedback_value = self._feedback_ref.value or ""

        self._state = new_state
        self._rebuild_ui()

    def _on_edit_click(self) -> None:
        """Handle Edit button click: VIEW → EDIT."""
        if self._state == FieldState.VIEW:
            self._transition_to(FieldState.EDIT)

    def _on_save_click(self) -> None:
        """Handle Save button click: EDIT → VIEW."""
        if self._state == FieldState.EDIT:
            # Capture value from editor
            if self._editor_ref is not None:
                self._value = self._editor_ref.value or ""

            # Notify save callback
            if self.on_save:
                try:
                    self.on_save(self._value)
                except Exception as e:
                    logger.exception("on_save callback failed")

            self._transition_to(FieldState.VIEW)

    def _on_freeze_toggle(self, is_frozen: bool) -> None:
        """Handle Freeze toggle change.

        Transitions:
            VIEW → FROZEN (freeze on)
            EDIT → FROZEN (auto-save then freeze)
            FROZEN → VIEW (freeze off)
        """
        if is_frozen:
            if self._state == FieldState.EDIT:
                # Auto-save before freezing
                if self._editor_ref is not None:
                    self._value = self._editor_ref.value or ""
                if self.on_save:
                    try:
                        self.on_save(self._value)
                    except Exception as e:
                        logger.exception("on_save callback failed during auto-save before freeze")

            # Notify freeze callback
            if self.on_freeze:
                try:
                    self.on_freeze(True)
                except Exception as e:
                    logger.exception("on_freeze callback failed")

            self._transition_to(FieldState.FROZEN)
        else:
            # Unfreeze: FROZEN → VIEW
            if self.on_freeze:
                try:
                    self.on_freeze(False)
                except Exception as e:
                    logger.exception("on_freeze callback failed")

            self._transition_to(FieldState.VIEW)

    def _on_redo_click(self) -> None:
        """Handle Redo button click: pass content + feedback to on_redo callback."""
        if self.on_redo:
            content = self.value
            feedback = self.feedback_value
            try:
                self.on_redo(content, feedback)
            except Exception as e:
                logger.exception("on_redo callback failed")

    def save(self) -> None:
        """Programmatic save — triggers the same logic as Save button click."""
        if self._state == FieldState.FROZEN:
            return
        if self._state == FieldState.EDIT:
            self._on_save_click()
        else:
            # In VIEW state, just call the save callback with current value
            if self.on_save:
                try:
                    self.on_save(self._value)
                except Exception as e:
                    logger.exception("on_save callback failed")

    def _rebuild_ui(self) -> None:
        """Clear the container and rebuild UI based on current state."""
        if self._container is None:
            return

        # Clear refs
        self._editor_ref = None
        self._display_ref = None
        self._feedback_ref = None
        self._freeze_toggle_ref = None

        self._container.clear()
        with self._container:
            self._build_main_field()
            if self.show_feedback:
                self._build_feedback_field()
                self._build_redo_button()

    def _build_main_field(self) -> None:
        """Build the main content field based on current state."""
        if self._state == FieldState.VIEW:
            self._build_view_state()
        elif self._state == FieldState.EDIT:
            self._build_edit_state()
        elif self._state == FieldState.FROZEN:
            self._build_frozen_state()

    def _build_view_state(self) -> None:
        """Build VIEW state: rendered markdown + Edit button + Freeze toggle."""
        ui.label(self.label).classes("text-subtitle2 font-semibold q-mb-xs")
        self._display_ref = ui.markdown(self._value).classes(
            "w-full p-4 bg-grey-1 rounded border"
        )
        with ui.row().classes("w-full items-center justify-between q-mt-sm"):
            self._freeze_toggle_ref = ui.switch(
                "Freeze", value=False
            ).props("color=warning")
            self._freeze_toggle_ref.on_value_change(
                lambda e: self._on_freeze_toggle(e.value)
            )
            ui.button("Edit", icon="edit", on_click=self._on_edit_click).props(
                "color=secondary"
            )

    def _build_edit_state(self) -> None:
        """Build EDIT state: textarea + Save button + Freeze toggle."""
        ui.label(self.label).classes("text-subtitle2 font-semibold q-mb-xs")
        self._editor_ref = ui.textarea(
            value=self._value,
            label="Edit content",
        ).classes("w-full").props(f"outlined autogrow rows={max(self.rows, 12)}")

        with ui.row().classes("w-full items-center justify-between q-mt-sm"):
            self._freeze_toggle_ref = ui.switch(
                "Freeze", value=False
            ).props("color=warning")
            self._freeze_toggle_ref.on_value_change(
                lambda e: self._on_freeze_toggle(e.value)
            )
            ui.button("Save", icon="save", on_click=self._on_save_click).props(
                "color=primary"
            )

    def _build_frozen_state(self) -> None:
        """Build FROZEN state: rendered markdown only, no buttons."""
        ui.label(self.label).classes("text-subtitle2 font-semibold q-mb-xs")
        self._display_ref = ui.markdown(self._value).classes(
            "w-full p-4 bg-blue-grey-1 rounded border"
        )
        # Frozen indicator with unfreeze toggle
        with ui.row().classes("w-full items-center q-mt-sm"):
            self._freeze_toggle_ref = ui.switch(
                "Freeze", value=True
            ).props("color=warning")
            self._freeze_toggle_ref.on_value_change(
                lambda e: self._on_freeze_toggle(e.value)
            )

    def _build_feedback_field(self) -> None:
        """Build the always-editable feedback textarea (no freeze toggle)."""
        ui.label("Feedback / Review Notes").classes(
            "text-subtitle2 font-semibold q-mt-md q-mb-xs"
        )
        self._feedback_ref = ui.textarea(
            value=self._feedback_value,
            label="Enter feedback for redo...",
        ).classes("w-full").props("outlined rows=2")

    def _build_redo_button(self) -> None:
        """Build the Redo button (hidden when frozen)."""
        if self._state != FieldState.FROZEN:
            with ui.row().classes("w-full justify-end q-mt-sm"):
                ui.button(
                    "Redo", icon="refresh", on_click=self._on_redo_click
                ).props("color=accent")

    def render(self, container: Any) -> "EditableField":
        """Render the field in the given container and return self for chaining.

        Args:
            container: A NiceGUI container element (e.g., ui.column()).

        Returns:
            Self for method chaining.
        """
        self._container = container

        with container:
            if hasattr(container, "clear"):
                container.clear()
            self._build_main_field()
            if self.show_feedback:
                self._build_feedback_field()
                self._build_redo_button()

        return self


def create_editable_field(
    value: str = "",
    label: str = "Content",
    readonly_label: str = "Read-only content",
    on_change: Optional[Callable[[str], None]] = None,
    on_save: Optional[Callable[[str], None]] = None,
    on_freeze: Optional[Callable[[bool], None]] = None,
    on_redo: Optional[Callable[[str, str], None]] = None,
    is_frozen: bool = False,
    show_feedback: bool = False,
    rows: int = 6,
) -> EditableField:
    """Backward-compatible factory function to create an EditableField.

    This function preserves the old API signature so existing panel code
    continues to work until updated in Task 6.

    Args:
        value: Initial value.
        label: Label for the field.
        readonly_label: Ignored (kept for backward compatibility).
        on_change: Ignored (kept for backward compatibility).
        on_save: Callback when saved.
        on_freeze: Callback when freeze state changes (receives bool: is_frozen).
        on_redo: Callback for redo action (content, feedback) -> None.
        is_frozen: Start in frozen state.
        show_feedback: Whether to show feedback field (default False for backward compat).
        rows: Textarea rows.

    Returns:
        Configured EditableField instance.
    """
    field = EditableField(
        value=value,
        label=label,
        on_save=on_save,
        on_freeze=on_freeze,
        on_redo=on_redo,
        is_frozen=is_frozen,
        show_feedback=show_feedback,
        rows=rows,
    )
    return field
