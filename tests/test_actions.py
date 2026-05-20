"""Тесты для строгой валидации действий агента."""
import pytest
from pydantic import ValidationError

from src.actions import (
    AgentAction,
    ClickAction,
    TypeAction,
    NavigateAction,
    ScrollAction,
    ScreenshotAction,
    UploadFileAction,
    parse_strict_action,
)


class TestStrictModels:
    def test_click_action_valid(self):
        action = ClickAction(element_display_id=5)
        assert action.action_type == "click"
        assert action.element_display_id == 5

    def test_click_action_missing_element_id_raises(self):
        with pytest.raises(ValidationError):
            ClickAction()

    def test_type_action_valid(self):
        action = TypeAction(element_display_id=3, text="hello")
        assert action.text == "hello"

    def test_type_action_missing_text_raises(self):
        with pytest.raises(ValidationError):
            TypeAction(element_display_id=3)

    def test_navigate_action_valid(self):
        action = NavigateAction(url="https://example.com")
        assert action.url == "https://example.com"

    def test_navigate_action_missing_url_raises(self):
        with pytest.raises(ValidationError):
            NavigateAction()

    def test_scroll_action_defaults(self):
        action = ScrollAction(direction="down")
        assert action.amount == 300

    def test_screenshot_action_no_required_fields(self):
        action = ScreenshotAction()
        assert action.action_type == "screenshot"


class TestParseStrictAction:
    def test_parse_click(self):
        data = {"action_type": "click", "element_display_id": 5, "reasoning": "btn"}
        action = parse_strict_action(data)
        assert isinstance(action, ClickAction)
        assert action.element_display_id == 5

    def test_parse_type(self):
        data = {"action_type": "type", "element_display_id": 3, "text": "hello"}
        action = parse_strict_action(data)
        assert isinstance(action, TypeAction)
        assert action.text == "hello"

    def test_parse_invalid_action_type_raises(self):
        with pytest.raises(ValidationError):
            parse_strict_action({"action_type": "nonexistent"})

    def test_parse_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            parse_strict_action({"action_type": "click"})


class TestPathValidators:
    def test_upload_file_path_traversal_blocked(self):
        with pytest.raises(ValidationError):
            UploadFileAction(element_display_id=1, file_path="../etc/passwd")

    def test_upload_file_absolute_path_blocked(self):
        with pytest.raises(ValidationError):
            UploadFileAction(element_display_id=1, file_path="/etc/passwd")

    def test_upload_file_relative_path_allowed(self):
        action = UploadFileAction(element_display_id=1, file_path="data/file.txt")
        assert action.file_path == "data/file.txt"

    def test_legacy_agent_action_path_validator(self):
        with pytest.raises(ValidationError):
            AgentAction(action_type="screenshot", filename="../secret.txt")


class TestLegacyAgentAction:
    def test_legacy_click(self):
        action = AgentAction(action_type="click", element_display_id=5)
        assert action.action_type == "click"
        assert action.element_display_id == 5

    def test_legacy_finish(self):
        action = AgentAction(action_type="finish", summary="done")
        assert action.summary == "done"
