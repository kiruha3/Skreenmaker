from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


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
