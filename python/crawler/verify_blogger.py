#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
博主真实性校验 - Step3

- 对 wechat/weibo/xiaohongshu 分别尝试不同校验策略
- 优先级：URL直连 > 平台搜索 > 本地白名单
- 退出码 0=存在, 1=不存在/校验失败, 2=网络异常
"""

import argparse
import sys
import re
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 已知白名单（用于离线演示，真实环境会走网络校验）
WHITELIST = {
    "wechat_li_yongle": True,
    "wechat_banfo": True,
    "weibo_leijun": True,
    "xhs_food_001": True,
}

# 博主领域映射（用于校验后生成更贴合的 Mock 文章）
BLOGGER_TOPICS = {
    "李永乐": ["物理科普", "数学思维", "AI与教育"],
    "半佛": ["财经科普", "消费陷阱", "职场"],
    "雷军": ["小米科技", "创业", "智能硬件"],
    "美食": ["探店", "家常菜", "烘焙"],
}

def check_url(url: str, timeout=8) -> bool:
    if not url or not url.startswith("http"):
        return False
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        # 200 或 302 均视为可访问
        if r.status_code in (200, 301, 302):
            # 简单反爬检测：若返回包含“不存在”“未找到”则判不存在
            low = r.text.lower()
            if any(k in low for k in ["不存在", "未找到", "not found", "no longer exists"]):
                return False
            return True
        return False
    except Exception as e:
        print(f"[verify] URL 请求异常: {e}", file=sys.stderr)
        return False

def check_wechat_via_sogou(name: str, timeout=10) -> bool:
    """尝试搜狗微信搜索该公众号名称 - 精确匹配结果标题"""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("[verify] 未安装 requests/bs4，跳过搜狗校验", file=sys.stderr)
        return False
    try:
        url = f"https://weixin.sogou.com/weixin?type=1&query={name}&ie=utf8"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://weixin.sogou.com/",
        }
        print(f"[verify] 搜狗搜索: {url}", file=sys.stderr)
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            print(f"[verify] 搜狗返回 {r.status_code}", file=sys.stderr)
            return False
        soup = BeautifulSoup(r.text, "lxml")
        text = soup.get_text()
        # 明确无结果
        if "没有找到" in text and "微信公众号" in text:
            print("[verify] 搜狗提示无结果", file=sys.stderr)
            return False
        # 精确：在公众号结果区域查找标题
        # 搜狗公众号结果通常在 .news-list 或 .wx-rb-account 区域
        candidates = soup.select(".news-list .txt-box a, .wx-rb a, [uigs*='account_name'] a, h3 a")
        found_titles = [c.get_text(strip=True) for c in candidates[:8]]
        print(f"[verify] 搜狗标题候选: {found_titles}", file=sys.stderr)
        if not found_titles:
            # 若无候选但页面有结果列表，说明被反爬或结构变更，保守返回 False 让用户确认
            if soup.select("ul.news-list li, .news-box"):
                # 检查标题是否包含 name 的关键子串（至少2字匹配）
                # 对不存在的博主，标题不会包含完整 name
                return False
            return False
        # 只要有一个标题包含 name 的核心词（去掉空格）则判存在
        # 对长名要求完整匹配，短名要求包含
        name_key = name.strip().replace(" ", "")
        for t in found_titles:
            if name_key in t.replace(" ", "") or t.replace(" ", "") in name_key:
                print(f"[verify] 命中标题: {t}", file=sys.stderr)
                return True
        # 无命中
        return False
    except Exception as e:
        print(f"[verify] 搜狗校验异常: {e}", file=sys.stderr)
        return False

def check_weibo_via_api(name_or_id: str) -> bool:
    """微博校验：尝试 m.weibo.cn 搜索"""
    try:
        import requests
    except ImportError:
        return False
    try:
        # 简易：搜索接口（可能需 cookie，失败则回退）
        url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D3%26q%3D{name_or_id}&page_type=searchall"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200 and "cards" in r.text:
            return True
        return False
    except Exception as e:
        print(f"[verify] 微博校验异常: {e}", file=sys.stderr)
        return False

def verify_blogger(platform: str, bid: str, name: str, url: str) -> tuple[bool, str]:
    # 1. 白名单直通（离线可用）
    if bid in WHITELIST:
        return True, f"白名单命中：{bid} 已验证"
    # 2. URL 直连
    if url:
        if check_url(url):
            return True, f"链接可访问：{url[:40]}"
        else:
            print(f"[verify] URL 不可访问，继续平台校验", file=sys.stderr)
    # 3. 平台特定
    if platform == "wechat":
        # 优先搜狗
        if check_wechat_via_sogou(name):
            return True, f"搜狗微信找到公众号：{name}"
        # 尝试 URL 形式：https://mp.weixin.qq.com/s/... 通常无法直接判定，视为需人工确认
        # 若名称长度>=2且不含特殊字符，视为可能存在（宽松）
        if len(name.strip()) >= 2:
            # 网络不可用时，给出提示但允许
            return False, f"未在搜狗找到“{name}”，请确认公众号名称是否正确（可能需登录后校验）"
        return False, "名称过短，无法校验"
    elif platform == "weibo":
        if check_weibo_via_api(name or bid):
            return True, f"微博搜索到相关用户：{name}"
        if len(name) >= 2:
            return False, f"未在微博搜索到“{name}”，请确认昵称"
        return False, "无法校验"
    elif platform == "xiaohongshu":
        # 小红书需登录态，暂时宽松
        if url and "xiaohongshu.com" in url and check_url(url):
            return True, "小红书链接可访问"
        if len(name) >= 2:
            return False, f"小红书校验需登录态，暂无法自动确认“{name}”"
        return False, "无法校验"
    return False, "未知平台"

def main():
    parser = argparse.ArgumentParser(description="Verify blogger")
    parser.add_argument("--platform", required=True, choices=["wechat","weibo","xiaohongshu"])
    parser.add_argument("--id", required=True, help="博主ID")
    parser.add_argument("--name", required=True, help="博主名称")
    parser.add_argument("--url", default="", help="主页链接")
    args = parser.parse_args()

    print(f"[verify] 开始校验 platform={args.platform} id={args.id} name={args.name} url={args.url}", file=sys.stderr)
    ok, msg = verify_blogger(args.platform, args.id, args.name, args.url)
    print(msg)
    if ok:
        print(f"[verify] 结果：通过", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"[verify] 结果：未通过 - {msg}", file=sys.stderr)
        # 为演示：白名单外即使搜狗未找到，仍返回 0 但带警告？不，严格返回1让 C++ 感知未验证
        # 这里返回 1，C++  dialog 会显示未通过但仍允许保存
        sys.exit(1)

if __name__ == "__main__":
    main()
