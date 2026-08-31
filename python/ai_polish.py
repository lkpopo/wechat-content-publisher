#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兼容入口：python/ai_polish.py -> 转发到 python/automation/ai_polish.py
保留此文件是为了兼容 mainwindow.cpp 中对旧路径的回退逻辑
"""
from pathlib import Path
import runpy
import sys

target = Path(__file__).parent / "automation" / "ai_polish.py"
if target.exists():
    # 将当前参数原样转发
    sys.argv[0] = str(target)
    runpy.run_path(str(target), run_name="__main__")
else:
    print(f"[ai_polish] 找不到真实脚本: {target}", file=sys.stderr)
    sys.exit(1)
