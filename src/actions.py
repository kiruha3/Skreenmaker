from typing import Literal, Optional
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    action_type: Literal[
        "navigate",
        "click",
        "type",
        "scroll",
        "screenshot",
        "wait",
        "finish",
        "fail",
    ] = Field(description="Тип действия, которое агент хочет выполнить")

    reasoning: str = Field(
        default="",
        description="Краткое объяснение, почему выбрано это действие",
    )

    url: Optional[str] = Field(
        default=None,
        description="URL для действия navigate",
    )

    element_id: Optional[int] = Field(
        default=None,
        description="ID пронумерованного элемента для click/type",
    )

    text: Optional[str] = Field(
        default=None,
        description="Текст для ввода в поле (type)",
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
