"""Тесты для robust JSON extraction из LLM-ответов."""
import json

import pytest

from src.llm_client import BaseVisionLLM


class TestExtractJsonObject:
    def test_raw_json_object(self):
        raw = '{"action_type": "click", "element_id": 5}'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "click", "element_id": 5}

    def test_fenced_json(self):
        raw = '```json\n{"action_type": "click", "element_id": 5}\n```'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "click", "element_id": 5}

    def test_fenced_without_json_label(self):
        raw = '```\n{"action_type": "click", "element_id": 5}\n```'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "click", "element_id": 5}

    def test_pre_post_text(self):
        raw = 'Sure! Here is the action:\n{"action_type": "navigate", "url": "https://example.com"}\nHope this helps!'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "navigate", "url": "https://example.com"}

    def test_pre_post_with_fenced(self):
        raw = (
            'Here is your result:\n'
            '```json\n{"action_type": "type", "element_id": 3, "text": "hello"}\n```\n'
            'Let me know if you need more.'
        )
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "type", "element_id": 3, "text": "hello"}

    def test_nested_json(self):
        raw = '{"action_type": "click", "meta": {"reason": "btn"}, "element_id": 1}'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result["meta"] == {"reason": "btn"}

    def test_multiple_noise_before_and_after(self):
        raw = 'Some text {not: json} more text {"action_type": "done"} trailing text'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "done"}

    def test_malformed_no_braces_raises(self):
        raw = 'There is no JSON here at all.'
        with pytest.raises(ValueError, match="No JSON object found"):
            BaseVisionLLM._extract_json_object(raw)

    def test_malformed_unbalanced_raises(self):
        raw = '{"action_type": "click", "element_id": 5'
        with pytest.raises(ValueError, match="No valid JSON object found"):
            BaseVisionLLM._extract_json_object(raw)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="empty or not a string"):
            BaseVisionLLM._extract_json_object("")

    def test_json_array_extracts_inner_object(self):
        raw = '[{"action_type": "click", "element_id": 1}]'
        result = BaseVisionLLM._extract_json_object(raw)
        assert result == {"action_type": "click", "element_id": 1}

    def test_legacy_clean_json_alias(self):
        raw = '{"action_type": "click", "element_id": 5}'
        result = BaseVisionLLM._clean_json(raw)
        assert json.loads(result) == {"action_type": "click", "element_id": 5}
