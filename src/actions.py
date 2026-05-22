from typing import Literal, Optional, Union, Annotated, Dict, Any
from pydantic import BaseModel, Field, field_validator, TypeAdapter


class BaseAction(BaseModel):
    """Базовая модель для всех действий агента."""

    reasoning: str = Field(
        default="",
        description="Краткое объяснение, почему выбрано это действие",
    )


class NavigateAction(BaseAction):
    action_type: Literal["navigate"] = "navigate"
    url: str = Field(description="URL для навигации")


class ClickAction(BaseAction):
    action_type: Literal["click"] = "click"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")


class TypeAction(BaseAction):
    action_type: Literal["type"] = "type"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    text: str = Field(description="Текст для ввода")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")


class ScrollAction(BaseAction):
    action_type: Literal["scroll"] = "scroll"
    direction: Literal["up", "down", "left", "right"] = Field(description="Направление скролла")
    amount: int = Field(default=300, description="Количество пикселей для скролла")


class HoverAction(BaseAction):
    action_type: Literal["hover"] = "hover"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")


class PressKeyAction(BaseAction):
    action_type: Literal["press_key"] = "press_key"
    key: str = Field(description="Клавиша (Enter, Escape, Tab, ArrowDown, etc.)")


class SelectOptionAction(BaseAction):
    action_type: Literal["select_option"] = "select_option"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    text: Optional[str] = Field(default=None, description="Текст опции")
    option_value: Optional[str] = Field(default=None, description="Value опции")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")


class UploadFileAction(BaseAction):
    action_type: Literal["upload_file"] = "upload_file"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    file_path: str = Field(description="Путь к файлу для загрузки")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")

    @field_validator("file_path")
    @classmethod
    def _validate_path(cls, v: str) -> str:
        if ".." in v:
            raise ValueError('Path cannot contain ".."')
        if v.startswith("/") or v.startswith("\\") or (len(v) >= 2 and v[1] == ":"):
            raise ValueError("Absolute paths are not allowed")
        return v


class SwitchTabAction(BaseAction):
    action_type: Literal["switch_tab"] = "switch_tab"
    tab_index: int = Field(description="Индекс вкладки")


class DismissAlertAction(BaseAction):
    action_type: Literal["dismiss_alert"] = "dismiss_alert"


class AcceptAlertAction(BaseAction):
    action_type: Literal["accept_alert"] = "accept_alert"


class RightClickAction(BaseAction):
    action_type: Literal["right_click"] = "right_click"
    element_display_id: int = Field(description="ID пронумерованного элемента")
    selector: Optional[str] = Field(default=None, description="CSS-like selector для fallback")
    stable_hash: Optional[str] = Field(default=None, description="Стабильный хеш элемента для fallback")


class ScreenshotAction(BaseAction):
    action_type: Literal["screenshot"] = "screenshot"
    filename: Optional[str] = Field(default=None, description="Имя файла для скриншота")

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if ".." in v:
            raise ValueError('Filename cannot contain ".."')
        if v.startswith("/") or v.startswith("\\") or (len(v) >= 2 and v[1] == ":"):
            raise ValueError("Absolute paths are not allowed")
        return v


class WaitAction(BaseAction):
    action_type: Literal["wait"] = "wait"
    seconds: int = Field(default=2, description="Секунды ожидания")


class FinishAction(BaseAction):
    action_type: Literal["finish"] = "finish"
    summary: Optional[str] = Field(default=None, description="Итоговый ответ")


class FailAction(BaseAction):
    action_type: Literal["fail"] = "fail"
    reason: Optional[str] = Field(default=None, description="Причина неудачи")


class ActionResult(BaseModel):
    """Единый контракт результата действия."""
    status: str = Field(default="ok", description="ok | error | unchanged")
    observation: str = Field(default="", description="Что произошло")
    screenshot: Optional[str] = Field(default=None, description="Путь к скриншоту after")
    url: Optional[str] = Field(default=None, description="URL после действия")
    changed: bool = Field(default=False, description="Изменилась ли страница")
    error: Optional[str] = Field(default=None, description="Ошибка, если есть")
    action: Optional[Dict[str, Any]] = Field(default=None, description="Выполненное действие")
    before_screenshot: Optional[str] = Field(default=None, description="Путь к скриншоту before")
    after_screenshot: Optional[str] = Field(default=None, description="Путь к скриншоту after")
    diff_screenshot: Optional[str] = Field(default=None, description="Путь к diff изображению")
    used_locator: Optional[str] = Field(default=None, description="Какой locator сработал")
    fallback_used: bool = Field(default=False, description="Использован ли fallback")
    fallback_reason: Optional[str] = Field(default=None, description="Причина fallback")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Дополнительные данные")


# Discriminated union для строгой валидации
StrictAgentAction = Annotated[
    Union[
        NavigateAction,
        ClickAction,
        TypeAction,
        ScrollAction,
        HoverAction,
        PressKeyAction,
        SelectOptionAction,
        UploadFileAction,
        SwitchTabAction,
        DismissAlertAction,
        AcceptAlertAction,
        RightClickAction,
        ScreenshotAction,
        WaitAction,
        FinishAction,
        FailAction,
    ],
    Field(discriminator="action_type"),
]

_strict_action_adapter = TypeAdapter(StrictAgentAction)


def parse_strict_action(data: dict) -> BaseAction:
    """Строгая валидация действия через discriminated union."""
    return _strict_action_adapter.validate_python(data)


# Legacy AgentAction — сохраняем для обратной совместимости
class AgentAction(BaseModel):
    action_type: Literal[
        "navigate",
        "click",
        "type",
        "scroll",
        "hover",
        "press_key",
        "select_option",
        "upload_file",
        "switch_tab",
        "dismiss_alert",
        "accept_alert",
        "right_click",
        "screenshot",
        "wait",
        "assert",
        "finish",
        "fail",
    ] = Field(description="Тип действия, которое агент хочет выполнить")

    reasoning: str = Field(
        default="",
        description="Краткое объяснение, почему выбрано это действие",
    )

    url: Optional[str] = Field(default=None, description="URL для действия navigate")

    element_display_id: Optional[int] = Field(
        default=None,
        description="ID пронумерованного элемента для click/type/hover/right_click/upload_file/select_option",
    )

    selector: Optional[str] = Field(
        default=None,
        description="CSS-like selector для fallback при изменении индекса",
    )

    stable_hash: Optional[str] = Field(
        default=None,
        description="Стабильный хеш элемента для fallback при изменении индекса",
    )

    text: Optional[str] = Field(
        default=None,
        description="Текст для ввода в поле (type) или option_text (select_option)",
    )

    key: Optional[str] = Field(
        default=None,
        description="Клавиша для press_key (Enter, Escape, Tab, ArrowDown, etc.)",
    )

    option_value: Optional[str] = Field(
        default=None,
        description="Value опции для select_option",
    )

    file_path: Optional[str] = Field(
        default=None,
        description="Путь к файлу для upload_file",
    )

    @field_validator("file_path", "filename")
    @classmethod
    def _validate_path(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if ".." in v:
            raise ValueError('Path cannot contain ".."')
        if v.startswith("/") or v.startswith("\\") or (len(v) >= 2 and v[1] == ":"):
            raise ValueError("Absolute paths are not allowed")
        return v

    assert_condition: Optional[str] = Field(
        default=None,
        description="Условие assert: url_contains('/path'), element_exists('#id'), text_contains('str'), title_is('Title')",
    )

    assert_expected: Optional[str] = Field(
        default=None,
        description="Ожидаемое значение для assert (опционально)",
    )

    tab_index: Optional[int] = Field(
        default=None,
        description="Индекс вкладки для switch_tab",
    )

    direction: Optional[Literal["up", "down", "left", "right"]] = Field(
        default=None,
        description="Направление скролла",
    )

    amount: Optional[int] = Field(
        default=300,
        description="Количество пикселей для скролла",
    )

    filename: Optional[str] = Field(
        default=None,
        description="Имя файла для screenshot",
    )

    seconds: Optional[int] = Field(
        default=None,
        description="Секунды ожидания для wait",
    )

    summary: Optional[str] = Field(
        default=None,
        description="Итоговый ответ для finish",
    )

    reason: Optional[str] = Field(
        default=None,
        description="Причина неудачи для fail",
    )
