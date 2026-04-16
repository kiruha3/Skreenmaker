import asyncio
import os
from src.browser import BrowserController
from src.overlay import draw_overlay


BASE_URL = "https://doca.dreamdocs.ru"
OUTPUT_DIR = "output/walkthrough_v2"


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    browser = BrowserController()
    await browser.launch(headless=True)
    try:
        # 1. Логин
        await browser.navigate(BASE_URL)
        await asyncio.sleep(1)

        elements = await browser.get_interactive_elements()
        # На странице логина: 4=email, 5=pass, 7=login
        email_el = next((e for e in elements if e.display_id == 4), None)
        pass_el = next((e for e in elements if e.display_id == 5), None)
        login_btn = next((e for e in elements if e.display_id == 7), None)

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

        # 2. Скриншот дашборда
        await browser.screenshot(os.path.join(OUTPUT_DIR, "00_dashboard.jpg"))
        print("Saved: 00_dashboard.jpg")

        # 3. Получаем элементы дашборда
        dashboard_elements = await browser.get_interactive_elements()
        print(f"Found {len(dashboard_elements)} interactive elements on dashboard")

        for el in dashboard_elements:
            label = f"el{el.display_id:02d}_{el.tag}"
            before_path = os.path.join(OUTPUT_DIR, f"before_click_{label}.jpg")
            annotated_path = os.path.join(OUTPUT_DIR, f"annotated_before_click_{label}.jpg")

            # Скриншот ДО клика
            await browser.screenshot(before_path)
            _, _ = draw_overlay(before_path, dashboard_elements, annotated_path)

            # Кликаем
            print(f"Clicking element {el.display_id}: [{el.tag}] '{el.text}'")
            await browser.click_by_coords(el.x + el.width / 2, el.y + el.height / 2)
            await asyncio.sleep(1.5)

            # Скриншот ПОСЛЕ клика
            after_path = os.path.join(OUTPUT_DIR, f"after_click_{label}.jpg")
            await browser.screenshot(after_path)
            print(f"  Saved: after_click_{label}.jpg")

            # Возвращаемся на дашборд (с обработкой ошибок навигации)
            for attempt in range(3):
                try:
                    await browser.navigate(BASE_URL)
                    break
                except Exception as e:
                    print(f"  Navigation retry {attempt+1}: {e}")
                    await asyncio.sleep(1)
            await asyncio.sleep(1.5)

            # Обновляем элементы
            dashboard_elements = await browser.get_interactive_elements()

        print(f"\nWalkthrough complete. Results saved to: {OUTPUT_DIR}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
