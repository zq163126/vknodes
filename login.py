import asyncio
import os
import requests
from playwright.async_api import async_playwright

def send_telegram_notification(caption_text, image_path=None):
    """
    通过 Telegram Bot 将登录状态及截图发送给用户。
    消息开头强制带有 “[vknodes]” 字样。
    """
    bot_token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")

    if not bot_token or not chat_id:
        print("未配置 Telegram 凭证 (TG_BOT_TOKEN 或 TG_CHAT_ID)，跳过消息推送。")
        return

    formatted_caption = f"[vknodes] {caption_text}"

    try:
        if image_path and os.path.exists(image_path):
            # 发送带图消息
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            with open(image_path, "rb") as photo:
                files = {"photo": photo}
                data = {"chat_id": chat_id, "caption": formatted_caption}
                response = requests.post(url, data=data, files=files, timeout=30)
            result = response.json()
            if result.get("ok"):
                print("Telegram 截图通知发送成功。")
            else:
                print(f"Telegram 发送失败: {result}")
        else:
            # 仅发送纯文本消息
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": formatted_caption}
            response = requests.post(url, data=data, timeout=30)
            if response.json().get("ok"):
                print("Telegram 文本通知发送成功。")
            else:
                print(f"Telegram 发送失败: {response.json()}")
    except Exception as e:
        print(f"发送 Telegram 通知时发生异常: {e}")

async def simulate_mouse_move_and_click(page, selector):
    """
    模拟真实的鼠标移动到目标元素上，并根据页面特殊的 CSS 变量 --core-x 和 --core-y 
    触发对应的坐标悬停和点击，以完美契合前端防机器人坐标校验机制。
    """
    element = await page.wait_for_selector(selector)
    box = await element.bounding_box()
    if not box:
        raise Exception(f"无法获取元素 {selector} 的边界框坐标。")
    
    target_x = box['x'] + box['width'] * 0.5
    target_y = box['y'] + box['height'] * 0.5

    print(f"正在模拟鼠标平滑移动至目标按钮: ({target_x}, {target_y})")
    
    card_element = await page.wait_for_selector('article.auth-card')
    card_box = await card_element.bounding_box()
    
    start_x = card_box['x'] + 50
    start_y = card_box['y'] + 50
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(0.3)

    steps = 15
    for i in range(steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps)
        curr_y = start_y + (target_y - start_y) * (i / steps)
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(0.02)

    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(0.5)

    await page.mouse.click(target_x, target_y)
    print("已成功在目标坐标执行点击操作。")

async def main():
    target_url = os.environ.get("TARGET_URL")
    account_user = os.environ.get("ACCOUNT_USER")
    account_pass = os.environ.get("ACCOUNT_PASS")

    if not target_url or not account_user or not account_pass:
        raise ValueError("请确保已正确配置环境变量: TARGET_URL, ACCOUNT_USER, ACCOUNT_PASS")

    screenshot_path = "login_status.png"
    login_status_msg = ""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1536, "height": 864},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        try:
            print("正在打开目标登录页面...")
            await page.goto(target_url, wait_until="networkidle")

            print("正在填写邮箱...")
            email_input = await page.wait_for_selector('input[name="email"]')
            await email_input.fill(account_user)
            await asyncio.sleep(0.5)

            print("正在填写密码...")
            password_input = await page.wait_for_selector('input[name="password"]')
            await password_input.fill(account_pass)
            await asyncio.sleep(0.5)

            print("正在勾选法律条款确认框...")
            checkbox = await page.wait_for_selector('input[name="accept_legal"]')
            if not await checkbox.is_checked():
                await checkbox.click()
            await asyncio.sleep(0.5)

            print("开始执行鼠标模拟与点击提交...")
            await simulate_mouse_move_and_click(
                page, 
                'button.button.button-primary.vf-signin-button.auth-submit'
            )

            # 等待跳转或检查结果
            try:
                await page.wait_for_url("**/dashboard**", timeout=10000)
                login_status_msg = "登录成功！已成功跳转至后台控制面板。"
                print(login_status_msg)
            except Exception:
                login_status_msg = f"登录后未检测到预期跳转，当前页面 URL: {page.url}"
                print(login_status_msg)

        except Exception as e:
            login_status_msg = f"登录流程执行出错异常: {str(e)}"
            print(login_status_msg)
        
        finally:
            # 无论成功失败，均对当前页面进行截图保存
            await page.screenshot(path=screenshot_path, full_page=True)
            await browser.close()

    # 触发 Telegram 通知推送
    send_telegram_notification(login_status_msg, screenshot_path)

if __name__ == "__main__":
    asyncio.run(main())
