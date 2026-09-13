import asyncio
import os
from playwright.async_api import async_playwright

async def simulate_mouse_move_and_click(page, selector):
    """
    模拟真实的鼠标移动到目标元素上，并根据页面特殊的 CSS 变量 --core-x 和 --core-y 
    触发对应的坐标悬停和点击，以完美契合前端防机器人坐标校验机制。
    """
    element = await page.wait_for_selector(selector)
    box = await element.bounding_box()
    if not box:
        raise Exception(f"无法获取元素 {selector} 的边界框坐标。")
    
    # 计算目标元素的中心点或合适位置的全局页面坐标
    target_x = box['x'] + box['width'] * 0.5
    target_y = box['y'] + box['height'] * 0.5

    print(f"正在模拟鼠标平滑移动至目标按钮: ({target_x}, {target_y})")
    
    # 获取卡片区域模拟鼠标划入
    card_element = await page.wait_for_selector('article.auth-card')
    card_box = await card_element.bounding_box()
    
    start_x = card_box['x'] + 50
    start_y = card_box['y'] + 50
    await page.mouse.move(start_x, start_y)
    await asyncio.sleep(0.3)

    # 模拟平滑划向目标按钮
    steps = 15
    for i in range(steps + 1):
        curr_x = start_x + (target_x - start_x) * (i / steps)
        curr_y = start_y + (target_y - start_y) * (i / steps)
        await page.mouse.move(curr_x, curr_y)
        await asyncio.sleep(0.02)

    # 最终停留在按钮上，触发按钮内部的 --core-x / --core-y 坐标计算
    await page.mouse.move(target_x, target_y)
    await asyncio.sleep(0.5)

    # 点击按钮
    await page.mouse.click(target_x, target_y)
    print("已成功在目标坐标执行点击操作。")

async def main():
    # 从环境变量获取隐私敏感数据（完全去除了特定字样）
    target_url = os.environ.get("TARGET_URL")
    account_user = os.environ.get("ACCOUNT_USER")
    account_pass = os.environ.get("ACCOUNT_PASS")

    if not target_url or not account_user or not account_pass:
        raise ValueError("请确保已正确配置环境变量: TARGET_URL, ACCOUNT_USER, ACCOUNT_PASS")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        
        # 创建上下文，设置常见浏览器的视口大小，确保与页面指纹匹配 (1536x864)
        context = await browser.new_context(
            viewport={"width": 1536, "height": 864},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print("正在打开目标登录页面...")
        await page.goto(target_url, wait_until="networkidle")

        # 1. 填写 E-MAIL
        print("正在填写邮箱...")
        email_input = await page.wait_for_selector('input[name="email"]')
        await email_input.fill(account_user)
        await asyncio.sleep(0.5)

        # 2. 填写 PASSWORD
        print("正在填写密码...")
        password_input = await page.wait_for_selector('input[name="password"]')
        await password_input.fill(account_pass)
        await asyncio.sleep(0.5)

        # 3. 勾选确认框 (accept_legal)
        print("正在勾选法律条款确认框...")
        checkbox = await page.wait_for_selector('input[name="accept_legal"]')
        is_checked = await checkbox.is_checked()
        if not is_checked:
            await checkbox.click()
        await asyncio.sleep(0.5)

        # 4. 模拟鼠标轨迹并点击提交按钮
        print("开始执行鼠标模拟与点击提交...")
        await simulate_mouse_move_and_click(
            page, 
            'button.button.button-primary.vf-signin-button.auth-submit'
        )

        # 等待登录后的跳转或响应结果
        try:
            await page.wait_for_url("**/dashboard**", timeout=10000)
            print("登录成功，已成功跳转！")
        except Exception:
            print("未能检测到预期的跳转，当前页面 URL:", page.url)
            await page.screenshot(path="login_result.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
