import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass
class TrackedElement:
    display_id: int
    stable_hash: str
    tag: str
    text: str
    selector: str
    x: float
    y: float
    width: float
    height: float
    is_visible: bool
    role: str = ""
    accessible_name: str = ""
    label: str = ""
    placeholder: str = ""
    testid: str = ""
    href: str = ""
    dom_path: str = ""
    enabled: bool = True

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    @property
    def candidate_locators(self) -> List[Dict[str, str]]:
        """Ordered list of candidate locators for Playwright resolver."""
        locators: List[Dict[str, str]] = []
        if self.testid:
            locators.append({"type": "test_id", "value": self.testid})
        if self.role and self.accessible_name:
            locators.append({"type": "role", "value": f"{self.role}[name='{self.accessible_name}']"})
        if self.label:
            locators.append({"type": "label", "value": self.label})
        if self.placeholder:
            locators.append({"type": "placeholder", "value": self.placeholder})
        if self.text:
            locators.append({"type": "text", "value": self.text})
        if self.selector and self.selector.startswith("#"):
            locators.append({"type": "css", "value": self.selector})
        if self.href:
            locators.append({"type": "href", "value": self.href})
        if self.dom_path:
            locators.append({"type": "dom_path", "value": self.dom_path})
        locators.append({"type": "coordinates", "value": f"{self.cx},{self.cy}"})
        return locators


def _quantize(value: float, step: float = 10.0) -> int:
    return int(round(value / step) * step)


def compute_element_hash(
    tag: str,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    testid: str = "",
) -> str:
    """Генерирует стабильный хеш на основе грубых координат и текста."""
    qx = _quantize(x)
    qy = _quantize(y)
    qw = _quantize(width)
    qh = _quantize(height)
    safe_text = text.strip()[:30]
    raw = f"{tag}|{qx}|{qy}|{qw}|{qh}|{safe_text}|{testid}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def _iou(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Intersection over Union для двух прямоугольников."""
    x1 = max(a["x"], b["x"])
    y1 = max(a["y"], b["y"])
    x2 = min(a["x"] + a["width"], b["x"] + b["width"])
    y2 = min(a["y"] + a["height"], b["y"] + b["height"])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = a["width"] * a["height"]
    area_b = b["width"] * b["height"]
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def deduplicate_elements(raw_elements: List[Dict[str, any]], iou_threshold: float = 0.8) -> List[Dict[str, any]]:
    """
    Удаляет вложенные/дублирующиеся элементы. Если IoU > threshold, оставляет больший (по площади).
    """
    result: List[Dict[str, any]] = []
    for el in raw_elements:
        area = el.get("width", 0) * el.get("height", 0)
        duplicate = False
        for i, existing in enumerate(result):
            existing_area = existing.get("width", 0) * existing.get("height", 0)
            if _iou(el, existing) > iou_threshold:
                # Оставляем больший элемент
                if area > existing_area:
                    result[i] = el
                duplicate = True
                break
        if not duplicate:
            result.append(el)
    return result


def track_elements(raw_elements: List[Dict[str, any]]) -> Tuple[List[TrackedElement], Dict[int, TrackedElement]]:
    """
    Принимает сырые элементы, дедуплицирует, назначает display_id и stable_hash.
    Возвращает список tracked элементов и mapping display_id -> element.
    """
    deduped = deduplicate_elements(raw_elements)

    tracked: List[TrackedElement] = []
    display_map: Dict[int, TrackedElement] = {}

    display_id = 1
    for el in deduped:
        stable_hash = compute_element_hash(
            tag=el.get("tag", ""),
            x=el.get("x", 0),
            y=el.get("y", 0),
            width=el.get("width", 0),
            height=el.get("height", 0),
            text=el.get("text", ""),
            testid=el.get("testid", ""),
        )
        te = TrackedElement(
            display_id=display_id,
            stable_hash=stable_hash,
            tag=el.get("tag", ""),
            text=el.get("text", ""),
            selector=el.get("selector", ""),
            x=el.get("x", 0),
            y=el.get("y", 0),
            width=el.get("width", 0),
            height=el.get("height", 0),
            is_visible=el.get("is_visible", True),
            role=el.get("role", ""),
            accessible_name=el.get("accessible_name", ""),
            label=el.get("label", ""),
            placeholder=el.get("placeholder", ""),
            testid=el.get("testid", ""),
            href=el.get("href", ""),
            dom_path=el.get("dom_path", ""),
            enabled=el.get("enabled", True),
        )
        tracked.append(te)
        display_map[display_id] = te
        display_id += 1

    return tracked, display_map
