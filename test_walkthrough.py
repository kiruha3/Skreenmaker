import asyncio
import os
from src.browser import BrowserController
from src.overlay import draw_overlay


BASE_URL = "https://doca.dreamdocs.ru"
OUTPUT_DIR = "output/walkthrough"


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    browser = BrowserController()
    await browser.launch(headless=True)
    try:
        # 1. Логин
        await browser.navigate(BASE_URL)
        await asyncio.sleep(1)

        elements = await browser.get_interactive_elements()
        email_el = next((e for e in elements if "пользовател" in (e.text or "").lower() or e.display_id == 4), None)
        pass_el = next((e for e in elements if "парол" in (e.text or "").lower() or e.display_id == 5), None)
        login_btn = next((e for e in elements if "ойти" in (e.text or "").lower() or e.display_id == 7), None)

        if email_el and pass_el and login_btn:
            await browser.click_by_coords(email_el.x + email_el.width / 2, email_el.y + email_el.height / 2)
            await browser._page.keyboard.type("kiruha3@mail.ru")
            await browser.click_by_coords(pass_el.x + pass_el.width / 2, pass_el.y + pass_el.height / 2)
            await browser._page.keyboard.type("Qatwl6IcVEdZ0!")
            await browser.click_by_coords(login_btn.x + login_btn.width / 2, login_btn.y + login_btn.height / 2)
            await asyncio.sleep(2)
        else:
            print("Login elements not found!")
            return

        # 2. Скриншот дашборда после логина
        await browser.screenshot(os.path.join(OUTPUT_DIR, "00_dashboard.jpg"))
        print("Saved: 00_dashboard.jpg")

        # 3. Получаем интерактивные элементы
        dashboard_elements = await browser.get_interactive_elements()
        print(f"Found {len(dashboard_elements)} interactive elements on dashboard")

        for el in dashboard_elements:
            safe_text = "".join(c if c.isalnum() or c in "_-" else "_" for c in el.text[:30])
            label = f"{el.display_id}_{el.tag}_{safe_text}"
            path = os.path.join(OUTPUT_DIR, f"before_click_{label}.jpg")
            annotated_path = os.path.join(OUTPUT_DIR, f"annotated_before_click_{label}.jpg")

            # Сохраняем скриншот ДО клика
            await browser.screenshot(path)
            _, _ = draw_overlay(path, dashboard_elements, annotated_path)

            # Кликаем
            print(f"Clicking element {el.display_id}: [{el.tag}] '{el.text}'")
            await browser.click_by_coords(el.x + el.width / 2, el.y + el.height / 2)
            await asyncio.sleep(1.5)

            # Сохраняем скриншот ПОСЛЕ клика
            after_path = os.path.join(OUTPUT_DIR, f"after_click_{label}.jpg")
            await browser.screenshot(after_path)
            print(f"  Saved: after_click_{label}.jpg")

            # Возвращаемся на дашборд
            await browser.navigate(BASE_URL)
            await asyncio.sleep(1.5)

            # Обновляем элементы для следующей итерации
            dashboard_elements = await browser.get_interactive_elements()

        print(f"\nWalkthrough complete. {len(dashboard_elements)} elements tested.")
        print(f"Results saved to: {OUTPUT_DIR}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
