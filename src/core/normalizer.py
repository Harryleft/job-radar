"""技能归一化 — 别名映射到标准名称

使用 importlib.resources 定位 skill_aliases.yaml，构建 O(1) 查找 dict。
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# 模块级缓存: lowercase alias → canonical name
_lookup: dict[str, str] | None = None


def _build_lookup() -> dict[str, str]:
    """从 skill_aliases.yaml 构建扁平化查找 dict"""
    lookup: dict[str, str] = {}

    config = _load_aliases()
    for canonical, aliases in config.items():
        # canonical 自身也加入查找表
        lookup[canonical.lower()] = canonical
        if isinstance(aliases, list):
            for alias in aliases:
                lookup[alias.lower()] = canonical
        elif isinstance(aliases, str):
            lookup[aliases.lower()] = canonical

    return lookup


def _load_aliases() -> dict[str, list[str] | str]:
    """加载 skill_aliases.yaml 配置"""
    # 尝试 importlib.resources (打包后)
    try:
        config_ref = resources.files("src.config").joinpath("skill_aliases.yaml")
        config_text = config_ref.read_text(encoding="utf-8")
        return yaml.safe_load(config_text) or {}
    except (FileNotFoundError, TypeError, ModuleNotFoundError, ImportError):
        pass

    # fallback: 相对于项目根目录
    candidates = [
        Path("src/config/skill_aliases.yaml"),
        Path(__file__).parent.parent / "config" / "skill_aliases.yaml",
    ]
    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

    logger.warning("skill_aliases.yaml 未找到，技能归一化将使用原始名称")
    return {}


def _get_lookup() -> dict[str, str]:
    global _lookup
    if _lookup is None:
        _lookup = _build_lookup()
    return _lookup


def normalize_skill(skill: str) -> str:
    """将技能别名映射到标准名称。大小写不敏感。未知技能原样返回。"""
    if not skill or not skill.strip():
        return skill
    lookup = _get_lookup()
    return lookup.get(skill.strip().lower(), skill.strip())


def normalize_skills(skills: list[str]) -> list[str]:
    """批量归一化技能列表"""
    return [normalize_skill(s) for s in skills]


def reset_lookup() -> None:
    """重置查找缓存（测试用）"""
    global _lookup
    _lookup = None
