import logging
import subprocess
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


def get_git_root() -> Path:
    """Find the nearest parent directory containing .git"""
    cur = Path(__file__).resolve().parent
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    return Path(__file__).resolve().parent.parent.parent


def run_git(args: list[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
    if cwd is None:
        cwd = get_git_root()
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
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

    return {
        "version": "v0.2.0",
        "branch": branch if branch else "master",
        "commit_hash": commit_hash if commit_hash else "unknown",
        "commit_message": commit_msg if commit_msg else "",
        "commit_time": commit_time if commit_time else "",
        "remote_url": remote_url if remote_url and code == 0 else "",
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
        raise HTTPException(status_code=500, detail=f"设置远程仓库失败: {err}")

    logger.info(f"Updated git remote origin to {url}")
    return {"success": True, "remote_url": url, "message": "远程仓库地址已成功配置！"}


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
            "message": "尚未配置远程仓库地址，请先绑定远程仓库",
        }

    # Fetch from remote
    logger.info("Running git fetch origin...")
    code, out, err = run_git(["fetch", "origin"], git_root)
    if code != 0:
        logger.warning(f"git fetch failed: {err}")
        return {
            "configured": True,
            "has_update": False,
            "error": f"无法连接到远程仓库: {err}",
            "message": "检查更新失败，请检查网络或远程仓库权限",
        }

    code, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], git_root)
    target_branch = branch if branch else "master"

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
            f"发现 {behind_count} 个新提交，可立即拉取更新！"
            if behind_count > 0
            else "当前已是最新版本，无需更新"
        ),
    }


@router.post("/pull-update")
def pull_latest_updates():
    """Pull the latest commits from origin."""
    git_root = get_git_root()

    code, remote_url, _ = run_git(["remote", "get-url", "origin"], git_root)
    if code != 0 or not remote_url:
        raise HTTPException(status_code=400, detail="未配置远程仓库地址")

    code, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], git_root)
    target_branch = branch if branch else "master"

    logger.info(f"Running git pull origin {target_branch}...")
    code, out, err = run_git(["pull", "origin", target_branch], git_root)
    if code != 0:
        logger.error(f"git pull failed: {err}")
        raise HTTPException(status_code=500, detail=f"拉取更新失败: {err or out}")

    logger.info(f"Git pull successful: {out}")
    return {
        "success": True,
        "output": out,
        "message": "系统更新拉取成功！请刷新页面以生效最新版本。",
    }
