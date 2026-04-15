"""BOSS直聘登录 — CDP 自动提取 / 手动 Cookie 导入

用法:
  python scripts/boss_login.py                    # CDP 模式（自动提取 Cookie）
  python scripts/boss_login.py --manual           # 手动输入 Cookie
  python scripts/boss_login.py --check            # 检查当前凭证状态
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="BOSS直聘登录")
    parser.add_argument("--check", action="store_true", help="检查当前登录状态")
    parser.add_argument("--manual", action="store_true", help="使用手动 Cookie 输入模式")
    args = parser.parse_args()

    from src.auth.playwright_login import (
        CookieParseError,
        MissingCookiesError,
        cdp_login,
        check_status,
        manual_login,
        save_credential,
    )

    if args.check:
        check_status()
        return

    try:
        if args.manual:
            cookies = manual_login()
        else:
            try:
                cookies = cdp_login()
            except RuntimeError as exc:
                print(f"\n提示: {exc}")
                print("降级到手动 Cookie 输入模式\n")
                cookies = manual_login()

        path = save_credential(cookies)
        print(f"\n登录成功！获取到 {len(cookies)} 个 cookie")
        print(f"凭证已保存到: {path}")
    except (CookieParseError, MissingCookiesError) as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(0)


if __name__ == "__main__":
    main()
