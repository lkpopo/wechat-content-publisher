import logging
import time
import sys
import os
import shutil
import subprocess
import socket
import json
import asyncio
from pathlib import Path

# Ensure local CDP connections bypass system/environment proxies
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
DEBUG_DIR = DATA_DIR / "debug"

# Dedicated profile directory for publisher (avoids Chrome 136+ restrictions on default User Data dir)
CHROME_PUBLISHER_USER_DATA = Path.home() / ".chrome-publisher"
CHROME_SRC_USER_DATA = Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"))


def _is_port_open(host: str = "127.0.0.1", port: int = 9222) -> bool:
    """Check if remote debugging port is open and accepting TCP connections."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.5)
            return s.connect_ex((host, port)) == 0
    except:
        return False


def _is_chrome_process_running() -> bool:
    """Check if any chrome.exe process is currently active."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return "chrome.exe" in output.lower()
    except Exception as e:
        logger.warning(f"[Chrome] Error checking chrome process: {e}")
        return False


def _find_chrome():
    """Locate Chrome executable path."""
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _get_active_profile_name() -> str:
    """Detect the user's active/last-used profile name in their system Chrome."""
    local_state_path = CHROME_SRC_USER_DATA / "Local State"
    if local_state_path.exists():
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                last_used = data.get("profile", {}).get("last_used")
                if last_used and (CHROME_SRC_USER_DATA / last_used).exists():
                    return last_used
        except Exception as e:
            logger.debug(f"[Chrome] Failed to read Local State: {e}")

    for cand in ["Profile 3", "Default"]:
        if (CHROME_SRC_USER_DATA / cand).exists():
            return cand
    return "Default"


def _init_publisher_profile():
    """
    Initialize publisher profile directory on first run by copying basic
    bookmarks and preferences from the user's local Chrome, giving them a familiar environment.
    """
    CHROME_PUBLISHER_USER_DATA.mkdir(parents=True, exist_ok=True)
    marker_file = CHROME_PUBLISHER_USER_DATA / ".initialized"
    if marker_file.exists():
        return

    if not CHROME_SRC_USER_DATA.exists():
        marker_file.touch()
        return

    try:
        logger.info("[Chrome] Initializing publisher profile from system Chrome...")
        # Copy Local State
        src_ls = CHROME_SRC_USER_DATA / "Local State"
        dst_ls = CHROME_PUBLISHER_USER_DATA / "Local State"
        if src_ls.exists() and not dst_ls.exists():
            shutil.copy2(src_ls, dst_ls)

        profile_name = _get_active_profile_name()
        src_prof = CHROME_SRC_USER_DATA / profile_name
        dst_prof = CHROME_PUBLISHER_USER_DATA / "Default"
        dst_prof.mkdir(parents=True, exist_ok=True)

        # Copy non-locked user files: Bookmarks, Preferences
        for fname in ["Bookmarks", "Preferences", "Favicons"]:
            s = src_prof / fname
            t = dst_prof / fname
            if s.exists() and not t.exists():
                try:
                    shutil.copy2(s, t)
                except Exception:
                    pass

        marker_file.touch()
        logger.info("[Chrome] Publisher profile initialization complete")
    except Exception as e:
        logger.warning(f"[Chrome] Could not fully initialize publisher profile: {e}")


def _start_chrome():
    """Start Chrome with remote debugging enabled and dedicated persistent user data."""
    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError("未找到谷歌浏览器(chrome.exe)，请确认已安装 Chrome")

    _init_publisher_profile()

    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={CHROME_PUBLISHER_USER_DATA}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    logger.info(f"[Chrome] Launching Chrome with remote debugging on port 9222...")
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags
    )

    # Wait up to 15s for the debugging port to be ready
    for i in range(15):
        time.sleep(1)
        if _is_port_open("127.0.0.1", 9222):
            logger.info(f"[Chrome] Chrome started successfully on port 9222 (took {i+1}s)")
            return True

    raise RuntimeError("Chrome 启动超时，未能开启 9222 调试端口")


def _ensure_chrome():
    """
    Ensure a Chrome instance is available with CDP port 9222.
    - If 9222 is open: reuse the running Chrome!
    - If 9222 is not open: start our dedicated publisher Chrome.
      (Never terminate the user's regular Chrome!)
    """
    # 1. Debug port already open -> great, reuse it!
    if _is_port_open("127.0.0.1", 9222):
        logger.info("[Chrome] Found existing Chrome running with port 9222 open")
        return True

    # 2. Port 9222 not open -> start our publisher Chrome with its own user-data-dir
    logger.info("[Chrome] Port 9222 not open. Launching publisher Chrome...")
    return _start_chrome()


async def _run_publish_async(article, title: str, content: str) -> dict:
    """Async publish implementation with Playwright over CDP"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        logger.info("[Toutiao] Connecting to Chrome over CDP (http://127.0.0.1:9222)...")
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser.contexts[0]

        # Check if there's already an open tab on toutiao
        existing_toutiao_page = next((page for page in context.pages if "mp.toutiao.com" in page.url), None)
        if existing_toutiao_page:
            logger.info("[Toutiao] Reusing existing Toutiao tab")
            page = existing_toutiao_page
            await page.bring_to_front()
        else:
            logger.info("[Toutiao] Opening a new tab in Chrome...")
            page = await context.new_page()

        try:
            logger.info("[Toutiao] Navigating to publish page...")
            # Use domcontentloaded to avoid getting stuck on heavy background network requests
            await page.goto("https://mp.toutiao.com/profile_v4/graphic/publish", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Check if redirected to login page
            if "login" in page.url:
                logger.warning(f"[Toutiao] Redirected to login page: {page.url}")
                return {
                    "success": False,
                    "message": "今日头条账号尚未登录。请在已打开的谷歌浏览器中扫码登录今日头条，登录后再次点击发布即可！"
                }

            logger.info("[Toutiao] Waiting for title input...")
            title_sel = 'textarea[placeholder*="标题"]'
            await page.wait_for_selector(title_sel, timeout=15000)
            title_input = page.locator(title_sel)
            await title_input.fill("")
            await title_input.fill(title)
            logger.info(f"[Toutiao] Title filled: {title[:20]}...")

            # Clean any interfering AI assistant drawers or overlay masks
            await _clean_toutiao_overlays(page)

            logger.info("[Toutiao] Waiting for editor...")
            editor_sel = '.ProseMirror[contenteditable="true"]'
            await page.wait_for_selector(editor_sel, timeout=15000)

            # Focus editor natively without triggering pointer event interceptions
            await page.evaluate("""(sel) => {
                const editor = document.querySelector(sel);
                if (editor) {
                    editor.focus();
                }
            }""", editor_sel)

            blocks = content.split("\n\n")
            for i, block in enumerate(blocks):
                block = block.strip()
                if not block:
                    continue

                if block.startswith("[image_"):
                    image_id = block.replace("[", "").replace("]", "")
                    idx = int(image_id.replace("image_", ""))
                    img = next((img_item for img_item in article.images if img_item.image_index == idx), None)
                    if img and img.local_path and os.path.exists(img.local_path):
                        await _upload_image_async(page, img.local_path)
                    else:
                        logger.warning(f"[Toutiao] Image not found for block: {block}")
                else:
                    await _insert_paragraph_async(page, block, i > 0)

            logger.info("[Toutiao] Content successfully filled")
            await asyncio.sleep(2)

            # Clean any new overlays that might have popped up during editing
            await _clean_toutiao_overlays(page)

            # 1. Verify content is indeed filled
            editor_text_len = await page.evaluate("""() => {
                const el = document.querySelector('.ProseMirror[contenteditable="true"]');
                return el ? el.innerText.trim().length : 0;
            }""")
            if editor_text_len < 10:
                raise RuntimeError(f"文章正文填充异常：编辑器内仅检测到 {editor_text_len} 个字符，未能完整填充")
            logger.info(f"[Toutiao] Content verified: {editor_text_len} characters in editor")

            # 2. Step 1: Click "预览发布" / "发布" button
            logger.info("[Toutiao] Searching for preview/publish button...")
            preview_selectors = [
                'button:has-text("预览发布")',
                'button.publish-btn-last',
                'button:has-text("发布")',
                'div[role="button"]:has-text("发布")',
            ]
            preview_btn = None
            for sel in preview_selectors:
                try:
                    loc = page.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        preview_btn = loc
                        logger.info(f"[Toutiao] Found preview button with selector: {sel}")
                        break
                except Exception:
                    continue

            if not preview_btn:
                raise RuntimeError("未找到今日头条【预览发布】按钮，无法进入发布流程")

            logger.info("[Toutiao] Clicking preview/publish button...")
            await preview_btn.click(force=True)

            # 3. Step 2: Wait for confirmation dialog / secondary publish button
            logger.info("[Toutiao] Waiting for confirm publish dialog...")
            confirm_selectors = [
                'button:has-text("确认发布")',
                'button:has-text("确定发布")',
                'div.byte-modal button:has-text("确定")',
                'div.byte-modal button:has-text("确认发布")',
                'div.semi-modal button:has-text("确定")',
                'div.byte-modal button.byte-btn-primary',
                'button:has-text("确认")',
            ]
            confirm_btn = None
            # Wait up to 8s for confirm dialog
            for _ in range(16):
                await asyncio.sleep(0.5)
                # Check if already redirected
                if "articles" in page.url:
                    logger.info("[Toutiao] Page redirected to articles list directly!")
                    break
                for c_sel in confirm_selectors:
                    try:
                        loc = page.locator(c_sel).last
                        if await loc.count() > 0 and await loc.is_visible():
                            confirm_btn = loc
                            logger.info(f"[Toutiao] Found confirmation button: {c_sel}")
                            break
                    except Exception:
                        continue
                if confirm_btn:
                    break

            if confirm_btn:
                logger.info("[Toutiao] Clicking confirm publish button...")
                await confirm_btn.click(force=True)
            else:
                logger.info("[Toutiao] No secondary confirmation modal appeared, checking direct result...")

            # 4. Step 3: Wait for publish result (URL redirect to articles or success toast)
            logger.info("[Toutiao] Waiting for publish result verification...")
            publish_success = False
            error_message = None

            for attempt in range(20):
                await asyncio.sleep(1)
                curr_url = page.url

                # Check 1: Redirected to article management list
                if "articles" in curr_url or "graphic/articles" in curr_url:
                    publish_success = True
                    logger.info(f"[Toutiao] Published successfully verified by URL redirect: {curr_url}")
                    break

                # Check 2: Success toast in page
                toast_info = await page.evaluate("""() => {
                    const toasts = Array.from(document.querySelectorAll('.byte-message, .semi-toast, .semi-toast-content, .byte-modal-title, .byte-message-notice'));
                    const texts = toasts.map(t => (t.innerText || '').trim()).filter(Boolean);
                    return texts;
                }""")
                if any("发布成功" in t or "发表成功" in t or "提交成功" in t for t in toast_info):
                    publish_success = True
                    logger.info(f"[Toutiao] Published successfully verified by message toast: {toast_info}")
                    break

                # Check 3: Error modal or warning toast
                for t in toast_info:
                    if any(kw in t for kw in ["失败", "违规", "禁止", "不符合", "请重新", "错误", "敏感"]):
                        error_message = f"今日头条拦截提示: {t}"
                        break
                if error_message:
                    break

            if not publish_success:
                if error_message:
                    raise RuntimeError(f"今日头条发布失败：{error_message}")
                else:
                    # Final check: is current page still on publish?
                    if "publish" in page.url:
                        # Inspect if there's any visible error text on the page
                        page_errors = await page.evaluate("""() => {
                            const errEls = document.querySelectorAll('.byte-form-item-error-tip, .error-tip, .byte-input-error');
                            return Array.from(errEls).map(e => e.innerText.trim()).filter(Boolean);
                        }""")
                        if page_errors:
                            raise RuntimeError(f"今日头条发布校验未通过: {', '.join(page_errors)}")
                        raise RuntimeError("今日头条发布超时：未能在预期时间内确认发布结果")

            logger.info("[Toutiao] Publish action completed successfully and verified!")
            return {"success": True, "message": "文章已成功填充并确认发布到今日头条！"}

        except Exception as e:
            logger.error(f"[Toutiao] Error during publish: {e}", exc_info=True)
            try:
                DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(DEBUG_DIR / "toutiao_error.png"))
            except Exception:
                pass
            return {"success": False, "message": str(e)}


async def _clean_toutiao_overlays(page):
    """Dismiss and remove any drawers, AI assistant panels, or masks blocking the page."""
    try:
        await page.evaluate("""() => {
            // 1. Click close buttons on any open drawers or popups
            const closeSelectors = [
                '.ai-assistant-drawer .byte-drawer-close-btn',
                '.ai-assistant-drawer .byte-icon-close',
                '.ai-assistant-drawer button[aria-label="Close"]',
                '.byte-drawer-close-btn',
                '.byte-modal-close-icon',
                'button[aria-label="Close"]'
            ];
            for (const sel of closeSelectors) {
                document.querySelectorAll(sel).forEach(btn => {
                    try { btn.click(); } catch(e) {}
                });
            }

            // 2. Remove all blocking mask elements from DOM
            const maskSelectors = [
                '.byte-drawer-mask',
                '.byte-modal-mask',
                '.driver-overlay',
                '.semi-modal-mask',
                '.semi-portal'
            ];
            for (const mSel of maskSelectors) {
                document.querySelectorAll(mSel).forEach(mask => {
                    mask.style.display = 'none';
                    mask.remove();
                });
            }
        }""")
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.debug(f"[Toutiao] Note on overlay cleanup: {e}")


async def _insert_paragraph_async(page, text: str, add_newline: bool = False):
    """Insert text into the ProseMirror editor smoothly and reliably"""
    # Use native keyboard insertion when possible for best compatibility with ProseMirror
    try:
        if add_newline:
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.1)
        await page.keyboard.insert_text(text)
        await asyncio.sleep(0.1)
    except Exception:
        # Fallback to execCommand
        await page.evaluate("""(text, addNewline) => {
            const editor = document.querySelector('.ProseMirror[contenteditable="true"]');
            if (!editor) return;
            editor.focus();
            if (addNewline) {
                document.execCommand('insertParagraph', false);
            }
            document.execCommand('insertText', false, text);
            editor.dispatchEvent(new Event('input', { bubbles: true }));
        }""", text, add_newline)


async def _upload_image_async(page, image_path: str):
    """Upload local image to Toutiao ProseMirror editor"""
    if not image_path or not os.path.exists(image_path):
        logger.warning(f"[Toutiao] Image file does not exist: {image_path}")
        return

    logger.info(f"[Toutiao] Uploading image: {os.path.basename(image_path)}")
    try:
        # 1. Trigger toolbar image button click via JS
        await page.evaluate("""() => {
            const btn = document.querySelector('div.syl-toolbar-tool.image button') || 
                        document.querySelector('div.syl-toolbar-tool.image');
            if (btn) btn.click();
        }""")
        await asyncio.sleep(1)

        # 2. Locate file input inside upload panel
        file_input = page.locator('.upload-handler input[type="file"], .upload-image-panel input[type="file"], input#upload-drag-input')
        if await file_input.count() > 0:
            await file_input.first.set_input_files(image_path)
            logger.info(f"[Toutiao] Image file set: {os.path.basename(image_path)}, uploading...")
            await asyncio.sleep(2.5)

            # 3. Click '确定' confirm button via JS in the active modal
            confirmed = await page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const confirmBtn = btns.find(b => b.innerText && b.innerText.trim() === '确定' && b.offsetParent !== null);
                if (confirmBtn) {
                    confirmBtn.click();
                    return true;
                }
                return false;
            }""")
            if confirmed:
                logger.info(f"[Toutiao] Image inserted into editor: {os.path.basename(image_path)}")
                await asyncio.sleep(1.5)
            else:
                logger.warning(f"[Toutiao] Could not confirm image insert for: {os.path.basename(image_path)}")
        else:
            logger.warning(f"[Toutiao] File input did not appear for: {os.path.basename(image_path)}")

        # 4. Insert enter after image for next content blocks
        await page.keyboard.press("Enter")
        await asyncio.sleep(0.3)

    except Exception as e:
        logger.error(f"[Toutiao] Failed to upload image {image_path}: {e}")


def publish_to_toutiao(article, title: str, content: str) -> dict:
    """Publish to Toutiao - main entry point"""
    logger.info(f"[Toutiao] Starting publish for article {article.id}")

    try:
        _ensure_chrome()
    except Exception as e:
        logger.error(f"[Toutiao] Chrome readiness check failed: {e}")
        return {"success": False, "message": str(e)}

    # IMPORTANT: On Windows, Playwright requires ProactorEventLoop to launch subprocesses
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_publish_async(article, title, content))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"[Toutiao] Unexpected exception in publish_to_toutiao: {e}", exc_info=True)
        return {"success": False, "message": str(e)}
