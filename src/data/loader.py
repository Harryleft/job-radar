"""数据加载器 — 读取 boss-cli JSON 导出

支持格式:
1. boss-cli export envelope: {"ok": true, "data": {"jobList": [...]}}
2. boss-cli export flat list: {"ok": true, "data": [...]}
3. 纯 Job 数组: [{"jobName": "...", ...}, ...]
4. 单个 Job 对象: {"jobName": "...", ...}
"""

from __future__ import annotations

import json
from pathlib import Path

from src.data.models import Job


def load_jobs(data_path: str) -> list[Job]:
    """从 JSON 文件加载岗位数据

    Args:
        data_path: JSON 文件路径

    Returns:
        Job 列表

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
        ValueError: 无法识别的数据格式
    """
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"数据文件不存在: {data_path}")

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    return _parse_jobs(raw)


def _parse_jobs(raw: object) -> list[Job]:
    """从多种 JSON 结构中解析 Job 列表"""
    # 纯数组: [job1, job2, ...]
    if isinstance(raw, list):
        return [Job.model_validate(item) for item in raw]

    if not isinstance(raw, dict):
        raise ValueError(f"无法识别的 JSON 结构: {type(raw).__name__}")

    # boss-cli envelope: {"ok": true, "data": ...}
    if "data" in raw:
        data = raw["data"]
        # data 是 {"jobList": [...]}
        if isinstance(data, dict) and "jobList" in data:
            return [Job.model_validate(item) for item in data["jobList"]]
        # data 是 {"job_list": [...]}
        if isinstance(data, dict) and "job_list" in data:
            return [Job.model_validate(item) for item in data["job_list"]]
        # data 直接是数组
        if isinstance(data, list):
            return [Job.model_validate(item) for item in data]

    # 可能是单条 Job
    if "jobName" in raw:
        return [Job.model_validate(raw)]

    raise ValueError("无法识别的 JSON 结构，期望 boss-cli 导出格式或 Job 数组")
