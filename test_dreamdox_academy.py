import asyncio
import os
import json
from datetime import datetime
from src.browser import BrowserController
from src.overlay import draw_overlay

BASE_URL = "http://185.112.226.84:5173"
API_BASE = "http://185.112.226.84:8000"
OUTPUT_DIR = "output/dreamdox_academy_test"
CREDENTIALS = {"email": "kiruha3@mail.ru", "password": "Qatwl6IcVEdZ0!"}

os.makedirs(OUTPUT_DIR, exist_ok=True)

report = {
    "start_time": datetime.now().isoformat(),
    "steps": [],
    "bugs": [],
}


def add_step(name, status="ok", details="", screenshot=""):
    report["steps"].append({
        "name": name,
        "status": status,
        "details": details,
        "screenshot": screenshot,
        "time": datetime.now().isoformat(),
    })


def add_bug(title, severity, description, screenshot="", module=""):
    report["bugs"].append({
        "title": title,
        "severity": severity,
        "description": description,
        "screenshot": screenshot,
        "module": module,
        "time": datetime.now().isoformat(),
    })


async def screenshot(browser, name, elements=None):
    raw_path = os.path.join(OUTPUT_DIR, f"{name}_raw.jpg")
    ann_path = os.path.join(OUTPUT_DIR, f"{name}_annotated.jpg")
    await browser.screenshot(raw_path)
    if elements is not None:
        draw_overlay(raw_path, elements, ann_path)
    return raw_path, ann_path if elements is not None else raw_path


async def find_el(elements, **kwargs):
    for e in elements:
        match = True
        for k, v in kwargs.items():
            if k == "text_contains":
                if v.lower() not in e.text.lower():
                    match = False
                    break
            elif k == "text_equals":
                if e.text.strip() != v.strip():
                    match = False
                    break
            elif k == "tag":
                if e.tag != v:
                    match = False
                    break
            elif getattr(e, k, None) != v:
                match = False
                break
        if match:
            return e
    return None


async def click_el(browser, el):
    if el:
        await browser.click_by_coords(el.x + el.width / 2, el.y + el.height / 2)
        return True
    return False


async def wait_and_screenshot(browser, name, delay=1.5):
    await asyncio.sleep(delay)
    els = await browser.get_interactive_elements()
    raw, ann = await screenshot(browser, name, els)
    return raw, ann, els


async def main():
    browser = BrowserController(viewport_width=1280, viewport_height=900)
    await browser.launch(headless=True)
    try:
        # 1. Переход на логин напрямую
        await browser.navigate(f"{BASE_URL}/login")
        raw, ann, els = await wait_and_screenshot(browser, "01_login_page")
        add_step("Страница логина", screenshot=raw)

        # 2. Ввод credentials через Playwright fill
        await browser._page.fill('input[type="email"]', CREDENTIALS["email"])
        await browser._page.fill('input[type="password"]', CREDENTIALS["password"])
        await asyncio.sleep(0.5)
        raw, ann, els = await wait_and_screenshot(browser, "02_login_filled")
        add_step("Логин заполнен", screenshot=raw)

        # 3. Отправка формы
        await browser._page.click('button[type="submit"]')
        await asyncio.sleep(2.5)
        raw, ann, els = await wait_and_screenshot(browser, "03_after_login")
        add_step("После логина", screenshot=raw)

        # Проверка что залогинились
        page_text = await browser._page.evaluate("() => document.body.innerText")
        if "Войти" in page_text and "Академия DreamDocs" in page_text and "kiruha3" not in page_text.lower():
            add_bug("Логин не работает", "critical", "После отправки формы логина пользователь остаётся неавторизованным.", screenshot=raw, module="auth")

        # 4. Дашборд
        await browser.navigate(f"{BASE_URL}/dashboard")
        raw, ann, els = await wait_and_screenshot(browser, "04_dashboard")
        add_step("Дашборд", screenshot=raw)

        # 5. Курсы
        await browser.navigate(f"{BASE_URL}/courses")
        raw, ann, els = await wait_and_screenshot(browser, "05_courses_list")
        add_step("Список курсов", screenshot=raw)

        # 6. Открываем DreamDocs
        dream_link = await find_el(els, text_contains="DreamDocs")
        if not dream_link:
            dream_link = await find_el(els, text_contains="Подробнее")
        if dream_link:
            await click_el(browser, dream_link)
            raw, ann, els = await wait_and_screenshot(browser, "06_course_dreamdocs")
            add_step("Курс DreamDocs", screenshot=raw)
        else:
            add_step("Курс DreamDocs", status="warn", details="Не найдена ссылка")

        # 7. Скроллим вниз чтобы увидеть модули
        await browser.scroll("down", 300)
        raw, ann, els = await wait_and_screenshot(browser, "07_course_scrolled")
        add_step("Курс DreamDocs (прокрутка)", screenshot=raw)

        # 8. Ищем модуль теста и кликаем "Начать тест" или "Подробнее"
        quiz_found = False
        for e in els:
            if "тест" in e.text.lower() or "quiz" in e.text.lower():
                # Это может быть название модуля, кликнем по нему чтобы раскрыть
                await click_el(browser, e)
                await asyncio.sleep(1.5)
                raw, ann, els_inner = await wait_and_screenshot(browser, "08_quiz_opened")
                add_step("Модуль теста раскрыт", screenshot=raw)
                quiz_found = True

                # Ищем "Начать тест"
                start_btn = await find_el(els_inner, text_contains="Начать")
                if start_btn:
                    await click_el(browser, start_btn)
                    await asyncio.sleep(2)
                    raw, ann, els_q = await wait_and_screenshot(browser, "09_quiz_started")
                    add_step("Тест начат", screenshot=raw)

                    # Выбираем первый radio
                    radios = [x for x in els_q if x.tag == "input"]
                    if radios:
                        await click_el(browser, radios[0])
                        await asyncio.sleep(0.8)
                        raw, ann, els_q2 = await wait_and_screenshot(browser, "10_quiz_answered")
                        add_step("Ответ выбран", screenshot=raw)

                    # Жмем "Завершить"
                    finish_btn = await find_el(els_q, text_contains="Завершить")
                    if finish_btn:
                        await click_el(browser, finish_btn)
                        await asyncio.sleep(2.5)
                        raw, ann, els_fin = await wait_and_screenshot(browser, "11_quiz_finished")
                        add_step("Тест завершен", screenshot=raw)
                        txt = await browser._page.evaluate("() => document.body.innerText")
                        if "Балл" not in txt and "Тест завершён" not in txt and "Результат" not in txt:
                            add_bug("Результаты теста не отображаются", "high", "После завершения теста не появился экран с баллом.", screenshot=raw, module="quiz")
                else:
                    add_step("Тест", status="warn", details="Кнопка 'Начать тест' не найдена внутри модуля")
                break

        if not quiz_found:
            add_step("Тест", status="warn", details="Модуль теста не найден")

        # 12. Возврат к курсу
        await browser.navigate(f"{BASE_URL}/courses/4")
        raw, ann, els = await wait_and_screenshot(browser, "12_back_to_course")
        add_step("Возврат к курсу", screenshot=raw)

        # 13. Ищем книгу
        book_found = False
        for e in els:
            if "книга" in e.text.lower() or "book" in e.text.lower():
                await click_el(browser, e)
                await asyncio.sleep(2)
                raw, ann, els_b = await wait_and_screenshot(browser, "13_book_opened")
                add_step("Книга открыта", screenshot=raw)
                book_found = True
                txt = await browser._page.evaluate("() => document.body.innerText")
                if "Загрузка книги" in txt:
                    add_bug("Книга зависает в загрузке", "medium", "Книга показывает 'Загрузка книги...' бесконечно.", screenshot=raw, module="book")
                break
        if not book_found:
            add_step("Книга", status="warn", details="Модуль книги не найден")

        # 14. Возврат
        await browser.navigate(f"{BASE_URL}/courses/4")
        raw, ann, els = await wait_and_screenshot(browser, "14_course_after_book")
        add_step("Курс после книги", screenshot=raw)

        # 15. Форум
        forum_found = False
        for e in els:
            if "форум" in e.text.lower() or "forum" in e.text.lower():
                await click_el(browser, e)
                await asyncio.sleep(2)
                raw, ann, els_f = await wait_and_screenshot(browser, "15_forum_opened")
                add_step("Форум открыт", screenshot=raw)
                forum_found = True
                break
        if not forum_found:
            add_step("Форум", status="warn", details="Модуль форума не найден")

        # 16. Проверка прогресса на странице курса
        await browser.navigate(f"{BASE_URL}/courses/4")
        raw, ann, els = await wait_and_screenshot(browser, "16_course_progress")
        add_step("Проверка прогресса", screenshot=raw)
        txt = await browser._page.evaluate("() => document.body.innerText")
        if "Прогресс" not in txt:
            add_bug("Прогресс-бар отсутствует", "medium", "На странице курса не отображается прогресс-бар.", screenshot=raw, module="course_detail")

        # 17. Car Repair
        await browser.navigate(f"{BASE_URL}/courses")
        raw, ann, els = await wait_and_screenshot(browser, "17_courses_list_2")
        add_step("Список курсов (повторно)", screenshot=raw)
        car_link = await find_el(els, text_contains="Car Repair")
        if not car_link:
            car_link = await find_el(els, text_contains="ремонт")
        if car_link:
            await click_el(browser, car_link)
            raw, ann, els = await wait_and_screenshot(browser, "18_car_repair")
            add_step("Курс Car Repair", screenshot=raw)
        else:
            add_step("Car Repair", status="warn", details="Курс не найден в списке")

    except Exception as e:
        add_step("Critical error", status="error", details=str(e))
        try:
            els = await browser.get_interactive_elements()
            raw, _ = await screenshot(browser, "99_error", els)
            add_bug("Критическая ошибка тестирования", "critical", str(e), screenshot=raw)
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
