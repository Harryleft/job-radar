"""BOSS直聘登录 — CDP 连接真实 Chrome + 手动 Cookie 导入（降级方案）

两种登录方式:
  1. cdp_login()  — 启动真实 Chrome，用户扫码后通过 CDP 自动提取 Cookie（推荐）
  2. manual_login() — 手动从浏览器 Cookie 管理页复制粘贴（降级方案）
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import webbrowser
from pathlib import Path

# 与 boss-cli 相同的常量，确保输出格式兼容
CREDENTIAL_FILE = Path.home() / ".config" / "boss-cli" / "credential.json"
REQUIRED_COOKIES = {"__zp_stoken__", "wt2", "wbg", "zp_at"}
BOSS_LOGIN_URL = "https://www.zhipin.com/web/user/?ka=header-login"
BOSS_BASE_URL = "https://www.zhipin.com"
COOKIE_SETTINGS_URL = "edge://settings/siteData?search=zhipin.com"

# Chrome 调试端口
DEBUG_PORT = 9222

# Windows Chrome 路径（按优先级搜索）
_CHROME_SEARCH_PATHS = [
    Path(r"C:\Program Files\Google\Chrome Dev\Application\chrome.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")),
]


class MissingCookiesError(RuntimeError):
    """登录后缺少必需 Cookie"""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"缺少必需 Cookie: {', '.join(missing)}")


class CookieParseError(RuntimeError):
    """用户粘贴的 Cookie 格式无法解析"""


class ChromeNotFoundError(RuntimeError):
    """未找到 Chrome 浏览器"""


class PlaywrightNotInstalledError(RuntimeError):
    """Playwright 未安装"""


# ── Chrome 查找 ───────────────────────────────────────────────────────


def _find_chrome() -> Path | None:
    """在常见路径中搜索 Chrome 可执行文件"""
    for p in _CHROME_SEARCH_PATHS:
        if p.exists():
            return p
    return None


# ── CDP 登录（推荐方案）───────────────────────────────────────────────


def cdp_login() -> dict[str, str]:
    """启动真实 Chrome，用户扫码后通过 CDP 自动提取 Cookie。

    流程:
      1. 启动独立 Chrome 实例（带调试端口 + 临时 profile）
      2. 打开登录页，用户扫码
      3. 登录后跳转主页，等待 __zp_stoken__ JS 生成
      4. 通过 CDP 提取所有 Cookie（含 HttpOnly）
      5. 验证 4 个必需 Cookie 齐全

    Returns:
        cookies dict，格式兼容 boss-cli Credential

    Raises:
        ChromeNotFoundError: 未找到 Chrome
        PlaywrightNotInstalledError: Playwright 未安装
        MissingCookiesError: 缺少必需 Cookie
    """
    # 检查 Chrome
    chrome_path = _find_chrome()
    if not chrome_path:
        raise ChromeNotFoundError(
            "未找到 Chrome 浏览器，请安装 Google Chrome\n"
            "下载地址: https://www.google.com/chrome/"
        )

    # 检查 Playwright
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PlaywrightNotInstalledError(
            "Playwright 未安装，请运行:\n"
            "  pip install playwright && playwright install chromium"
        ) from exc

    print("\n=== BOSS直聘登录（CDP 模式）===\n")

    # 创建临时 profile 目录
    tmp_dir = tempfile.mkdtemp(prefix="job-radar-chrome-")
    proc: subprocess.Popen | None = None

    try:
        # 启动独立 Chrome 实例
        print(f"正在启动 Chrome ({chrome_path.name})...")
        cmd = [
            str(chrome_path),
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={tmp_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            BOSS_LOGIN_URL,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 等待用户扫码登录
        print("请在 Chrome 中完成扫码登录，登录成功后按回车继续...")
        input()

        # 通过 CDP 连接并提取 Cookie
        print("正在提取 Cookie...")
        cookie_dict = _extract_cookies_via_cdp(sync_playwright)

        # 验证
        missing = sorted(REQUIRED_COOKIES - set(cookie_dict.keys()))
        if missing:
            raise MissingCookiesError(missing)

        return cookie_dict

    finally:
        # 清理
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_cookies_via_cdp(sync_playwright_factory) -> dict[str, str]:
    """通过 Playwright CDP 连接提取 Cookie"""
    with sync_playwright_factory() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{DEBUG_PORT}")
        contexts = browser.contexts

        if not contexts:
            raise MissingCookiesError(sorted(REQUIRED_COOKIES))

        # 导航到主页确保 JS 执行生成 __zp_stoken__
        page = contexts[0].pages[0] if contexts[0].pages else contexts[0].new_page()

        if "zhipin.com" not in (page.url or ""):
            page.goto(BOSS_BASE_URL, wait_until="domcontentloaded", timeout=10000)
            # 等待 __zp_stoken__ 生成
            import contextlib

            with contextlib.suppress(Exception):
                page.wait_for_function(
                    'document.cookie.includes("__zp_stoken__")',
                    timeout=8000,
                )

        # 额外等一下确保 JS 执行完成
        time.sleep(1)

        # 提取所有 Cookie
        all_cookies = contexts[0].cookies(BOSS_BASE_URL)
        cookie_dict = {c["name"]: c["value"] for c in all_cookies}

    return cookie_dict


# ── 手动登录（降级方案）────────────────────────────────────────────────


def manual_login() -> dict[str, str]:
    """打开浏览器让用户手动登录，引导从 Cookie 设置页提取。

    Returns:
        cookies dict，格式兼容 boss-cli Credential

    Raises:
        MissingCookiesError: 缺少必需 Cookie
    """
    print("\n=== BOSS直聘登录（手动模式）===\n")

    # Step 1: 打开登录页
    print("正在打开登录页...")
    webbrowser.open(BOSS_LOGIN_URL)
    print("请在浏览器中完成扫码登录，登录成功后按回车继续...")
    input()

    # Step 2: 打开 Cookie 管理页
    print("\n正在打开浏览器 Cookie 管理页...")
    webbrowser.open(COOKIE_SETTINGS_URL)
    print(
        "\n请在 Cookie 管理页中找到 zhipin.com，点击进入查看所有 Cookie。\n"
        "逐个输入以下 4 个 Cookie 的值（直接回车跳过，但不建议）:\n"
    )

    # Step 3: 逐个输入
    cookies: dict[str, str] = {}
    for key in ("__zp_stoken__", "wt2", "wbg", "zp_at"):
        val = input(f"  {key}: ").strip()
        if val:
            cookies[key] = val
        else:
            print(f"    ⚠ 跳过了 {key}")

    # Step 4: 验证
    missing = sorted(REQUIRED_COOKIES - set(cookies.keys()))
    if missing:
        raise MissingCookiesError(missing)

    return cookies


# ── Cookie 解析 ──────────────────────────────────────────────────────


def _parse_cookie_input(raw: str) -> dict[str, str]:
    """解析用户粘贴的 Cookie 内容。

    支持格式:
      - JSON: {"__zp_stoken__": "abc", "wt2": "def"}
      - Cookie 字符串: __zp_stoken__=abc; wt2=def
    """
    raw = raw.strip()

    # 尝试 JSON 解析
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        pass

    # 尝试 Cookie 字符串解析
    if "=" in raw:
        cookies: dict[str, str] = {}
        for pair in raw.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, _, val = pair.partition("=")
                cookies[key.strip()] = val.strip()
        if cookies:
            return cookies

    raise CookieParseError("无法解析输入内容，请确保是 JSON 或 Cookie 字符串格式")


# ── 凭据持久化 ────────────────────────────────────────────────────────


def save_credential(cookies: dict[str, str]) -> Path:
    """将 Cookie 保存到 boss-cli 凭据文件。

    格式兼容 boss-cli 的 Credential.to_dict():
    {"cookies": {...}, "saved_at": <unix_timestamp>}
    """
    CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"cookies": cookies, "saved_at": time.time()}
    CREDENTIAL_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return CREDENTIAL_FILE


def load_credential() -> dict[str, str] | None:
    """加载已保存的凭据，返回 cookies dict 或 None。"""
    if not CREDENTIAL_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIAL_FILE.read_text(encoding="utf-8"))
        return data.get("cookies")
    except (json.JSONDecodeError, KeyError):
        return None


# ── 辅助函数 ──────────────────────────────────────────────────────────


def check_status() -> None:
    """打印当前凭据状态（用于 CLI 输出）。"""
    cookies = load_credential()
    if not cookies:
        print("未登录 — 请运行: python scripts/boss_login.py")
        return

    missing = sorted(REQUIRED_COOKIES - set(cookies.keys()))
    if missing:
        print(f"凭证不完整，缺少: {', '.join(missing)}")
    else:
        print(f"已登录 ({len(cookies)} 个 cookie)")
        for key in sorted(REQUIRED_COOKIES):
            val = cookies.get(key, "")
            display = f"{val[:20]}..." if len(val) > 20 else val
            print(f"  {key}: {display}")
