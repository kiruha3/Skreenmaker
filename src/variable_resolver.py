import re
from typing import Dict, Any, List


VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def resolve_variables(text: str, variables: Dict[str, str]) -> str:
    """Заменяет ${name} на значение из словаря переменных.

    Если переменная не найдена — оставляет оригинальный плейсхолдер.
    None и пустая строка возвращаются как есть.
    """
    if not text:
        return text

    def replacer(match):
        key = match.group(1)
        return variables.get(key, match.group(0))

    return VAR_PATTERN.sub(replacer, text)


def resolve_step(step: Dict[str, Any], variables: Dict[str, str]) -> Dict[str, Any]:
    """Применяет интерполяцию ко всем строковым полям шага сценария.

    Немутирующая функция — возвращает новый dict.
    """
    resolved = {}
    for key, value in step.items():
        if isinstance(value, str):
            resolved[key] = resolve_variables(value, variables)
        else:
            resolved[key] = value
    return resolved


def resolve_steps(steps: List[Dict[str, Any]], variables: Dict[str, str]) -> List[Dict[str, Any]]:
    """Применяет интерполяцию переменных ко всем шагам сценария."""
    return [resolve_step(s, variables) for s in steps]
