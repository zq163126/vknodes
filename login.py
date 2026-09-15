import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

def send_telegram_notification(caption_text, image_path=None):
    """
    通过 Telegram Bot 将登录/操作状态及截图发送给用户。
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
    模拟真实的鼠标移动到目标元素上（登录按钮）。
    在按钮内部的合理范围内（30% - 70% 区域）随机生成点击坐标，
    并配合随机步长移动，以绕过固定坐标检测。
    """
    element = await page.wait_for_selector(selector)
    box = await element.bounding_box()
    if not box:
        raise Exception(f"无法获取元素 {selector} 的边界框坐标。")
    
    target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
    target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)

    print(f"正在模拟鼠标平滑移动至目标按钮（随机坐标）: ({target_x:.2f}, {target_y:.2f})")
    
    card_element = await page.wait_for_selector('article.auth-card')
    card_box = await card_element.bounding_box()
    
    start_x = card_box['x'] + random.uniform(20, 80)
    start_y = card_box['y'] + random.uniform(20, 80)
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.2, 0.4))

    steps = random.randint(12, 20)
    for i in range(steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps) + random.uniform(-1, 1)
        curr_y = start_y + (target_y - start_y) * (i / steps) + random.uniform(-1, 1)
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(random.uniform(0.015, 0.035))

    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(random.uniform(0.3, 0.6))

    await page.mouse.click(target_x, target_y)
    print("已成功在随机坐标执行点击操作。")

async def simulate_renew_server_click(page):
    """
    模拟鼠标从容器区域划入、在 Renew Server 按钮区域动态寻优/移动并随机点击，
    配合滚动与真实鼠标移动事件，联动页面 --core-x/--core-y 变化。
    """
    selector = 'a[href*="/renewal-costs?server="]'
    element = await page.wait_for_selector(selector, state="visible", timeout=10000)
    await element.scroll_into_view_if_needed()
    box = await element.bounding_box()
    if not box:
        raise Exception("无法获取 Renew Server 按钮的边界框坐标。")

    card_element = await page.query_selector('section.v31-server-overview')
    c_box = None
    if card_element:
        await card_element.scroll_into_view_if_needed()
        c_box = await card_element.bounding_box()

    target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
    target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
    print(f"正在模拟鼠标移动至 Renew Server 按钮（随机坐标）: ({target_x:.2f}, {target_y:.2f})")

    if c_box:
        start_x = c_box['x'] + random.uniform(20, c_box['width'] * 0.4)
        start_y = c_box['y'] + random.uniform(20, c_box['height'] * 0.4)
    else:
        start_x, start_y = target_x - 100, target_y - 50

    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.2, 0.4))

    steps = random.randint(15, 25)
    for i in range(steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps) + random.uniform(-1.5, 1.5)
        curr_y = start_y + (target_y - start_y) * (i / steps) + random.uniform(-1.5, 1.5)
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(random.uniform(0.015, 0.03))

    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(random.uniform(0.3, 0.6))

    await page.mouse.click(target_x, target_y)
    print("已成功点击 Renew Server 按钮。")

async def simulate_renew_free_click(page):
    """
    模拟鼠标从临近区域移动至 Renew for FREE 按钮的内部随机点并点击，
    契合 --core-x / --core-y 联动与防机器人校验。
    """
    selector = 'button.renewal-primary-action'
    element = await page.wait_for_selector(selector, state="visible", timeout=10000)
    await element.scroll_into_view_if_needed()
    box = await element.bounding_box()
    if not box:
        raise Exception("无法获取 Renew for FREE 按钮的边界框坐标。")

    target_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
    target_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
    print(f"正在模拟鼠标移动至 Renew for FREE 按钮（随机坐标）: ({target_x:.2f}, {target_y:.2f})")

    # 尝试寻找父级表单或卡片作为起点
    form_element = await page.query_selector('form')
    c_box = None
    if form_element:
        c_box = await form_element.bounding_box()

    if c_box:
        start_x = c_box['x'] + random.uniform(20, c_box['width'] * 0.4)
        start_y = c_box['y'] + random.uniform(20, c_box['height'] * 0.4)
    else:
        start_x, start_y = target_x - 100, target_y - 50

    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(random.uniform(0.2, 0.4))

    steps = random.randint(15, 25)
    for i in range(steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps) + random.uniform(-1.5, 1.5)
        curr_y = start_y + (target_y - start_y) * (i / steps) + random.uniform(-1.5, 1.5)
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(random.uniform(0.015, 0.03))

    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(random.uniform(0.3, 0.6))

    await page.mouse.click(target_x, target_y)
    print("已成功点击 Renew for FREE 按钮。")

async def main():
    target_url = os.environ.get("TARGET_URL")
    account_user = os.environ.get("ACCOUNT_USER")
    account_pass = os.environ.get("ACCOUNT_PASS")

    if not target_url or not account_user or not account_pass:
        raise ValueError("请确保已正确配置环境变量: TARGET_URL, ACCOUNT_USER, ACCOUNT_PASS")

    login_screenshot_path = "login_status.png"
    renew_screenshot_path = "renew_status.png"
    final_screenshot_path = "final_status.png"
    
    login_status_msg = ""
    renew_status_msg = ""
    final_status_msg = ""

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
            # === 保持登录部分绝对不变 ===
            print("正在打开目标登录页面...")
            await page.goto(target_url, wait_until="networkidle")

            print("正在填写邮箱...")
            email_input = await page.wait_for_selector('input[name="email"]')
            await email_input.fill(account_user)
            await asyncio.sleep(random.uniform(0.4, 0.8))

            print("正在填写密码...")
            password_input = await page.wait_for_selector('input[name="password"]')
            await password_input.fill(account_pass)
            await asyncio.sleep(random.uniform(0.4, 0.8))

            print("正在勾选法律条款确认框...")
            checkbox = await page.wait_for_selector('input[name="accept_legal"]')
            if not await checkbox.is_checked():
                await checkbox.click()
            await asyncio.sleep(random.uniform(0.4, 0.8))

            print("开始执行随机鼠标轨迹与点击提交...")
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
            # ==========================

            # 登录状态截图并发送
            await page.screenshot(path=login_screenshot_path, full_page=True)
            send_telegram_notification(login_status_msg, login_screenshot_path)

            # === 登录成功后延时 4 秒再做下一步 ===
            print("登录成功，等待 4 秒进行后续面板加载...")
            await asyncio.sleep(4)

            # === 查找并点击 Renew Server 按钮 ===
            try:
                print("尝试查找并点击 Renew Server 按钮...")
                await simulate_renew_server_click(page)
                
                # 点击完 Renew Server 按钮后延时 4 秒再截图发送 telegram
                print("已点击 Renew Server 按钮，等待 4 秒后截图...")
                await asyncio.sleep(4)
                
                renew_status_msg = "成功找到并点击了 Renew Server 按钮。"
                print(renew_status_msg)
            except Exception as e:
                renew_status_msg = f"查找或点击 Renew Server 失败: {str(e)}"
                print(renew_status_msg)
                await asyncio.sleep(4)

            # Renew Server 操作后截图并发送
            await page.screenshot(path=renew_screenshot_path, full_page=True)
            send_telegram_notification(renew_status_msg, renew_screenshot_path)

            # === 查找并点击 Renew for FREE 按钮 ===
            try:
                print("尝试查找并点击 Renew for FREE 按钮...")
                await simulate_renew_free_click(page)
                
                # 点击完 Renew for FREE 按钮后延时 4 秒再截图发送 telegram
                print("已点击 Renew for FREE 按钮，等待 4 秒后截图...")
                await asyncio.sleep(4)
                
                final_status_msg = "成功找到并点击了 Renew for FREE 按钮。"
                print(final_status_msg)
            except Exception as e:
                final_status_msg = f"查找或点击 Renew for FREE 失败: {str(e)}"
                print(final_status_msg)
                await asyncio.sleep(4)

            # 最终操作后截图并发送
            await page.screenshot(path=final_screenshot_path, full_page=True)
            send_telegram_notification(final_status_msg, final_screenshot_path)
            # ======================================

        except Exception as e:
            err_msg = f"整体流程执行异常: {str(e)}"
            print(err_msg)
            await page.screenshot(path=login_screenshot_path, full_page=True)
            send_telegram_notification(err_msg, login_screenshot_path)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
