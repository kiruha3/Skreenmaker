from typing import List, Tuple, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from src.browser import InteractiveElement


def draw_overlay(
    screenshot_path: str,
    elements: List[InteractiveElement],
    output_path: str,
) -> Tuple[str, Dict[int, Dict[str, Any]]]:
    """
    Рисует на скриншоте номера интерактивных элементов.
    Возвращает путь к аннотированному изображению и словарь element_id -> info.
    """
    img = Image.open(screenshot_path)
    draw = ImageDraw.Draw(img)

    # Попробуем использовать шрифт по умолчанию, но с увеличенным размером
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    element_map: Dict[int, Dict[str, Any]] = {}

    for el in elements:
        # Центр элемента
        cx = el.x + el.width / 2
        cy = el.y + el.height / 2

        # Рамка
        draw.rectangle(
            [(el.x, el.y), (el.x + el.width, el.y + el.height)],
            outline="red",
            width=2,
        )

        # Номер в кружке/прямоугольнике
        label = str(el.element_id)
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad = 3
        label_x = el.x
        label_y = el.y - text_h - pad * 2
        if label_y < 0:
            label_y = el.y

        draw.rectangle(
            [(label_x, label_y), (label_x + text_w + pad * 2, label_y + text_h + pad * 2)],
            fill="red",
        )
        draw.text(
            (label_x + pad, label_y + pad),
            label,
            fill="white",
            font=font,
        )

        element_map[el.element_id] = {
            "tag": el.tag,
            "text": el.text,
            "selector": el.selector,
            "cx": cx,
            "cy": cy,
            "x": el.x,
            "y": el.y,
            "width": el.width,
            "height": el.height,
        }

    img.save(output_path, "JPEG", quality=85)
    return output_path, element_map
