from src.element_tracker import (
    compute_element_hash,
    deduplicate_elements,
    track_elements,
    TrackedElement,
)


def test_compute_element_hash_consistency():
    h1 = compute_element_hash("button", 10.0, 20.0, 100.0, 50.0, "Click me")
    h2 = compute_element_hash("button", 14.0, 24.0, 104.0, 54.0, "Click me")
    # Координаты квантизуются до 10px, хеши должны совпасть
    assert h1 == h2
    assert len(h1) == 8


def test_compute_element_hash_different_text():
    h1 = compute_element_hash("button", 10.0, 20.0, 100.0, 50.0, "Click me")
    h2 = compute_element_hash("button", 10.0, 20.0, 100.0, 50.0, "Submit")
    assert h1 != h2


def test_deduplicate_elements_keeps_larger():
    raw = [
        {"x": 0, "y": 0, "width": 100, "height": 100, "tag": "div", "text": "outer"},
        {"x": 5, "y": 5, "width": 90, "height": 90, "tag": "div", "text": "inner"},
    ]
    result = deduplicate_elements(raw, iou_threshold=0.8)
    assert len(result) == 1
    assert result[0]["text"] == "outer"


def test_deduplicate_elements_no_overlap():
    raw = [
        {"x": 0, "y": 0, "width": 50, "height": 50, "tag": "a", "text": "link1"},
        {"x": 200, "y": 200, "width": 50, "height": 50, "tag": "a", "text": "link2"},
    ]
    result = deduplicate_elements(raw)
    assert len(result) == 2


def test_track_elements_assigns_ids():
    raw = [
        {"tag": "button", "text": "OK", "selector": "button.ok", "x": 0, "y": 0, "width": 50, "height": 30, "is_visible": True},
        {"tag": "a", "text": "Cancel", "selector": "a.cancel", "x": 100, "y": 0, "width": 60, "height": 30, "is_visible": True},
    ]
    tracked, mapping = track_elements(raw)
    assert len(tracked) == 2
    assert tracked[0].display_id == 1
    assert tracked[1].display_id == 2
    assert mapping[1].tag == "button"
    assert mapping[2].tag == "a"
    assert len(tracked[0].stable_hash) == 8


def test_track_elements_deduplicates():
    raw = [
        {"tag": "div", "text": "outer", "selector": "div", "x": 0, "y": 0, "width": 100, "height": 100, "is_visible": True},
        {"tag": "div", "text": "inner", "selector": "div", "x": 5, "y": 5, "width": 90, "height": 90, "is_visible": True},
    ]
    tracked, mapping = track_elements(raw)
    assert len(tracked) == 1
    assert tracked[0].display_id == 1
