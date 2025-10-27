# get_cookies.py
# 获取B站登录cookies的脚本
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# 使用相对路径
COOKIE_FILE = Path(__file__).parent / "cookies.json"

async def save_cookies():
    async with async_playwright() as p:
        # 启动浏览器，headless=False 可以看到二维码
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        print("正在打开 B站登录页，请在浏览器中扫码登录...")

        await page.goto("https://passport.bilibili.com/login", wait_until="domcontentloaded")

        # 等待登录成功，跳转到主页，最长等待 2 分钟
        try:
            await page.wait_for_url("https://www.bilibili.com/", timeout=120000)
            print("登录成功，正在获取 cookie...")
        except Exception as e:
            print("登录超时或出错:", e)
            await browser.close()
            return

        cookies = await context.cookies()
        # 确保目录存在
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        print(f"✅ cookie 已保存到 {COOKIE_FILE}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(save_cookies())