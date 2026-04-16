from pathlib import Path

from PIL import Image

from src.overlay import draw_overlay
from src.element_tracker import TrackedElement


def test_draw_overlay_creates_file(tmp_path):
    # Создаем фиктивное изображение
    img_path = tmp_path / "raw.jpg"
    out_path = tmp_path / "annotated.jpg"
    img = Image.new("RGB", (400, 300), color="white")
    img.save(img_path)

    elements = [
        TrackedElement(
            display_id=1,
            stable_hash="abc123",
            tag="button",
            text="Click me",
            selector="button.btn",
            x=50,
            y=50,
            width=100,
            height=40,
            is_visible=True,
        ),
        TrackedElement(
            display_id=2,
            stable_hash="def456",
            tag="a",
            text="Link",
            selector="a.link",
            x=200,
            y=100,
            width=60,
            height=20,
            is_visible=True,
        ),
    ]

    result_path, mapping = draw_overlay(str(img_path), elements, str(out_path))
    assert Path(result_path).exists()
    assert 1 in mapping
    assert 2 in mapping
    assert mapping[1]["tag"] == "button"
    assert mapping[2]["tag"] == "a"
