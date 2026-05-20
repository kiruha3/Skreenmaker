"""Сканирование frontend-файлов на реальные credentials и URL.

Проверяет, что в static/app.js, .tmp-build/main.js и manual_agent.py
не осталось hardcoded email/паролей или URL реальных систем.
"""
import pathlib
import re

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent

# Файлы для сканирования
SCAN_FILES = [
    PROJECT_ROOT / "static" / "app.js",
    PROJECT_ROOT / ".tmp-build" / "main.js",
    PROJECT_ROOT / "manual_agent.py",
]

# Допустимые placeholder-домены (safe)
SAFE_DOMAINS = {"example.com", "example.test", "example.org", "example.invalid", "localhost"}

# Известные реальные credentials из истории (blacklist)
CREDENTIAL_BLACKLIST = {
    "k.tretyakov@slsoft.ru",
    "v_vP5GxCva",
}

# Реальные-looking домены (pattern)
REAL_DOMAIN_RE = re.compile(r"https?://([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")

# Email-like строки
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_domains(text: str):
    """Извлечь все домены из URL."""
    return {m.group(1).lower() for m in REAL_DOMAIN_RE.finditer(text)}


def _extract_emails(text: str):
    """Извлечь все email."""
    return {m.group(0).lower() for m in EMAIL_RE.finditer(text)}


@pytest.mark.parametrize("path", SCAN_FILES, ids=lambda p: p.name)
def test_no_known_credentials(path: pathlib.Path):
    """Проверить, что известные реальные credentials отсутствуют."""
    if not path.exists():
        pytest.skip(f"Файл не найден: {path}")
    text = _read_text(path)
    found = CREDENTIAL_BLACKLIST & set(text.split())
    assert not found, f"Найдены известные credentials в {path}: {found}"


@pytest.mark.parametrize("path", SCAN_FILES, ids=lambda p: p.name)
def test_no_real_looking_emails(path: pathlib.Path):
    """Проверить, что нет email вне безопасных placeholder-доменов."""
    if not path.exists():
        pytest.skip(f"Файл не найден: {path}")
    text = _read_text(path)
    emails = _extract_emails(text)
    unsafe = {
        email for email in emails
        if not any(email.endswith(f"@{d}") for d in SAFE_DOMAINS)
    }
    assert not unsafe, f"Найдены потенциально реальные email в {path}: {unsafe}"


@pytest.mark.parametrize("path", SCAN_FILES, ids=lambda p: p.name)
def test_no_real_looking_domains(path: pathlib.Path):
    """Проверить, что URL-адреса используют только безопасные placeholder-домены."""
    if not path.exists():
        pytest.skip(f"Файл не найден: {path}")
    text = _read_text(path)
    domains = _extract_domains(text)
    unsafe = domains - SAFE_DOMAINS
    assert not unsafe, f"Найдены потенциально реальные домены в {path}: {unsafe}"
