"""Unit tests for EditableField state transitions.

Tests the VIEW/EDIT/FROZEN state machine without requiring NiceGUI to be running.
State transitions are tested by calling internal methods and checking field.state.

Requirements: 9.1–9.5, 10.1–10.5, 11.1–11.5
"""

from unittest.mock import MagicMock

import pytest

from business_coach.gui.editable_field import EditableField, FieldState


class TestViewToEditTransition:
    """Test VIEW → EDIT transition (Edit click changes state).

    Requirements: 9.1, 9.2
    """

    def test_initial_state_is_view(self) -> None:
        field = EditableField(value="hello")
        assert field.state == FieldState.VIEW

    def test_edit_click_transitions_to_edit(self) -> None:
        field = EditableField(value="hello")
        field._on_edit_click()
        assert field.state == FieldState.EDIT

    def test_edit_click_preserves_value(self) -> None:
        field = EditableField(value="my content")
        field._on_edit_click()
        assert field._value == "my content"

    def test_edit_click_from_non_view_state_is_noop(self) -> None:
        field = EditableField(value="hello", is_frozen=True)
        field._on_edit_click()
        assert field.state == FieldState.FROZEN


class TestEditToViewTransition:
    """Test EDIT → VIEW transition persists content.

    Requirements: 9.3, 9.4, 9.5
    """

    def test_save_click_transitions_to_view(self) -> None:
        field = EditableField(value="original")
        field._on_edit_click()
        assert field.state == FieldState.EDIT
        field._on_save_click()
        assert field.state == FieldState.VIEW

    def test_save_click_persists_value(self) -> None:
        field = EditableField(value="original")
        field._on_edit_click()
        # Simulate editing by changing _value directly (no UI refs in test)
        field._value = "updated content"
        field._on_save_click()
        assert field._value == "updated content"
        assert field.state == FieldState.VIEW

    def test_save_click_calls_on_save_callback(self) -> None:
        on_save = MagicMock()
        field = EditableField(value="content", on_save=on_save)
        field._on_edit_click()
        field._on_save_click()
        on_save.assert_called_once_with("content")

    def test_save_click_from_non_edit_state_is_noop(self) -> None:
        field = EditableField(value="hello")
        assert field.state == FieldState.VIEW
        field._on_save_click()
        assert field.state == FieldState.VIEW


class TestViewToFrozenTransition:
    """Test VIEW → FROZEN hides Edit/Save buttons (state changes to FROZEN).

    Requirements: 10.1, 10.2, 10.3
    """

    def test_freeze_toggle_on_transitions_to_frozen(self) -> None:
        field = EditableField(value="hello")
        assert field.state == FieldState.VIEW
        field._on_freeze_toggle(True)
        assert field.state == FieldState.FROZEN

    def test_frozen_state_rejects_value_setter(self) -> None:
        field = EditableField(value="original")
        field._on_freeze_toggle(True)
        assert field.state == FieldState.FROZEN
        field.value = "attempted change"
        assert field._value == "original"

    def test_freeze_toggle_calls_on_freeze_callback(self) -> None:
        on_freeze = MagicMock()
        field = EditableField(value="hello", on_freeze=on_freeze)
        field._on_freeze_toggle(True)
        on_freeze.assert_called_once_with(True)

    def test_is_frozen_property_true_when_frozen(self) -> None:
        field = EditableField(value="hello")
        field._on_freeze_toggle(True)
        assert field.is_frozen is True


class TestFrozenToViewTransition:
    """Test FROZEN → VIEW restores Edit button (state changes to VIEW).

    Requirements: 10.5
    """

    def test_freeze_toggle_off_transitions_to_view(self) -> None:
        field = EditableField(value="hello", is_frozen=True)
        assert field.state == FieldState.FROZEN
        field._on_freeze_toggle(False)
        assert field.state == FieldState.VIEW

    def test_unfreeze_allows_value_setter(self) -> None:
        field = EditableField(value="original", is_frozen=True)
        assert field.state == FieldState.FROZEN
        field._on_freeze_toggle(False)
        field.value = "new value"
        assert field._value == "new value"

    def test_unfreeze_calls_on_freeze_callback_with_false(self) -> None:
        on_freeze = MagicMock()
        field = EditableField(value="hello", on_freeze=on_freeze, is_frozen=True)
        field._on_freeze_toggle(False)
        on_freeze.assert_called_once_with(False)

    def test_is_frozen_property_false_after_unfreeze(self) -> None:
        field = EditableField(value="hello", is_frozen=True)
        field._on_freeze_toggle(False)
        assert field.is_frozen is False


class TestEditToFrozenTransition:
    """Test EDIT → FROZEN auto-saves before freezing.

    Requirements: 10.1, 10.2
    """

    def test_freeze_from_edit_transitions_to_frozen(self) -> None:
        field = EditableField(value="original")
        field._on_edit_click()
        assert field.state == FieldState.EDIT
        field._on_freeze_toggle(True)
        assert field.state == FieldState.FROZEN

    def test_freeze_from_edit_auto_saves_value(self) -> None:
        on_save = MagicMock()
        field = EditableField(value="original", on_save=on_save)
        field._on_edit_click()
        # Simulate user editing the value
        field._value = "edited content"
        field._on_freeze_toggle(True)
        on_save.assert_called_once_with("edited content")

    def test_freeze_from_edit_calls_both_callbacks(self) -> None:
        on_save = MagicMock()
        on_freeze = MagicMock()
        field = EditableField(value="content", on_save=on_save, on_freeze=on_freeze)
        field._on_edit_click()
        field._on_freeze_toggle(True)
        on_save.assert_called_once_with("content")
        on_freeze.assert_called_once_with(True)


class TestFeedbackFieldAlwaysEditable:
    """Test feedback field is always editable regardless of main field state.

    Requirements: 11.1, 11.2
    """

    def test_feedback_value_settable_in_view_state(self) -> None:
        field = EditableField(value="main", show_feedback=True)
        assert field.state == FieldState.VIEW
        field.feedback_value = "my feedback"
        assert field.feedback_value == "my feedback"

    def test_feedback_value_settable_in_edit_state(self) -> None:
        field = EditableField(value="main", show_feedback=True)
        field._on_edit_click()
        assert field.state == FieldState.EDIT
        field.feedback_value = "feedback in edit"
        assert field.feedback_value == "feedback in edit"

    def test_feedback_value_settable_in_frozen_state(self) -> None:
        field = EditableField(value="main", show_feedback=True, is_frozen=True)
        assert field.state == FieldState.FROZEN
        field.feedback_value = "feedback while frozen"
        assert field.feedback_value == "feedback while frozen"

    def test_feedback_has_no_freeze_toggle(self) -> None:
        """Feedback field is always editable — no freeze behavior applies to it."""
        field = EditableField(value="main", show_feedback=True, is_frozen=True)
        # Main field rejects changes when frozen
        field.value = "rejected"
        assert field._value == "main"
        # Feedback field still accepts changes
        field.feedback_value = "accepted"
        assert field._feedback_value == "accepted"


class TestRedoButton:
    """Test Redo button passes content + feedback to on_redo callback.

    Requirements: 11.3, 11.4, 11.5
    """

    def test_redo_click_calls_on_redo_with_content_and_feedback(self) -> None:
        on_redo = MagicMock()
        field = EditableField(value="main content", on_redo=on_redo, show_feedback=True)
        field.feedback_value = "please improve"
        field._on_redo_click()
        on_redo.assert_called_once_with("main content", "please improve")

    def test_redo_click_with_empty_feedback(self) -> None:
        on_redo = MagicMock()
        field = EditableField(value="content", on_redo=on_redo, show_feedback=True)
        field._on_redo_click()
        on_redo.assert_called_once_with("content", "")

    def test_redo_click_without_callback_is_noop(self) -> None:
        field = EditableField(value="content", on_redo=None, show_feedback=True)
        # Should not raise
        field._on_redo_click()

    def test_redo_click_with_callback_exception_does_not_propagate(self) -> None:
        on_redo = MagicMock(side_effect=RuntimeError("callback error"))
        field = EditableField(value="content", on_redo=on_redo, show_feedback=True)
        field.feedback_value = "feedback"
        # Should not raise — exception is caught internally
        field._on_redo_click()
        on_redo.assert_called_once_with("content", "feedback")
