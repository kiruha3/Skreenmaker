import pytest
from src.variable_resolver import resolve_variables, resolve_step, resolve_steps


def test_resolve_simple():
    assert resolve_variables("${user}", {"user": "admin"}) == "admin"


def test_resolve_multiple():
    assert resolve_variables("${a} and ${b}", {"a": "1", "b": "2"}) == "1 and 2"


def test_resolve_missing():
    assert resolve_variables("${x}", {}) == "${x}"


def test_resolve_step():
    step = {"action_type": "type", "text": "${pass}"}
    assert resolve_step(step, {"pass": "secret"})["text"] == "secret"


def test_resolve_steps():
    steps = [
        {"action_type": "navigate", "url": "${base_url}/login"},
        {"action_type": "type", "text": "${email}"},
    ]
    result = resolve_steps(steps, {"base_url": "https://example.com", "email": "a@b.com"})
    assert result[0]["url"] == "https://example.com/login"
    assert result[1]["text"] == "a@b.com"


def test_resolve_no_variables():
    assert resolve_variables("hello world", {}) == "hello world"


def test_resolve_empty_text():
    assert resolve_variables(None, {"a": "b"}) is None
    assert resolve_variables("", {"a": "b"}) == ""
