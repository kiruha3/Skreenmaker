import asyncio
import os
import json
from datetime import datetime
from src.browser import BrowserController
from src.overlay import draw_overlay

BASE_URL = "http://185.112.226.84:5173"
OUTPUT_DIR = "output/dreamdox_academy_test_v3"
CREDENTIALS = {"email": "kiruha3@mail.ru", "password": "Qatwl6IcVEdZ0!"}

os.makedirs(OUTPUT_DIR, exist_ok=True)

report = {
    "start_time": datetime.now().isoformat(),
    "steps": [],
    "bugs": [],
}


def add_step(name, status="ok", details="", screenshot=""):
    report["steps"].append({
        "name": name, "status": status, "details": details,
        "screenshot": screenshot, "time": datetime.now().isoformat(),
    })


def add_bug(title, severity, description, screenshot="", module=""):
    report["bugs"].append({
        "title": title, "severity": severity, "description": description,
        "screenshot": screenshot, "module": module, "time": datetime.now().isoformat(),
    })


async def ss(browser, name, elements=None):
    raw = os.path.join(OUTPUT_DIR, f"{name}_raw.jpg")
    ann = os.path.join(OUTPUT_DIR, f"{name}_annotated.jpg")
    await browser.screenshot(raw)
    if elements is not None:
        draw_overlay(raw, elements, ann)
    return raw, ann if elements is not None else raw


async def safe_click(browser, selector_or_text, by="text", timeout=3000):
    try:
        page = browser._page
        if by == "text":
            await page.get_by_text(selector_or_text, exact=False).first.click(timeout=timeout)
        elif by == "role":
            role, name = selector_or_text
            await page.get_by_role(role, name=name).first.click(timeout=timeout)
        else:
            await page.locator(selector_or_text).first.click(timeout=timeout)
        await asyncio.sleep(1.2)
        return True
    except Exception as e:
        return False


async def click_quiz_start(page, quiz_name="Быстрая самопроверка", timeout=3000):
    """Click the 'Начать тест' button inside a specific quiz module."""
    try:
        locator = page.locator(f'.module-item:has-text("{quiz_name}") button:has-text("Начать тест")')
        await locator.click(timeout=timeout)
        await asyncio.sleep(1.5)
        return True
    except Exception:
        # fallback 1: any visible 'Начать тест' button
        try:
            await page.locator('button:has-text("Начать тест")').first.click(timeout=timeout)
            await asyncio.sleep(1.5)
            return True
        except Exception:
            # fallback 2: dispatch click event via JS
            try:
                await page.evaluate(f"""
                    () => {{
                        const mod = Array.from(document.querySelectorAll('.module-item')).find(el => el.innerText.includes('{quiz_name}'));
                        if (mod) {{
                            const btn = mod.querySelector('button');
                            if (btn) {{ btn.click(); return true; }}
                        }}
                        const btn = document.querySelector('button');
                        if (btn) {{ btn.click(); return true; }}
                        return false;
                    }}
                """)
                await asyncio.sleep(1.5)
                return True
            except Exception:
                return False


async def main():
    browser = BrowserController(viewport_width=1280, viewport_height=900)
    await browser.launch(headless=True)
    page = browser._page
    try:
        # 1. Login
        await browser.navigate(f"{BASE_URL}/login")
        await asyncio.sleep(1)
        await page.fill('input[type="email"]', CREDENTIALS["email"])
        await page.fill('input[type="password"]', CREDENTIALS["password"])
        await page.click('button[type="submit"]')
        await asyncio.sleep(2.5)
        els = await browser.get_interactive_elements()
        raw, _ = await ss(browser, "01_after_login", els)
        add_step("Логин", screenshot=raw)

        # 2. Dashboard
        await browser.navigate(f"{BASE_URL}/dashboard")
        await asyncio.sleep(2)
        els = await browser.get_interactive_elements()
        raw, _ = await ss(browser, "02_dashboard", els)
        add_step("Дашборд", screenshot=raw)

        # 3. Courses
        await browser.navigate(f"{BASE_URL}/courses")
        await asyncio.sleep(2)
        els = await browser.get_interactive_elements()
        raw, _ = await ss(browser, "03_courses", els)
        add_step("Курсы", screenshot=raw)

        # 4. DreamDocs
        await safe_click(browser, "DreamDocs", by="text")
        await asyncio.sleep(2)
        els = await browser.get_interactive_elements()
        raw, _ = await ss(browser, "04_dreamdocs_top", els)
        add_step("DreamDocs (верх)", screenshot=raw)

        # Скроллим вниз
        await browser.scroll("down", 400)
        await asyncio.sleep(1)
        raw, _ = await ss(browser, "05_dreamdocs_scrolled", None)
        add_step("DreamDocs (скролл)", screenshot=raw)

        # Получаем список всех модулей через evaluate
        modules_info = await page.evaluate("""
            () => {
                const items = [];
                document.querySelectorAll('.module-item').forEach((el, idx) => {
                    const name = el.querySelector('.mod-name')?.innerText || '';
                    const type = el.querySelector('.mod-type')?.innerText || '';
                    const completed = el.classList.contains('completed');
                    items.push({idx, name, type, completed});
                });
                return items;
            }
        """)
        add_step("Модули DreamDocs", details=json.dumps(modules_info, ensure_ascii=False))

        # 5. Тестируем книгу
        book_ok = await safe_click(browser, "Теория: введение в DreamDocs", by="text")
        if book_ok:
            await asyncio.sleep(2)
            raw, _ = await ss(browser, "06_book_opened", None)
            add_step("Книга открыта", screenshot=raw)
            txt = await page.evaluate("() => document.body.innerText")
            if "Загрузка книги" in txt and "Глава" not in txt:
                add_bug("Книга не загружается", "medium", "Показывается 'Загрузка книги...' без содержимого.", screenshot=raw, module="book")
        else:
            add_step("Книга", status="warn", details="Не удалось кликнуть")

        # Возврат к курсу
        await browser.navigate(f"{BASE_URL}/courses/4")
        await asyncio.sleep(2)
        await browser.scroll("down", 500)
        await asyncio.sleep(1)
        raw, _ = await ss(browser, "07_dreamdocs_modules", None)
        add_step("DreamDocs модули", screenshot=raw)

        # 6. Ищем и открываем тест
        test_clicked = False
        for keyword in ["Самопроверка", "Проверка знаний", "Итоговый тест", "Тест"]:
            if await safe_click(browser, keyword, by="text"):
                test_clicked = True
                break
        if test_clicked:
            await asyncio.sleep(2)
            raw, _ = await ss(browser, "08_quiz_opened", None)
            add_step("Тест раскрыт", screenshot=raw)

            # Improved click on start button
            start_ok = await click_quiz_start(page, quiz_name="Быстрая самопроверка")
            if start_ok:
                # Wait for Vue to react
                await asyncio.sleep(2)
                raw, _ = await ss(browser, "09_quiz_started", None)
                add_step("Тест начат", screenshot=raw)

                # Verify we are in attempt mode
                try:
                    in_attempt = await page.locator('.quiz-attempt').is_visible(timeout=2000)
                except Exception:
                    in_attempt = False
                if not in_attempt:
                    add_step("Тест начат", status="warn", details="Кнопка нажата, но тест не перешел в режим попытки")
                else:
                    # Отвечаем на все вопросы
                    try:
                        while True:
                            radios = await page.locator('input[type="radio"]').all()
                            if radios:
                                await radios[0].click()
                                await asyncio.sleep(0.5)
                            # check for finish button
                            finish_btn = page.get_by_text("Завершить тест", exact=False)
                            if await finish_btn.is_visible(timeout=1500):
                                break
                            # click next
                            next_btn = page.get_by_text("Далее", exact=False)
                            if await next_btn.is_visible(timeout=1500):
                                await next_btn.click()
                                await asyncio.sleep(1)
                            else:
                                break
                        raw, _ = await ss(browser, "10_quiz_answered", None)
                        add_step("Ответы выбраны", screenshot=raw)
                    except Exception as e:
                        add_step("Выбор ответа", status="warn", details=str(e))

                    # Завершаем
                    finish_ok = await safe_click(browser, "Завершить тест", by="text")
                    if finish_ok:
                        await asyncio.sleep(2.5)
                        raw, _ = await ss(browser, "11_quiz_finished", None)
                        add_step("Тест завершён", screenshot=raw)
                        txt = await page.evaluate("() => document.body.innerText")
                        if "Балл" not in txt and "Тест завершён" not in txt and "Результат" not in txt:
                            add_bug("Результаты теста не видны", "high", "После завершения теста нет экрана с результатами.", screenshot=raw, module="quiz")
                    else:
                        add_step("Завершение теста", status="warn", details="Кнопка 'Завершить тест' не найдена")
            else:
                add_step("Начало теста", status="warn", details="Кнопка 'Начать тест' не найдена")
        else:
            add_step("Тест", status="warn", details="Не найден модуль теста по ключевым словам")

        # 7. Проверка прогресса после теста
        await browser.navigate(f"{BASE_URL}/courses/4")
        await asyncio.sleep(2)
        await browser.scroll("down", 300)
        await asyncio.sleep(1)
        raw, _ = await ss(browser, "12_progress_after_quiz", None)
        add_step("Прогресс после теста", screenshot=raw)
        txt = await page.evaluate("() => document.body.innerText")
        if "Прогресс" not in txt:
            add_bug("Прогресс-бар отсутствует", "medium", "Не найден текст 'Прогресс' на странице курса.", screenshot=raw, module="course_detail")

        # 8. Car Repair через прямой URL (course 72)
        await browser.navigate(f"{BASE_URL}/courses/72")
        await asyncio.sleep(2)
        raw, _ = await ss(browser, "13_car_repair", None)
        add_step("Car Repair", screenshot=raw)
        txt = await page.evaluate("() => document.body.innerText")
        if "404" in txt or "не найден" in txt.lower() or "not found" in txt.lower():
            add_bug("Курс Car Repair недоступен", "medium", "Переход на /courses/72 показывает ошибку или 404.", screenshot=raw, module="course")
        elif "записаться" in txt.lower() or "enrol" in txt.lower():
            add_bug("Car Repair требует записи", "low", "Пользователь не заэнроллен в курс 72.", screenshot=raw, module="course")
        elif "В этом курсе пока нет материалов" in txt:
            add_step("Car Repair пустой", status="warn", details="Курс отображается как пустой")
        elif "модул" not in txt.lower() and "раздел" not in txt.lower():
            add_bug("Курс Car Repair пустой", "medium", "Страница курса 72 не содержит модулей или разделов.", screenshot=raw, module="course")

        # 14. Forum на DreamDocs
        await browser.navigate(f"{BASE_URL}/courses/4")
        await asyncio.sleep(2)
        await browser.scroll("down", 600)
        await asyncio.sleep(1)
        forum_ok = await safe_click(browser, "Обсуждения", by="text")
        if not forum_ok:
            forum_ok = await safe_click(browser, "Форум", by="text")
        if forum_ok:
            await asyncio.sleep(2)
            raw, _ = await ss(browser, "14_forum_opened", None)
            add_step("Форум открыт", screenshot=raw)
        else:
            add_step("Форум", status="warn", details="Не найден модуль форума")

    except Exception as e:
        add_step("Critical error", status="error", details=str(e))
        try:
            raw, _ = await ss(browser, "99_error", await browser.get_interactive_elements())
            add_bug("Критическая ошибка", "critical", str(e), screenshot=raw)
        except Exception:
            pass
    finally:
        await browser.close()

    report["end_time"] = datetime.now().isoformat()
    report_path = os.path.join(OUTPUT_DIR, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
