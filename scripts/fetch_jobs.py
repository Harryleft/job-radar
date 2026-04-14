"""一键采集岗位数据 — 直接用 BossClient API，绕过 CLI 凭证删除

用法:
  1. boss login                        # 扫码登录（只需一次）
  2. python scripts/fetch_jobs.py      # 运行采集
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "real_jobs.json"
CRED_FILE = Path.home() / ".config" / "boss-cli" / "credential.json"

CITIES = {
    "101210100": "杭州",
    "101310100": "海口",
    "101270100": "成都",
    "101180100": "郑州",
    "101190100": "南京",
}

KEYWORDS = ["数据分析师", "AI工程师", "Python开发", "产品经理"]


def main():
    # 读取凭证
    if not CRED_FILE.exists():
        print("请先运行: boss login")
        sys.exit(1)

    with open(CRED_FILE, encoding="utf-8") as f:
        cred_data = json.load(f)
    cookies = cred_data.get("cookies", {})

    # 加载已有数据
    seen_ids: set[str] = set()
    all_jobs: list[dict] = []
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        existing = raw.get("data", {}).get("jobList", []) if isinstance(raw, dict) else raw
        all_jobs = list(existing)
        seen_ids = {j.get("encryptJobId", "") for j in all_jobs}

    print(f"已有 {len(all_jobs)} 条，开始采集...\n")

    # 直接用 boss-cli 的 BossClient（不经过 CLI 层，不会删除凭证）
    from boss_cli.auth import Credential
    from boss_cli.client import BossClient

    cred = Credential(cookies=cookies)

    with BossClient(credential=cred, request_delay=0.3) as client:
        for code, name in CITIES.items():
            for kw in KEYWORDS:
                try:
                    data = client.search_jobs(query=kw, city=code, page=1, page_size=30)
                    jobs = data.get("jobList", [])
                    new = 0
                    for j in jobs:
                        eid = j.get("encryptJobId", "")
                        if eid and eid not in seen_ids:
                            seen_ids.add(eid)
                            all_jobs.append(j)
                            new += 1
                    print(f"  {name}/{kw}: +{new} (total: {len(all_jobs)})")
                    if not jobs:
                        print("  ⚠ 返回为空，可能 token 已过期")
                        break
                except Exception as e:
                    err_msg = str(e)[:80]
                    print(f"  {name}/{kw}: ✗ {err_msg}")
                    break

    # 统计
    cities = Counter(j.get("cityName", "") for j in all_jobs)
    print(f"\n总计: {len(all_jobs)} 条")
    for c, n in cities.most_common():
        print(f"  {c}: {n}")

    # 保存
    output = {"ok": True, "data": {"jobList": all_jobs}}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到 {DATA_FILE}")


if __name__ == "__main__":
    main()
