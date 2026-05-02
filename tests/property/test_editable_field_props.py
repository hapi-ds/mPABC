"""Property-based tests for EditableField component.

Feature: bc-improvements
Validates: Requirements 10.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from business_coach.gui.editable_field import EditableField, FieldState


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Generate a random non-empty printable string for initial values
_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        whitelist_characters=" /-_:.\n",
    ),
    min_size=1,
    max_size=200,
)

# Generate a random string (including empty) for programmatic set attempts
_any_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        whitelist_characters=" /-_:.\n",
    ),
    min_size=0,
    max_size=200,
)


# ---------------------------------------------------------------------------
# Property 11: Frozen field rejects programmatic changes
# Feature: bc-improvements, Property 11: Frozen field rejects programmatic changes
# ---------------------------------------------------------------------------


class TestFrozenFieldRejectsProgrammaticChanges:
    """Property 11: Frozen field rejects programmatic changes.

    For any EditableField instance in the FROZEN state and for any string
    value, attempting to set the field's value programmatically SHALL leave
    the field's value unchanged (equal to the value it had before the set
    attempt).

    **Validates: Requirements 10.4**
    """

    @given(initial_value=_safe_text, new_value=_any_text)
    @settings(max_examples=100)
    def test_frozen_field_rejects_value_setter(
        self,
        initial_value: str,
        new_value: str,
    ) -> None:
        """For any frozen EditableField and any string, setting .value leaves value unchanged."""
        # Create an EditableField in FROZEN state with an initial value
        field = EditableField(value=initial_value, is_frozen=True)

        # Verify the field is indeed in FROZEN state
        assert field.state == FieldState.FROZEN

        # Attempt to set the value programmatically
        field.value = new_value

        # Assert the value remains unchanged (equal to the initial value)
        assert field.value == initial_value
