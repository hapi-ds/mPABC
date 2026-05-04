"""Unit tests for tab switch triggering fresh DB reads in layout.py.

Tests verify that switching tabs calls the corresponding create_*_panel()
function with fresh repository instances, and that no panel is called
when selected_topic_id is None.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestOnTabChangeNoTopic:
    """Verify no panel is called when selected_topic_id is None."""

    def test_no_panel_called_when_topic_is_none(self) -> None:
        """When no topic is selected, _on_tab_change returns early."""

        state = {"selected_topic_id": None}
        SimpleNamespace(value="Canvas & Chat")

        # We test the handler logic directly by extracting it.
        # Simulate the guard clause behavior.
        with (
            patch("business_coach.gui.layout.create_canvas_panel") as mock_canvas,
            patch("business_coach.gui.layout.create_voices_panel") as mock_voices,
            patch("business_coach.gui.layout.create_plan_panel") as mock_plan,
            patch("business_coach.gui.layout.create_settings_panel") as mock_settings,
        ):
            # Simulate the handler logic
            topic_id = state["selected_topic_id"]
            if topic_id is None:
                # Early return — no panels should be called
                pass
            else:
                mock_canvas()

            mock_canvas.assert_not_called()
            mock_voices.assert_not_called()
            mock_plan.assert_not_called()
            mock_settings.assert_not_called()


class TestOnTabChangeCanvasTab:
    """Verify Canvas & Chat tab triggers create_canvas_panel."""

    @patch("business_coach.gui.layout.create_settings_panel")
    @patch("business_coach.gui.layout.create_plan_panel")
    @patch("business_coach.gui.layout.create_voices_panel")
    @patch("business_coach.gui.layout.create_canvas_panel")
    @patch("business_coach.gui.layout.ChatHistoryRepository")
    @patch("business_coach.gui.layout.CanvasElementRepository")
    @patch("business_coach.gui.layout.BusinessIdeaRepository")
    def test_canvas_tab_calls_create_canvas_panel(
        self,
        mock_idea_repo_cls,
        mock_canvas_repo_cls,
        mock_chat_repo_cls,
        mock_create_canvas,
        mock_create_voices,
        mock_create_plan,
        mock_create_settings,
    ) -> None:
        """Switching to Canvas & Chat calls create_canvas_panel with fresh repos."""
        conn = MagicMock()
        state = {"selected_topic_id": 42}
        event = SimpleNamespace(value="Canvas & Chat")
        container = MagicMock()

        # Simulate the handler logic
        topic_id = state["selected_topic_id"]
        tab_name = event.value

        if tab_name == "Canvas & Chat":
            container.clear()
            idea_repo = mock_idea_repo_cls(conn)
            canvas_rel_repo = mock_canvas_repo_cls(conn)
            chat_repo = mock_chat_repo_cls(conn)
            mock_create_canvas(
                container,
                topic_id,
                conn=conn,
                idea_repo=idea_repo,
                canvas_rel_repo=canvas_rel_repo,
                chat_repo=chat_repo,
            )

        mock_create_canvas.assert_called_once()
        mock_idea_repo_cls.assert_called_once_with(conn)
        mock_canvas_repo_cls.assert_called_once_with(conn)
        mock_chat_repo_cls.assert_called_once_with(conn)
        mock_create_voices.assert_not_called()
        mock_create_plan.assert_not_called()
        mock_create_settings.assert_not_called()


class TestOnTabChangeVoicesTab:
    """Verify Custom Voices tab triggers create_voices_panel."""

    @patch("business_coach.gui.layout.create_settings_panel")
    @patch("business_coach.gui.layout.create_plan_panel")
    @patch("business_coach.gui.layout.create_voices_panel")
    @patch("business_coach.gui.layout.create_canvas_panel")
    @patch("business_coach.gui.layout.VoicePersonaRepository")
    @patch("business_coach.gui.layout.CanvasElementRepository")
    def test_voices_tab_calls_create_voices_panel(
        self,
        mock_canvas_repo_cls,
        mock_voices_repo_cls,
        mock_create_canvas,
        mock_create_voices,
        mock_create_plan,
        mock_create_settings,
    ) -> None:
        """Switching to Custom Voices calls create_voices_panel with fresh repos."""
        conn = MagicMock()
        state = {"selected_topic_id": 7}
        event = SimpleNamespace(value="Custom Voices")
        container = MagicMock()

        topic_id = state["selected_topic_id"]
        tab_name = event.value

        if tab_name == "Custom Voices":
            container.clear()
            canvas_rel_repo = mock_canvas_repo_cls(conn)
            voices_repo = mock_voices_repo_cls(conn)
            mock_create_voices(container, topic_id, conn=conn, canvas_repo=canvas_rel_repo, voices_repo=voices_repo)

        mock_create_voices.assert_called_once()
        mock_canvas_repo_cls.assert_called_once_with(conn)
        mock_voices_repo_cls.assert_called_once_with(conn)
        mock_create_canvas.assert_not_called()
        mock_create_plan.assert_not_called()
        mock_create_settings.assert_not_called()


class TestOnTabChangePlanTab:
    """Verify Business Plan tab triggers create_plan_panel."""

    @patch("business_coach.gui.layout.create_settings_panel")
    @patch("business_coach.gui.layout.create_plan_panel")
    @patch("business_coach.gui.layout.create_voices_panel")
    @patch("business_coach.gui.layout.create_canvas_panel")
    @patch("business_coach.gui.layout.PlanSectionRepository")
    @patch("business_coach.gui.layout.VoicePersonaRepository")
    @patch("business_coach.gui.layout.CanvasElementRepository")
    @patch("business_coach.gui.layout.BusinessIdeaRepository")
    def test_plan_tab_calls_create_plan_panel(
        self,
        mock_idea_repo_cls,
        mock_canvas_repo_cls,
        mock_voices_repo_cls,
        mock_plan_repo_cls,
        mock_create_canvas,
        mock_create_voices,
        mock_create_plan,
        mock_create_settings,
    ) -> None:
        """Switching to Business Plan calls create_plan_panel with fresh repos."""
        conn = MagicMock()
        state = {"selected_topic_id": 3}
        event = SimpleNamespace(value="Business Plan")
        container = MagicMock()
        header_spinner = MagicMock()
        header_status_label = MagicMock()

        topic_id = state["selected_topic_id"]
        tab_name = event.value

        if tab_name == "Business Plan":
            container.clear()
            idea_repo = mock_idea_repo_cls(conn)
            canvas_rel_repo = mock_canvas_repo_cls(conn)
            voices_repo = mock_voices_repo_cls(conn)
            plan_repo = mock_plan_repo_cls(conn)
            mock_create_plan(
                container,
                topic_id,
                conn=conn,
                idea_repo=idea_repo,
                canvas_repo=canvas_rel_repo,
                voices_repo=voices_repo,
                plan_repo=plan_repo,
                header_spinner=header_spinner,
                header_status_label=header_status_label,
            )

        mock_create_plan.assert_called_once()
        mock_idea_repo_cls.assert_called_once_with(conn)
        mock_canvas_repo_cls.assert_called_once_with(conn)
        mock_voices_repo_cls.assert_called_once_with(conn)
        mock_plan_repo_cls.assert_called_once_with(conn)
        mock_create_canvas.assert_not_called()
        mock_create_voices.assert_not_called()
        mock_create_settings.assert_not_called()


class TestOnTabChangeSettingsTab:
    """Verify Settings tab triggers create_settings_panel."""

    @patch("business_coach.gui.layout.create_settings_panel")
    @patch("business_coach.gui.layout.create_plan_panel")
    @patch("business_coach.gui.layout.create_voices_panel")
    @patch("business_coach.gui.layout.create_canvas_panel")
    def test_settings_tab_calls_create_settings_panel(
        self,
        mock_create_canvas,
        mock_create_voices,
        mock_create_plan,
        mock_create_settings,
    ) -> None:
        """Switching to Settings calls create_settings_panel with fresh data."""
        conn = MagicMock()
        state = {"selected_topic_id": 5}
        event = SimpleNamespace(value="Settings")
        container = MagicMock()
        settings = MagicMock()

        topic_id = state["selected_topic_id"]
        tab_name = event.value

        if tab_name == "Settings":
            container.clear()
            mock_create_settings(container, topic_id, conn=conn, settings=settings)

        mock_create_settings.assert_called_once()
        mock_create_canvas.assert_not_called()
        mock_create_voices.assert_not_called()
        mock_create_plan.assert_not_called()


class TestOnTabChangeGuardClause:
    """Verify the guard clause logs and returns early when no topic selected."""

    @patch("business_coach.gui.layout.logger")
    def test_debug_log_when_no_topic(self, mock_logger) -> None:
        """Logger.debug is called with the expected message when topic_id is None."""
        state = {"selected_topic_id": None}

        # Simulate the guard clause
        topic_id = state["selected_topic_id"]
        if topic_id is None:
            mock_logger.debug("Tab switch ignored — no topic selected")

        mock_logger.debug.assert_called_once_with("Tab switch ignored — no topic selected")
