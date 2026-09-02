import logging
import json
import subprocess
import sys
import time
import websocket
import requests
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def publish_to_toutiao(article, title: str, content: str) -> dict:
    logger.info(f"[Toutiao] Starting publish for article {article.id}")
    logger.info(f"[Toutiao] Title: {title[:50]}...")

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = str(Path("data/chrome-profile").resolve())
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        resp.json()
        logger.info("[Toutiao] Chrome already running")
    except:
        logger.info("[Toutiao] Launching Chrome...")
        subprocess.Popen([
            chrome_path,
            "--remote-debugging-port=9222",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ])
        time.sleep(3)

    resp = requests.get("http://127.0.0.1:9222/json")
    pages = resp.json()
    ws_url = pages[0]["webSocketDebuggerUrl"]

    ws = websocket.create_connection(ws_url)
    msg_id = 1

    def send_cmd(method, params=None):
        nonlocal msg_id
        cmd = {"id": msg_id, "method": method}
        if params:
            cmd["params"] = params
        ws.send(json.dumps(cmd))
        result = json.loads(ws.recv())
        msg_id += 1
        return result

    try:
        logger.info("[Toutiao] Navigating to publish page...")
        send_cmd("Page.navigate", {"url": "https://mp.toutiao.com/profile_v4/graphic/publish"})
        time.sleep(5)

        logger.info("[Toutiao] Filling title...")
        send_cmd("Runtime.evaluate", {
            "expression": """
                (function() {
                    var input = document.querySelector('input[placeholder*="标题"]')
                        || document.querySelector('[aria-label*="标题"]')
                        || document.querySelector('.title-input input');
                    if (input) {
                        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeInputValueSetter.call(input, '""" + title.replace("'", "\\'") + """');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        return 'ok';
                    }
                    return 'not found';
                })()
            """
        })
        logger.info("[Toutiao] Title filled")

        logger.info("[Toutiao] Filling content...")
        lines = content.split("\n\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("[image_"):
                idx = int(line.replace("[image_", "").replace("]", ""))
                img = next((i for i in article.images if i.image_index == idx), None)
                if img and img.local_path:
                    send_cmd("Runtime.evaluate", {
                        "expression": f"""
                            (function() {{
                                var input = document.querySelector('input[type="file"]');
                                if (input) {{
                                    input.style.display = 'block';
                                    return 'ok';
                                }}
                                return 'not found';
                            }})()
                        """
                    })
            else:
                send_cmd("Input.insertText", {"text": line})
                send_cmd("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})
                send_cmd("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Enter", "code": "Enter", "windowsVirtualKeyCode": 13})

        logger.info("[Toutiao] Content filled, clicking publish...")
        send_cmd("Runtime.evaluate", {
            "expression": """
                (function() {
                    var btn = document.querySelector('button:has-text("发布")')
                        || document.querySelector('button.publishBtn')
                        || Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('发布'));
                    if (btn) {
                        btn.click();
                        return 'ok';
                    }
                    return 'not found';
                })()
            """
        })

        time.sleep(5)
        logger.info("[Toutiao] Publish success!")
        return {"success": True, "message": "发布成功"}
    except Exception as e:
        logger.error(f"[Toutiao] Publish error: {e}", exc_info=True)
        raise
    finally:
        ws.close()
