import asyncio
import os
from src.browser import BrowserController
from src.page_parser import extract_page_context, format_page_context
from src.llm_client import create_llm


async def main():
    os.makedirs("output/phase2", exist_ok=True)
    browser = BrowserController()
    await browser.launch(headless=True)
    try:
        await browser.navigate("https://example.com")

        # Тест page_parser
        ctx = await extract_page_context(browser._page)
        print("=== Page Context ===")
        print(format_page_context(ctx))

        # Тест создания LLM (OpenAI fallback)
        try:
            llm = create_llm("openai", api_key=os.environ.get("OPENAI_API_KEY", "dummy"))
            print(f"\nLLM created: {type(llm).__name__}")
        except ValueError as e:
            print(f"\nLLM creation skipped (no key): {e}")

        # Тест Ollama LLM creation
        try:
            ollama = create_llm("ollama")
            print(f"Ollama LLM created: {type(ollama).__name__}")
        except Exception as e:
            print(f"Ollama creation error: {e}")

    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
