"""Утилита для сравнения скриншотов before/after."""
from typing import Tuple, Optional
from PIL import Image, ImageChops


def diff_screenshots(before_path: str, after_path: str, threshold: int = 10) -> Tuple[bool, Optional[Image.Image]]:
    """Сравнивает два скриншота.

    Returns:
        changed: True если различия превышают порог
        diff_image: Optional PIL Image с визуализацией различий
    """
    try:
        before = Image.open(before_path).convert("RGB")
        after = Image.open(after_path).convert("RGB")
    except Exception as exc:
        raise ValueError(f"Cannot open screenshot: {exc}")

    if before.size != after.size:
        return True, None

    diff = ImageChops.difference(before, after)
    # Если diff пустой — картинки идентичны
    if diff.getbbox() is None:
        return False, None

    # Оцениваем "серьёзность" изменений через grayscale + threshold
    gray = diff.convert("L")
    pixels = list(gray.getdata())
    changed_pixels = sum(1 for p in pixels if p > threshold)
    total_pixels = len(pixels)
    ratio = changed_pixels / total_pixels if total_pixels > 0 else 0

    # Считаем changed, если изменилось > 0.5% пикселей
    changed = ratio > 0.005

    # Генерируем diff image (красные пиксели на чёрном фоне)
    diff_visual = Image.new("RGB", before.size)
    diff_pixels = diff.load()
    visual_pixels = diff_visual.load()
    for y in range(before.size[1]):
        for x in range(before.size[0]):
            r, g, b = diff_pixels[x, y]
            if r > threshold or g > threshold or b > threshold:
                visual_pixels[x, y] = (255, 0, 0)
            else:
                visual_pixels[x, y] = (0, 0, 0)

    return changed, diff_visual
