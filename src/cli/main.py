"""CLI 入口 — Typer 命令定义"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Windows 终端 UTF-8 支持
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.analysis.market import MarketAnalysis
from src.analysis.matcher import Matcher
from src.analysis.recommender import Recommender
from src.core.scorer import RuleBasedScorer
from src.data.loader import load_jobs
from src.data.profile import load_profile

app = typer.Typer(
    name="job-detect",
    help="求职决策 CLI — 不是搜索工具，是决策工具",
    add_completion=False,
)
console = Console()


# ─── 统一错误处理 ───


def _handle_error(exc: Exception) -> None:
    """友好的中文错误提示"""
    if isinstance(exc, FileNotFoundError):
        console.print(f"\n[red]文件未找到:[/red] {exc}")
        console.print("[dim]请检查文件路径是否正确[/dim]")
    elif isinstance(exc, json.JSONDecodeError):
        console.print(f"\n[red]JSON 格式错误:[/red] {exc}")
        file_hint = exc.args[1] if len(exc.args) > 1 else "未知"
        console.print(f"[dim]文件: {file_hint}, 行 {exc.lineno}[/dim]")
    elif isinstance(exc, ValueError) and "YAML" in str(type(exc).__module__):
        console.print(f"\n[red]YAML 格式错误:[/red] {exc}")
        console.print("[dim]请检查 profile.yaml 格式是否正确[/dim]")
    elif isinstance(exc, ValueError):
        console.print(f"\n[red]配置错误:[/red] {exc}")
    else:
        console.print(f"\n[red]错误:[/red] {exc}")
    raise typer.Exit(code=1)


# ─── analyze 命令 ───


@app.command()
def analyze(
    data: str = typer.Option(..., "--data", "-d", help="boss-cli 导出的 JSON 文件路径"),
    profile: str = typer.Option(..., "--profile", "-p", help="用户配置文件 (YAML) 路径"),
    top: int = typer.Option(20, "--top", "-t", help="显示前 N 条推荐"),
    min_score: float = typer.Option(0, "--min-score", help="最低匹配分数过滤"),
) -> None:
    """完整分析: 匹配排名 + 技能差距 + 市场分析"""
    try:
        jobs = load_jobs(data)
        user_profile = load_profile(profile)
    except Exception as exc:
        _handle_error(exc)
        return

    if not jobs:
        console.print("[yellow]数据集中没有岗位数据[/yellow]")
        return

    scorer = RuleBasedScorer(user_profile.scoring)
    matcher = Matcher(scorer)
    recommender = Recommender(matcher)

    # 排名
    ranked = recommender.rank(jobs, user_profile, top_n=top, min_score=min_score)

    # 市场分析
    market = MarketAnalysis(jobs)

    # 技能差距
    gap = recommender.skill_gap_report(jobs, user_profile, top_n=top)

    # 输出
    _print_header()
    _print_ranking_table(ranked)
    _print_market_analysis(market)
    _print_skill_gap(gap)


# ─── match 命令 ───


@app.command()
def match(
    data: str = typer.Option(..., "--data", "-d", help="boss-cli 导出的 JSON 文件路径"),
    profile: str = typer.Option(..., "--profile", "-p", help="用户配置文件 (YAML) 路径"),
    top: int = typer.Option(20, "--top", "-t", help="显示前 N 条推荐"),
    min_score: float = typer.Option(0, "--min-score", help="最低匹配分数过滤"),
) -> None:
    """匹配推荐: 只输出排名表"""
    try:
        jobs = load_jobs(data)
        user_profile = load_profile(profile)
    except Exception as exc:
        _handle_error(exc)
        return

    if not jobs:
        console.print("[yellow]数据集中没有岗位数据[/yellow]")
        return

    scorer = RuleBasedScorer(user_profile.scoring)
    matcher = Matcher(scorer)
    recommender = Recommender(matcher)

    ranked = recommender.rank(jobs, user_profile, top_n=top, min_score=min_score)

    _print_header()
    _print_ranking_table(ranked)


# ─── market 命令 ───


@app.command()
def market(
    data: str = typer.Option(..., "--data", "-d", help="boss-cli 导出的 JSON 文件路径"),
    keyword: str = typer.Option("", "--keyword", "-k", help="关键词过滤"),
) -> None:
    """市场概览: 不需要用户配置，纯数据分析"""
    try:
        jobs = load_jobs(data)
    except Exception as exc:
        _handle_error(exc)
        return

    if not jobs:
        console.print("[yellow]数据集中没有岗位数据[/yellow]")
        return

    # 关键词过滤
    if keyword:
        jobs = [j for j in jobs if keyword in j.job_name or keyword in " ".join(j.skills)]

    if not jobs:
        console.print(f"[yellow]没有匹配 '{keyword}' 的岗位[/yellow]")
        return

    analysis = MarketAnalysis(jobs)
    _print_header()
    _print_market_analysis(analysis, show_keyword=keyword)


# ─── init 命令 ───


@app.command()
def init(
    output: str = typer.Option("profile.yaml", "--output", "-o", help="输出文件路径"),
) -> None:
    """交互式生成用户配置文件"""
    console.print("[bold cyan]Job Detect — 配置文件生成器[/bold cyan]\n")

    skills_str = console.input("[bold]你的技能[/bold] (逗号分隔): ")
    years_str = console.input("[bold]工作年限[/bold] (数字): ")
    cities_str = console.input("[bold]目标城市[/bold] (逗号分隔): ")
    salary_min_str = console.input("[bold]最低薪资[/bold] (如 15K): ")
    salary_max_str = console.input("[bold]最高薪资[/bold] (如 35K): ")
    roles_str = console.input("[bold]目标岗位[/bold] (逗号分隔): ")

    skills = [s.strip() for s in skills_str.split(",") if s.strip()]
    years = int(years_str) if years_str.strip().isdigit() else 3
    cities = [c.strip() for c in cities_str.split(",") if c.strip()]
    roles = [r.strip() for r in roles_str.split(",") if r.strip()]

    content = _generate_profile_yaml(skills, years, cities, salary_min_str, salary_max_str, roles)

    out_path = Path(output)
    out_path.write_text(content, encoding="utf-8")
    console.print(f"\n[green]配置文件已生成:[/green] {out_path.absolute()}")
    console.print(
        "[dim]可以运行: job-detect analyze "
        "--data ./jobs.json --profile ./profile.yaml[/dim]"
    )


# ─── 输出格式化 ───


def _print_header() -> None:
    console.print(Panel("Job Detect — 岗位匹配报告", style="bold cyan", padding=(1, 2)))


def _print_ranking_table(ranked: list) -> None:
    console.print("\n[bold]岗位推荐排名[/bold]")
    console.rule()

    table = Table(show_lines=False, padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("岗位", min_width=16)
    table.add_column("公司", min_width=10)
    table.add_column("匹配度", justify="right", width=6)
    table.add_column("薪资", min_width=12)
    table.add_column("差距技能", min_width=12)

    for i, (job, result) in enumerate(ranked, 1):
        if result.total_score >= 70:
            score_color = "green"
        elif result.total_score >= 40:
            score_color = "yellow"
        else:
            score_color = "red"
        missing = ", ".join(result.missing_skills[:3]) if result.missing_skills else "—"
        table.add_row(
            str(i),
            job.job_name,
            job.brand_name or "—",
            f"[{score_color}]{result.total_score:.0f}%[/{score_color}]",
            job.salary_desc or "面议",
            missing,
        )

    console.print(table)


def _print_market_analysis(analysis: MarketAnalysis, show_keyword: str = "") -> None:
    title = f"市场分析 — {show_keyword}" if show_keyword else "市场分析"
    console.print(f"\n[bold]{title}[/bold]")
    console.rule()

    # 城市分布
    cities = analysis.city_distribution()
    if cities:
        city_str = " ".join(f"{c}({p}%)" for c, p in list(cities.items())[:5])
        console.print(f" 城市: {city_str}")

    # 薪资
    salary = analysis.salary_stats()
    if salary.get("median"):
        console.print(f" 薪资: {salary['min']}-{salary['max']}元 (中位数: {salary['median']}元)")

    # 需求量
    console.print(f" 需求量: {analysis.job_count()} 个岗位")

    # Top 技能
    skills = analysis.skill_frequency(10)
    if skills:
        skill_str = " ".join(f"{s}({p}%)" for s, p in skills[:6])
        console.print(f" Top 技能: {skill_str}")


def _print_skill_gap(gap: dict) -> None:
    console.print("\n[bold]技能差距报告[/bold]")
    console.rule()

    have = gap.get("have", [])
    if have:
        console.print(f" 你已有: {', '.join(s + ' ✓' for s in have)}")

    need = gap.get("need", [])
    if need:
        need_str = ", ".join(f"{s} ({p}%)" for s, p in need[:5])
        console.print(f" 需要补: {need_str}")

    suggest = gap.get("suggest", "")
    if suggest:
        console.print(f" [green]建议优先:[/green] {suggest}")


def _generate_profile_yaml(
    skills: list[str],
    years: int,
    cities: list[str],
    salary_min: str,
    salary_max: str,
    roles: list[str],
) -> str:
    """生成 profile.yaml 内容"""
    skills_yaml = "\n".join(f"  - {s}" for s in skills)
    cities_yaml = ", ".join(cities)
    roles_yaml = "\n".join(f"  - {r}" for r in roles)
    if years >= 8:
        _level = "senior"
    elif years >= 5:
        _level = "mid-senior"
    elif years >= 3:
        _level = "mid"
    else:
        _level = "junior"

    return f"""\
skills:
{skills_yaml}

experience:
  years: {years}
  level: {_level}

preferences:
  cities: [{cities_yaml}]
  salary_min: {salary_min}
  salary_max: {salary_max}

target_roles:
{roles_yaml}

# 评分权重（可选，默认 40/30/30）
# scoring:
#   skill: 0.4
#   experience: 0.3
#   salary: 0.3

# BOSS直聘 cookie（预留，用于后续自动化采集）
# boss_cookie: ""
"""


if __name__ == "__main__":
    app()
