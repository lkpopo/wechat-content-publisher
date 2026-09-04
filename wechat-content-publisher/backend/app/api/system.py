import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


def _find_git_bin() -> str:
    """Find absolute path to git binary on Windows/Linux."""
    which_git = shutil.which("git")
    if which_git:
        return which_git

    common_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Users\Administrator\AppData\Local\Programs\Git\cmd\git.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p

    return "git"


def get_git_root() -> Path:
    """Find the nearest directory containing .git, or self-heal with git init."""
    cur = Path(__file__).resolve().parent
    while cur != cur.parent:
        git_marker = cur / ".git"
        if git_marker.exists():
            return cur
        cur = cur.parent

    # Default project root: wechat-content-publisher
    default_root = Path(__file__).resolve().parent.parent.parent
    git_marker = default_root / ".git"
    if not git_marker.exists():
        try:
            git_bin = _find_git_bin()
            subprocess.run([git_bin, "init", "-b", "main"], cwd=str(default_root), capture_output=True)
            logger.info(f"Initialized git repository at {default_root}")
        except Exception as e:
            logger.warning(f"Failed to auto-init git at {default_root}: {e}")

    return default_root


def run_git(args: list[str], cwd: Optional[Path] = None, timeout: int = 60) -> Tuple[int, str, str]:
    if cwd is None:
        cwd = get_git_root()

    git_bin = _find_git_bin()
    cmd = [git_bin] + args

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=True,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", f"Git 命令执行超时 ({timeout}秒)，请检查网络连接"
    except Exception as e:
        return -1, "", str(e)


class RemoteUrlRequest(BaseModel):
    remote_url: str


@router.get("/version")
def get_version_info():
    """Get local git repository version and remote tracking info."""
    git_root = get_git_root()

    code, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], git_root)
    code, commit_hash, _ = run_git(["log", "-1", "--format=%h"], git_root)
    code, commit_msg, _ = run_git(["log", "-1", "--format=%s"], git_root)
    code, commit_time, _ = run_git(["log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M"], git_root)
    code, remote_url, _ = run_git(["remote", "get-url", "origin"], git_root)

    current_branch = branch if (branch and branch != "HEAD") else "main"

    return {
        "version": "v0.2.1",
        "branch": current_branch,
        "commit_hash": commit_hash if commit_hash else "unknown",
        "commit_message": commit_msg if commit_msg else "初始版本",
        "commit_time": commit_time if commit_time else "",
        "remote_url": remote_url if (remote_url and code == 0) else "",
        "git_root": str(git_root),
    }


@router.post("/set-remote")
def set_remote_url(req: RemoteUrlRequest):
    """Set or update the origin remote URL."""
    url = req.remote_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="远程仓库 URL 不能为空")

    git_root = get_git_root()

    code, _, _ = run_git(["remote", "get-url", "origin"], git_root)
    if code == 0:
        set_code, out, err = run_git(["remote", "set-url", "origin", url], git_root)
    else:
        set_code, out, err = run_git(["remote", "add", "origin", url], git_root)

    if set_code != 0:
        logger.error(f"Failed to set remote origin: {err or out}")
        raise HTTPException(status_code=500, detail=f"设置远程仓库失败: {err or out}")

    logger.info(f"Updated git remote origin to {url} at {git_root}")
    return {"success": True, "remote_url": url, "message": "远程仓库地址已成功绑定！"}


@router.post("/check-update")
def check_for_updates():
    """Fetch from remote and check if new commits are available."""
    git_root = get_git_root()

    # Check remote origin
    code, remote_url, _ = run_git(["remote", "get-url", "origin"], git_root)
    if code != 0 or not remote_url:
        return {
            "configured": False,
            "has_update": False,
            "message": "尚未配置远程仓库地址，请先在上方输入框绑定远程仓库",
        }

    code, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], git_root)
    target_branch = branch if (branch and branch != "HEAD") else "main"

    # Fetch from remote origin
    logger.info(f"Running git fetch origin {target_branch} at {git_root}...")
    code, out, err = run_git(["fetch", "origin", target_branch], git_root, timeout=60)
    if code != 0:
        # Fallback to fetch all
        code, out, err = run_git(["fetch", "origin"], git_root, timeout=60)

    if code != 0:
        logger.warning(f"git fetch failed: {err}")
        return {
            "configured": True,
            "has_update": False,
            "error": f"无法连接到远程仓库: {err}",
            "message": "检查更新失败，请检查网络连接或远程仓库访问权限",
        }

    # Count how many commits local is behind origin
    code, count_str, _ = run_git(
        ["rev-list", "--count", f"HEAD..origin/{target_branch}"], git_root
    )

    behind_count = 0
    if code == 0 and count_str.isdigit():
        behind_count = int(count_str)

    # Get commit log if behind
    commits = []
    if behind_count > 0:
        code, log_out, _ = run_git(
            ["log", f"HEAD..origin/{target_branch}", "--oneline", "-n", "10"],
            git_root,
        )
        if code == 0 and log_out:
            commits = log_out.splitlines()

    return {
        "configured": True,
        "has_update": behind_count > 0,
        "behind_count": behind_count,
        "branch": target_branch,
        "remote_url": remote_url,
        "recent_commits": commits,
        "message": (
            f"发现 {behind_count} 个新更新，可点击下方按钮立即拉取！"
            if behind_count > 0
            else "当前已是最新版本，无需更新！"
        ),
    }


@router.post("/pull-update")
def pull_latest_updates():
    """Pull the latest commits from origin with safe auto-stash."""
    git_root = get_git_root()

    code, remote_url, _ = run_git(["remote", "get-url", "origin"], git_root)
    if code != 0 or not remote_url:
        raise HTTPException(status_code=400, detail="未配置远程仓库地址，无法拉取更新")

    code, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], git_root)
    target_branch = branch if (branch and branch != "HEAD") else "main"

    logger.info(f"Safely running git pull origin {target_branch} at {git_root}...")

    # Stash any local uncommitted files to prevent pull conflict
    run_git(["stash"], git_root)

    code, out, err = run_git(["pull", "origin", target_branch, "--no-rebase"], git_root, timeout=90)

    # Try pop stash if stashed
    run_git(["stash", "pop"], git_root)

    if code != 0:
        logger.error(f"git pull failed: {err or out}")
        raise HTTPException(status_code=500, detail=f"拉取更新失败: {err or out}")

    logger.info(f"Git pull successful: {out}")
    return {
        "success": True,
        "output": out,
        "message": "代码已成功拉取更新！请按 Ctrl+F5 刷新页面生效最新版本。",
    }
