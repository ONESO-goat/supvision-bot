"""
Test suite for the YTG screen-watching pipeline: Agent, GuardianStateManager,
and ScreenshotLogic.

Run with:
    pip install pytest pillow --break-system-packages
    pytest test_agent_pipeline.py -v

Notes on approach:
- GuardianStateManager and ScreenshotLogic have no external deps, so they're
  tested directly.
- Agent depends on Engine, Prompts, and the Guardian/GuardianSettings models.
  Those are mocked so this file doesn't need your real API keys or DB to run.
- time.perf_counter is monkeypatched where timer behavior is being tested, so
  tests don't actually sleep for 2-5 minutes.
"""

import io
import time
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from agent.stopwatch import GuardianStateManager
from agent.screenshot_logic import ScreenshotLogic


# ---------------------------------------------------------------------------
# GuardianStateManager
# ---------------------------------------------------------------------------

class TestGuardianStateManager:

    def test_initial_state(self):
        sm = GuardianStateManager()
        assert sm.warning_active is False
        assert sm.tracking_start_time is None
        assert sm.give_user_points is False
        assert sm.amount_of_points_to_assign == 0
        assert sm.events == []

    def test_trigger_warning_sets_active_and_resets_timer(self):
        sm = GuardianStateManager()
        sm.tracking_start_time = 123.0  # pretend a timer was running
        sm.trigger_warning()
        assert sm.warning_active is True
        assert sm.tracking_start_time is None

    def test_user_scrolled_away_only_starts_if_warning_active(self):
        sm = GuardianStateManager()
        # warning not active -> should NOT start a timer
        sm.user_scrolled_away(target_duration=180)
        assert sm.tracking_start_time is None

    def test_user_scrolled_away_starts_timer_when_warned(self):
        sm = GuardianStateManager()
        sm.trigger_warning()
        sm.user_scrolled_away(target_duration=180)
        assert sm.tracking_start_time is not None
        assert sm.target_duration == 180

    def test_user_scrolled_away_does_not_restart_an_already_running_timer(self):
        sm = GuardianStateManager()
        sm.trigger_warning()
        sm.user_scrolled_away(target_duration=180)
        first_start = sm.tracking_start_time
        # calling again shouldn't reset the clock
        sm.user_scrolled_away(target_duration=999)
        assert sm.tracking_start_time == first_start
        assert sm.target_duration == 180

    def test_random_duration_falls_within_2_to_5_minutes(self):
        sm = GuardianStateManager()
        sm.trigger_warning()
        sm.user_scrolled_away(random_time_duration=True)
        assert 120 <= sm.target_duration <= 300

    def test_update_and_check_timer_no_op_when_not_warning(self):
        sm = GuardianStateManager()
        sm.update_and_check_timer()  # should not raise, should do nothing
        assert sm.give_user_points is False

    def test_update_and_check_timer_does_not_award_before_duration(self):
        sm = GuardianStateManager()
        sm.trigger_warning()
        with patch("time.perf_counter", side_effect=[100.0, 105.0]):
            sm.user_scrolled_away(target_duration=180)
            sm.update_and_check_timer()
        assert sm.give_user_points is False
        assert sm.warning_active is True  # still counting down

    def test_update_and_check_timer_awards_points_after_duration(self):
        sm = GuardianStateManager()
        sm.trigger_warning()
        # start at t=100, check at t=400 (well past a 180s target)
        with patch("time.perf_counter", side_effect=[100.0, 400.0]):
            sm.user_scrolled_away(target_duration=180)
            sm.update_and_check_timer()
        assert sm.give_user_points is True
        assert sm.amount_of_points_to_assign == 10
        assert sm.warning_active is False
        assert sm.tracking_start_time is None

    def test_update_and_check_timer_does_not_require_events(self):
        """Regression test: timer completion must not depend on self.events,
        since flush_wipe_events() can empty that list independently."""
        sm = GuardianStateManager()
        sm.trigger_warning()
        assert sm.events == []
        with patch("time.perf_counter", side_effect=[100.0, 400.0]):
            sm.user_scrolled_away(target_duration=180)
            sm.update_and_check_timer()
        assert sm.give_user_points is True

    def test_add_event_appends_expected_shape(self):
        sm = GuardianStateManager()
        sm.add_event(content="test content", time_duration=60)
        assert len(sm.events) == 1
        assert sm.events[0] == {
            "content": "test content",
            "should_avoid": True,
            "time_to_wait": 60,
        }

    def test_flush_wipe_events_empties_list_and_commits_each(self):
        sm = GuardianStateManager()
        sm.add_event(content="event one")
        sm.add_event(content="event two")

        mock_session = MagicMock()
        mock_user = MagicMock()

        with patch("stopwatch.GuardianRecapToOwner") as MockRecap:
            sm.flush_wipe_events(session=mock_session, user=mock_user)

        assert MockRecap.call_count == 2
        assert mock_session.add.call_count == 2
        assert mock_session.commit.call_count == 2
        assert sm.events == []

    def test_flush_wipe_events_no_op_on_empty_list(self):
        sm = GuardianStateManager()
        mock_session = MagicMock()
        sm.flush_wipe_events(session=mock_session, user=MagicMock())
        mock_session.add.assert_not_called()

    def test_empty_point_count_resets_to_zero(self):
        sm = GuardianStateManager()
        sm.amount_of_points_to_assign = 50
        sm.empty_point_count()
        assert sm.amount_of_points_to_assign == 0


# ---------------------------------------------------------------------------
# ScreenshotLogic
# ---------------------------------------------------------------------------

def _make_solid_image(size=(100, 100), color=(255, 0, 0)):
    return Image.new("RGB", size, color)


def _image_to_png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestScreenshotLogic:

    def test_is_different_below_threshold(self):
        sl = ScreenshotLogic()
        assert sl._is_different(0.001) is False

    def test_is_different_above_threshold(self):
        sl = ScreenshotLogic()
        assert sl._is_different(0.5) is True

    def test_difference_identical_images_is_zero(self):
        sl = ScreenshotLogic()
        img = _make_solid_image()
        assert sl.difference(img, img) == 0.0

    def test_difference_different_size_returns_max(self):
        sl = ScreenshotLogic()
        img1 = _make_solid_image(size=(100, 100))
        img2 = _make_solid_image(size=(50, 50))
        assert sl.difference(img1, img2) == 1.0

    def test_difference_completely_different_colors_is_high(self):
        sl = ScreenshotLogic()
        black = _make_solid_image(color=(0, 0, 0))
        white = _make_solid_image(color=(255, 255, 255))
        diff = sl.difference(black, white)
        assert diff == pytest.approx(1.0, abs=0.01)

    def test_check_for_updates_first_call_returns_false_and_stores_baseline(self):
        sl = ScreenshotLogic()
        fake_png = _image_to_png_bytes(_make_solid_image())
        with patch.object(sl, "capture_screenshot", return_value=fake_png):
            result = sl.check_for_updates()
        assert result is False
        assert sl.previous_screenshot is not None

    def test_check_for_updates_detects_no_change(self):
        sl = ScreenshotLogic()
        fake_png = _image_to_png_bytes(_make_solid_image(color=(10, 10, 10)))
        with patch.object(sl, "capture_screenshot", return_value=fake_png):
            sl.check_for_updates()  # establishes baseline
            result = sl.check_for_updates()  # same image again
        assert result is False
        assert sl.times_on_the_same_page == 1

    def test_check_for_updates_detects_real_change(self):
        sl = ScreenshotLogic()
        frame_a = _image_to_png_bytes(_make_solid_image(color=(0, 0, 0)))
        frame_b = _image_to_png_bytes(_make_solid_image(color=(255, 255, 255)))
        with patch.object(sl, "capture_screenshot", side_effect=[frame_a, frame_b]):
            sl.check_for_updates()  # baseline (black)
            result = sl.check_for_updates()  # now white -> big diff
        assert result is True
        assert sl.times_on_the_same_page == 0

    def test_check_for_updates_handles_capture_failure(self):
        sl = ScreenshotLogic()
        with patch.object(sl, "capture_screenshot", return_value=b""):
            result = sl.check_for_updates()
        assert result is False

    def test_capture_screenshot_does_not_write_to_disk(self, tmp_path):
        """Regression guard: capture_screenshot should not persist raw
        screenshots to disk (privacy requirement discussed in review)."""
        sl = ScreenshotLogic()
        sl.previous_image_file = str(tmp_path / "should_not_exist.jpeg")
        with patch("mss.mss") as mock_mss:
            mock_sct = MagicMock()
            mock_shot = MagicMock()
            mock_shot.rgb = b"\x00" * (10 * 10 * 3)
            mock_shot.size = (10, 10)
            mock_sct.grab.return_value = mock_shot
            mock_sct.monitors = [None, "monitor1"]
            mock_mss.return_value.__enter__.return_value = mock_sct
            sl.capture_screenshot()
        import os
        assert not os.path.exists(sl.previous_image_file)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
# Agent pulls in Engine, Prompts, and the Guardian models on import, which
# aren't needed for these tests. We patch them out before importing agent.py.

@pytest.fixture
def agent_instance():
    with patch("engine.Engine") as MockEngine, patch("helpers.prompt.Prompts") as MockPrompts:
        from agent.bot import Agent  # imported here so the patches above are active

        mock_guardian = MagicMock()
        mock_settings = MagicMock()
        mock_settings.strictness = "normal"

        a = Agent(
            guadian=mock_guardian,
            guardian_settings=mock_settings,
            guardian_restrictions=["gambling", "graphic violence"],
        )
        # Replace the real engine/screenshot_logic with controllable mocks
        a.engine = MagicMock()
        a.screenshot_logic = MagicMock()
        a.prompts = MagicMock()
        yield a


class TestAgentInitialization:

    def test_requires_guardian_and_settings(self):
        with patch("engine.Engine"), patch("helpers.prompt.Prompts"):
            from agent.bot import Agent
            with pytest.raises(ValueError):
                Agent(guadian=None, guardian_settings=MagicMock(), guardian_restrictions=[])
            with pytest.raises(ValueError):
                Agent(guadian=MagicMock(), guardian_settings=None, guardian_restrictions=[])


class TestAgentCheck:

    def test_check_returns_none_when_screen_unchanged(self, agent_instance):
        agent_instance.screenshot_logic.check_for_updates.return_value = False
        result = agent_instance.check()
        assert result is None
        # classification should never be attempted if nothing changed
        agent_instance.engine._classify_image.assert_not_called()

    def test_check_does_not_capture_screenshot_twice(self, agent_instance):
        """Regression test: check() should reuse the frame check_for_updates
        already captured, not call capture_screenshot() a second time."""
        agent_instance.screenshot_logic.check_for_updates.return_value = True
        fake_img = _make_solid_image()
        agent_instance.screenshot_logic.get_previous_image.return_value = fake_img
        agent_instance.engine._classify_image.return_value = {
            "summary": "A news article",
            "comments": "",
            "visible_text": "headline text",
            "detailed_description": "a detailed description",
            "confidence": 0.9,
            "error": False,
            "error_message": None,
        }
        agent_instance.engine._generate.return_value = {
            "flagged": False,
            "category": None,
            "confidence": 0.1,
            "description": "No content matching configured restrictions.",
            "source_context": None,
        }

        agent_instance.check()
        agent_instance.screenshot_logic.capture_screenshot.assert_not_called()

    def test_check_handles_vision_error_gracefully(self, agent_instance):
        agent_instance.screenshot_logic.check_for_updates.return_value = True
        agent_instance.screenshot_logic.get_previous_image.return_value = _make_solid_image()
        agent_instance.engine._classify_image.return_value = {
            "error": True,
            "error_message": "model timeout",
        }
        result = agent_instance.check()
        assert result is None
        # should not attempt the second-stage reasoning call on a vision error
        agent_instance.engine._generate.assert_not_called()

    def test_check_composes_description_from_all_vision_fields(self, agent_instance):
        """The reasoning call should receive summary + visible_text + comments
        + detailed_description, not just a single 'content' field that
        doesn't exist in the vision schema."""
        agent_instance.screenshot_logic.check_for_updates.return_value = True
        agent_instance.screenshot_logic.get_previous_image.return_value = _make_solid_image()
        agent_instance.engine._classify_image.return_value = {
            "summary": "SUMMARY_MARKER",
            "comments": "COMMENTS_MARKER",
            "visible_text": "VISIBLE_TEXT_MARKER",
            "detailed_description": "DETAIL_MARKER",
            "confidence": 0.9,
            "error": False,
            "error_message": None,
        }
        agent_instance.engine._generate.return_value = {
            "flagged": False, "category": None, "confidence": 0.1,
            "description": "clean", "source_context": None,
        }

        agent_instance.check()

        assert agent_instance.engine._generate.called
        passed_text = agent_instance.engine._generate.call_args.kwargs.get("text", "")
        for marker in ["SUMMARY_MARKER", "COMMENTS_MARKER", "VISIBLE_TEXT_MARKER", "DETAIL_MARKER"]:
            assert marker in passed_text


class TestAgentReadOverview:

    def test_flagged_content_triggers_warning_and_logs_event_once(self, agent_instance):
        user = MagicMock(name="Julius")
        result = {
            "flagged": True,
            "category": "gambling",
            "confidence": 0.8,
            "description": "A gambling site",
            "source_context": "chrome",
            "image_summary": {
                "summary": "s", "visible_text": "v", "detailed_description": "d", "confidence": 0.9,
            },
        }
        agent_instance.read_overview(user, result)
        assert agent_instance.stopwatch.warning_active is True
        assert len(agent_instance.stopwatch.events) == 1

    def test_flagged_content_does_not_duplicate_events_while_still_flagged(self, agent_instance):
        """Regression test: the same flagged content seen on consecutive
        polls should log exactly one event, not one per poll."""
        user = MagicMock(name="Julius")
        result = {
            "flagged": True,
            "category": "gambling",
            "confidence": 0.8,
            "description": "A gambling site",
            "source_context": "chrome",
            "image_summary": {
                "summary": "s", "visible_text": "v", "detailed_description": "d", "confidence": 0.9,
            },
        }
        agent_instance.read_overview(user, result)
        agent_instance.read_overview(user, result)
        agent_instance.read_overview(user, result)
        assert len(agent_instance.stopwatch.events) == 1

    def test_clearing_after_warning_starts_the_timer(self, agent_instance):
        user = MagicMock(name="Julius")
        flagged = {
            "flagged": True, "category": "gambling", "confidence": 0.8,
            "description": "A gambling site", "source_context": "chrome",
            "image_summary": {"summary": "s", "visible_text": "v", "detailed_description": "d", "confidence": 0.9},
        }
        clean = {
            "flagged": False, "category": None, "confidence": 0.1,
            "description": "clean", "source_context": None,
        }
        agent_instance.read_overview(user, flagged)
        assert agent_instance.stopwatch.tracking_start_time is None
        agent_instance.read_overview(user, clean)
        assert agent_instance.stopwatch.tracking_start_time is not None

    def test_clean_content_with_no_prior_warning_does_nothing(self, agent_instance):
        user = MagicMock(name="Julius")
        clean = {
            "flagged": False, "category": None, "confidence": 0.1,
            "description": "clean", "source_context": None,
        }
        agent_instance.read_overview(user, clean)
        assert agent_instance.stopwatch.warning_active is False
        assert agent_instance.stopwatch.tracking_start_time is None


class TestAgentBreakdownOverview:

    def test_breakdown_overview_uses_correct_field_names(self, agent_instance):
        """Regression test: fields must match the actual vision schema
        (summary/visible_text/detailed_description), not the old
        'content' field that never existed."""
        user = MagicMock()
        user.name = "Julius"
        result = {
            "category": "gambling",
            "description": "desc",
            "confidence": 0.8,
            "image_summary": {
                "summary": "SUMMARY_HERE",
                "visible_text": "VISIBLE_TEXT_HERE",
                "detailed_description": "DETAIL_HERE",
                "confidence": 0.6,
            },
        }
        text = agent_instance._breakdown_overview(user=user, classification_result=result)
        assert "SUMMARY_HERE" in text
        assert "VISIBLE_TEXT_HERE" in text
        assert "DETAIL_HERE" in text
        assert "Julius" in text

    def test_breakdown_overview_averages_confidence(self, agent_instance):
        user = MagicMock()
        user.name = "Julius"
        result = {
            "category": "gambling",
            "description": "desc",
            "confidence": 1.0,
            "image_summary": {
                "summary": "s", "visible_text": "v", "detailed_description": "d",
                "confidence": 0.0,
            },
        }
        text = agent_instance._breakdown_overview(user=user, classification_result=result)
        assert "0.5" in text  # (1.0 * 0.5) + (0.0 * 0.5)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))