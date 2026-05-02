"""Property-based tests for AppSettings validation and environment variable precedence.

Validates: Requirements 6.3, 6.4
"""

import os

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from business_coach.config import AppSettings

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# String settings that accept arbitrary non-empty text values
_STRING_SETTINGS: list[tuple[str, str]] = [
    ("lm_studio_base_url", "BC_LM_STUDIO_BASE_URL"),
    ("lm_studio_api_key", "BC_LM_STUDIO_API_KEY"),
    ("model_canvas", "BC_MODEL_CANVAS"),
    ("model_voices", "BC_MODEL_VOICES"),
    ("model_plan", "BC_MODEL_PLAN"),
    ("model_research", "BC_MODEL_RESEARCH"),
    ("model_chat", "BC_MODEL_CHAT"),
    ("embedding_model_name", "BC_EMBEDDING_MODEL_NAME"),
    ("log_level", "BC_LOG_LEVEL"),
]

# Generate a random non-empty printable string (no newlines/control chars)
_safe_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"), whitelist_characters=" /-_:."),
    min_size=1,
    max_size=80,
)

# Generate a random positive integer for monitoring_interval_hours
_pos_int = st.integers(min_value=1, max_value=10_000)


# ---------------------------------------------------------------------------
# Property 12: Settings validation
# Feature: bc-improvements, Property 12: Settings validation
# ---------------------------------------------------------------------------


class TestSettingsValidation:
    """Property 12: Settings validation.

    For any config dict with all required valid values, constructing
    AppSettings succeeds; for any config with an invalid type for a
    validated field, it raises ValidationError.

    **Validates: Requirements 6.3, 6.4**
    """

    @given(
        lm_studio_base_url=_safe_text,
        model_canvas=_safe_text,
        model_voices=_safe_text,
        model_plan=_safe_text,
        model_research=_safe_text,
        model_chat=_safe_text,
        embedding_model_name=_safe_text,
        log_level=_safe_text,
        monitoring_interval_hours=_pos_int,
    )
    @settings(max_examples=100)
    def test_valid_config_constructs_successfully(
        self,
        lm_studio_base_url: str,
        model_canvas: str,
        model_voices: str,
        model_plan: str,
        model_research: str,
        model_chat: str,
        embedding_model_name: str,
        log_level: str,
        monitoring_interval_hours: int,
    ) -> None:
        """For any valid values, AppSettings construction succeeds."""
        s = AppSettings(
            lm_studio_base_url=lm_studio_base_url,
            model_canvas=model_canvas,
            model_voices=model_voices,
            model_plan=model_plan,
            model_research=model_research,
            model_chat=model_chat,
            embedding_model_name=embedding_model_name,
            log_level=log_level,
            monitoring_interval_hours=monitoring_interval_hours,
        )
        assert s.lm_studio_base_url == lm_studio_base_url
        assert s.model_canvas == model_canvas
        assert s.monitoring_interval_hours == monitoring_interval_hours

    @given(bad_value=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_invalid_monitoring_interval_raises_validation_error(
        self,
        bad_value: str,
    ) -> None:
        """For any non-integer string for monitoring_interval_hours, ValidationError is raised."""
        env_key = "BC_MONITORING_INTERVAL_HOURS"
        original = os.environ.get(env_key)
        try:
            os.environ[env_key] = bad_value
            with pytest.raises(ValidationError):
                AppSettings()
        finally:
            if original is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = original


# ---------------------------------------------------------------------------
# Property 13: Environment variable precedence
# Feature: bc-improvements, Property 13: Environment variable precedence
# ---------------------------------------------------------------------------


class TestEnvVarPrecedence:
    """Property 13: Environment variable precedence.

    For any setting key with distinct values in .env and env var,
    the env var value wins.

    **Validates: Requirements 6.3, 6.4**
    """

    @given(
        setting_idx=st.integers(min_value=0, max_value=len(_STRING_SETTINGS) - 1),
        env_value=_safe_text,
    )
    @settings(max_examples=100)
    def test_env_var_overrides_default(
        self,
        setting_idx: int,
        env_value: str,
    ) -> None:
        """For any string setting, an env var with BC_ prefix overrides the default."""
        field_name, env_name = _STRING_SETTINGS[setting_idx]
        original = os.environ.get(env_name)
        try:
            os.environ[env_name] = env_value
            s = AppSettings()
            assert getattr(s, field_name) == env_value
        finally:
            if original is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = original

    @given(monitoring_hours=_pos_int)
    @settings(max_examples=100)
    def test_env_var_overrides_monitoring_interval(
        self,
        monitoring_hours: int,
    ) -> None:
        """For any valid integer, BC_MONITORING_INTERVAL_HOURS env var takes precedence."""
        env_key = "BC_MONITORING_INTERVAL_HOURS"
        original = os.environ.get(env_key)
        try:
            os.environ[env_key] = str(monitoring_hours)
            s = AppSettings()
            assert s.monitoring_interval_hours == monitoring_hours
        finally:
            if original is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = original


# ---------------------------------------------------------------------------
# Property 9: BC_ environment variable loading
# Feature: bc-improvements, Property 9: BC_ environment variable loading
# ---------------------------------------------------------------------------


class TestBCEnvVarLoading:
    """Property 9: BC_ environment variable loading.

    For any string setting field in AppSettings and for any non-empty string
    value, setting the corresponding BC_-prefixed environment variable to that
    value and constructing AppSettings SHALL result in the field having that
    value. This includes BC_DEFAULT_MAX_TOKENS for integer values.

    **Validates: Requirements 4.4, 7.2**
    """

    @given(
        setting_idx=st.integers(min_value=0, max_value=len(_STRING_SETTINGS) - 1),
        value=_safe_text,
    )
    @settings(max_examples=100)
    def test_bc_string_env_var_loading(
        self,
        setting_idx: int,
        value: str,
    ) -> None:
        """For any string setting, setting the BC_ env var results in that value being loaded."""
        field_name, env_name = _STRING_SETTINGS[setting_idx]
        original = os.environ.get(env_name)
        try:
            os.environ[env_name] = value
            s = AppSettings()
            assert getattr(s, field_name) == value
        finally:
            if original is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = original

    @given(max_tokens=st.integers(min_value=1, max_value=100_000))
    @settings(max_examples=100)
    def test_bc_default_max_tokens_env_var_loading(
        self,
        max_tokens: int,
    ) -> None:
        """For any positive integer, setting BC_DEFAULT_MAX_TOKENS results in that value being loaded."""
        env_key = "BC_DEFAULT_MAX_TOKENS"
        original = os.environ.get(env_key)
        try:
            os.environ[env_key] = str(max_tokens)
            s = AppSettings()
            assert s.default_max_tokens == max_tokens
        finally:
            if original is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = original


# ---------------------------------------------------------------------------
# Property 10: Non-integer max_tokens validation
# Feature: bc-improvements, Property 10: Non-integer max_tokens validation
# ---------------------------------------------------------------------------


class TestNonIntegerMaxTokensValidation:
    """Property 10: Non-integer max_tokens validation.

    For any string composed entirely of alphabetic characters (non-numeric),
    setting BC_DEFAULT_MAX_TOKENS to that string and constructing AppSettings
    SHALL raise a ValidationError.

    **Validates: Requirements 7.5**
    """

    @given(bad_value=st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_non_integer_max_tokens_raises_validation_error(
        self,
        bad_value: str,
    ) -> None:
        """For any alphabetic string, setting BC_DEFAULT_MAX_TOKENS raises ValidationError."""
        env_key = "BC_DEFAULT_MAX_TOKENS"
        original = os.environ.get(env_key)
        try:
            os.environ[env_key] = bad_value
            with pytest.raises(ValidationError):
                AppSettings()
        finally:
            if original is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = original
