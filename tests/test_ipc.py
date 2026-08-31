#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step1 IPC 链路自测脚本 - 模拟 C++ QProcess 调用"""

import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SCRIPT = ROOT / "python" / "automation" / "ai_polish.py"

def test_file_ipc():
    print("=== 测试 文件 IPC (temp_in -> temp_out) ===")
    with tempfile.TemporaryDirectory() as td:
        tmp_in = Path(td) / "temp_in.txt"
        tmp_out = Path(td) / "temp_out.txt"
        content = "这是 C++ 侧写入的原文第一段。\n第二段内容。"
        tmp_in.write_text(content, encoding="utf-8")
        print(f"写入 {tmp_in} {len(content)} chars")

        cmd = [PY, str(SCRIPT), str(tmp_in), str(tmp_out)]
        print(f"执行: {' '.join(cmd)}")
        env = {**subprocess.os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        print("STDERR:", result.stderr[:500])
        print("STDOUT:", result.stdout[:500])
        assert result.returncode == 0, f"exit {result.returncode}"
        assert tmp_out.exists(), "输出文件未生成"
        out = tmp_out.read_text(encoding="utf-8")
        # Step2 Mock 输出为 【润色】/润色 兼容 Step1 的 [已润色]
        assert "润色" in out, "润色标记缺失"
        print("✅ 文件 IPC 通过, 输出预览:")
        print(out[:400])

def test_stdout_fallback():
    print("\n=== 测试 stdout 回退 ===")
    content = "单行测试"
    cmd = [PY, str(SCRIPT), "--stdin", "--stdout", "--mock"]
    env = {**subprocess.os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(cmd, input=content, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    assert "润色" in result.stdout
    print("✅ stdout 通过")

def test_crawler():
    print("\n=== 测试 crawler Mock ===")
    script = ROOT / "python" / "crawler" / "crawler.py"
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "crawl.json"
        cmd = [PY, str(script), "--blogger", "wechat_li_yongle", "--platform", "wechat", "--output", str(out)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(result.stdout[:300])
        assert out.exists()
        import json
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["count"] >= 3
        print(f"✅ crawler 通过, {data['count']} 篇")

if __name__ == "__main__":
    test_file_ipc()
    test_stdout_fallback()
    test_crawler()
    print("\n✅ 全部链路测试通过")
