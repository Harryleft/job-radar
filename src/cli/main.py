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

from src.ai.chains import run_extract, run_recommend
from src.ai.profile_builder import career_path_to_profile
from src.ai.resume_parser import pdf_to_markdown
from src.ai.schemas import CareerRecommendation, ResumeExtract
from src.analysis.market import MarketAnalysis
from src.analysis.matcher import Matcher
from src.analysis.recommender import Recommender
from src.core.scorer import RuleBasedScorer
from src.data.loader import load_jobs
from src.data.models import Job
from src.data.profile import load_profile

app = typer.Typer(
    name="job-radar",
    help="求职决策 CLI — 岗位雷达，不是搜索工具，是决策工具",
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
    elif isinstance(exc, ValueError) and exc.__class__.__name__ in (
        "ScannerError",
        "ParserError",
        "YAMLError",
    ):
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


# ─── advisor 命令 ───


@app.command()
def advisor(
    resume: str = typer.Option(..., "--resume", "-r", help="简历 PDF 文件路径"),
    data: str = typer.Option(
        "", "--data", "-d", help="岗位数据 JSON 文件路径（省略则只做简历分析）"
    ),
    paths: int = typer.Option(3, "--paths", "-p", help="推荐职业路径数量 (1-5)"),
    top: int = typer.Option(10, "--top", "-t", help="每条路径显示前 N 个匹配岗位"),
    html: bool = typer.Option(False, "--html", help="同时生成可视化 HTML 报告"),
) -> None:
    """简历驱动的职业路径推荐：上传简历 → AI 分析 → 推荐职业方向 → 市场对比"""
    # 参数校验
    if paths < 1 or paths > 5:
        console.print("[red]--paths 参数必须在 1-5 之间[/red]")
        raise typer.Exit(code=1)

    try:
        # Step 1: PDF → Markdown
        console.print("[dim]正在解析简历...[/dim]")
        md_text = pdf_to_markdown(resume)

        # Step 2: Chain 1 — 结构化提取
        console.print("[dim]正在分析简历内容...[/dim]")
        extract = run_extract(md_text)
        _print_extract_summary(extract)

        # Step 3: Chain 2 — 职业路径推荐
        console.print(f"[dim]正在推荐 {paths} 条职业路径...[/dim]")
        recommendation = run_recommend(extract, num_paths=paths)

        if not data:
            # 只做简历分析，输出推荐路径即可
            _print_recommendation_only(recommendation, extract)
            return

        # Step 4: 加载岗位数据
        console.print("[dim]正在加载岗位数据...[/dim]")
        jobs = load_jobs(data)
        if not jobs:
            console.print("[yellow]岗位数据为空，仅输出推荐路径[/yellow]")
            _print_recommendation_only(recommendation, extract)
            return

        # Step 5: 每条路径 → 虚拟 Profile → 匹配 + 市场分析
        _print_header()
        _print_path_comparison(recommendation, extract, jobs, top)

        # Step 6: 可选 HTML 报告
        if html:
            from src.report.html_report import generate_html_report

            report_data = _build_report_data(recommendation, extract, jobs, top)
            html_path = generate_html_report(report_data)
            console.print(f"\n[green]HTML 报告已生成:[/green] {html_path}")

    except OSError as exc:
        console.print(f"\n[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        _handle_error(exc)


# ─── init 命令 ───


@app.command()
def init(
    output: str = typer.Option("profile.yaml", "--output", "-o", help="输出文件路径"),
) -> None:
    """交互式生成用户配置文件"""
    console.print("[bold cyan]Job Radar — 配置文件生成器[/bold cyan]\n")

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
        "[dim]可以运行: job-radar analyze "
        "--data ./jobs.json --profile ./profile.yaml[/dim]"
    )


# ─── 输出格式化 ───


def _print_header() -> None:
    console.print(Panel("Job Radar — 岗位匹配报告", style="bold cyan", padding=(1, 2)))


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


# ─── advisor 输出函数 ───


def _build_report_data(
    recommendation: CareerRecommendation,
    extract: ResumeExtract,
    jobs: list[Job],
    top_n: int,
) -> dict:
    """构建 HTML 报告所需的数据字典"""
    report: dict = {
        "resume": {
            "skills": extract.skills,
            "experience_years": extract.experience_years,
            "education": extract.education,
            "highlights": extract.highlights,
            "work_history": extract.work_history,
        },
        "paths": [],
        "total_jobs": len(jobs),
    }

    for path in recommendation.paths:
        profile = career_path_to_profile(path, extract)
        scorer = RuleBasedScorer(profile.scoring)
        matcher = Matcher(scorer)

        related = [
            j
            for j in jobs
            if path.title in j.job_name
            or any(kw in j.job_name for kw in path.title.split("/"))
        ]
        if not related:
            core_words = [w for w in path.title if len(w) >= 2]
            related = [j for j in jobs if any(w in j.job_name for w in core_words)]
        if not related:
            related = jobs

        ranked = matcher.match_all(related, profile)
        ranked.sort(key=lambda x: x[1].total_score, reverse=True)

        market = MarketAnalysis(related)
        salary = market.salary_stats()
        cities = market.city_distribution()

        path_data: dict = {
            "title": path.title,
            "match_reason": path.match_reason,
            "salary_range": path.salary_range,
            "required_skills": path.required_skills,
            "related_jobs": len(related),
            "market_salary": salary,
            "market_cities": dict(list(cities.items())[:5]),
            "top_jobs": [],
        }

        for job, result in ranked[:top_n]:
            job_data: dict = {
                "job_name": job.job_name,
                "brand_name": job.brand_name or "—",
                "salary_desc": job.salary_desc or "面议",
                "total_score": round(result.total_score, 1),
                "skill_overlap": round(result.skill_overlap * 100)
                if result.skill_overlap
                else None,
                "experience_match": round(result.experience_match * 100)
                if result.experience_match
                else None,
                "salary_fit": round(result.salary_fit * 100)
                if result.salary_fit
                else None,
                "matched_skills": result.matched_skills[:6],
                "missing_skills": result.missing_skills[:4],
                "city_name": job.city_name,
                "industry_name": job.industry_name,
                "company_scale": job.company_scale,
                "company_stage": job.company_stage,
                "job_experience": job.job_experience,
                "job_degree": job.job_degree,
            }
            path_data["top_jobs"].append(job_data)

        report["paths"].append(path_data)

    return report


def _print_extract_summary(extract: ResumeExtract) -> None:
    """打印简历提取摘要"""
    console.print("\n[bold]简历分析摘要[/bold]")
    console.rule()
    console.print(f" 技能: {', '.join(extract.skills)}")
    console.print(f" 工作年限: {extract.experience_years} 年")
    if extract.education:
        console.print(f" 学历: {extract.education}")
    if extract.highlights:
        console.print(f" 亮点: {'; '.join(extract.highlights[:3])}")


def _print_recommendation_only(
    recommendation: CareerRecommendation, extract: ResumeExtract
) -> None:
    """只做简历分析时的输出"""
    console.print("\n[bold]推荐职业路径[/bold]")
    console.rule()

    for i, path in enumerate(recommendation.paths, 1):
        level = _infer_level_display(extract.experience_years)
        console.print(f"\n [cyan]路径 {i}:[/cyan] {path.title} ({level})")
        console.print(f" [dim]匹配理由:[/dim] {path.match_reason}")
        if path.salary_range:
            console.print(f" [dim]预估薪资:[/dim] {path.salary_range}")
        if path.required_skills:
            console.print(f" [dim]补充技能:[/dim] {', '.join(path.required_skills)}")


def _print_path_comparison(
    recommendation: CareerRecommendation,
    extract: ResumeExtract,
    jobs: list[Job],
    top_n: int,
) -> None:
    """输出职业路径对比报告（统一表 + 分路径详情）"""
    # ─── 总览表 ───
    console.print(Panel("Job Radar — 职业路径推荐报告", style="bold cyan", padding=(1, 2)))
    console.print(f"[dim]基于: 简历分析 + {len(jobs)} 个岗位数据[/dim]\n")

    summary_table = Table(show_lines=False, padding=(0, 1), title="推荐职业路径")
    summary_table.add_column("#", style="dim", width=3)
    summary_table.add_column("职业方向", min_width=14)
    summary_table.add_column("匹配岗位", justify="right", width=8)
    summary_table.add_column("薪资中位数", justify="right", width=10)
    summary_table.add_column("Top 城市", min_width=16)
    summary_table.add_column("推荐理由", min_width=20)

    for i, path in enumerate(recommendation.paths, 1):
        profile = career_path_to_profile(path, extract)
        scorer = RuleBasedScorer(profile.scoring)
        matcher = Matcher(scorer)

        # 关键词筛选相关岗位
        related = [j for j in jobs if path.title in j.job_name or any(
            kw in j.job_name for kw in path.title.split("/")
        )]
        if not related:
            # 宽松匹配：用岗位名称中的核心词
            core_words = [w for w in path.title if len(w) >= 2]
            related = [j for j in jobs if any(w in j.job_name for w in core_words)]
        if not related:
            related = jobs  # fallback: 全量

        ranked = matcher.match_all(related, profile)
        ranked.sort(key=lambda x: x[1].total_score, reverse=True)
        top_ranked = ranked[:top_n]

        # 市场分析
        market = MarketAnalysis(related)
        salary = market.salary_stats()
        cities = market.city_distribution()

        salary_display = f"{salary['median']}元" if salary.get("median") else "—"
        city_display = " ".join(f"{c}({p}%)" for c, p in list(cities.items())[:3]) or "—"

        summary_table.add_row(
            str(i),
            path.title,
            str(len(top_ranked)),
            salary_display,
            city_display,
            path.match_reason[:30] + ("..." if len(path.match_reason) > 30 else ""),
        )

        # ─── 分路径详情 ───
        console.print(f"\n[bold cyan]路径 {i}: {path.title}[/bold cyan]")
        console.rule()
        console.print(f" [dim]匹配理由:[/dim] {path.match_reason}")
        if path.salary_range:
            console.print(f" [dim]预估薪资:[/dim] {path.salary_range}")
        if path.required_skills:
            console.print(f" [dim]需补充技能:[/dim] {', '.join(path.required_skills)}")

        # 市场概况
        _print_market_analysis(market, show_keyword=path.title)

        # Top 匹配岗位（详细卡片）
        if top_ranked:
            console.print("\n [bold]推荐岗位[/bold]")
            for j, (job, result) in enumerate(top_ranked[:5], 1):
                if result.total_score >= 70:
                    score_color, score_tag = "green", "强烈推荐"
                elif result.total_score >= 50:
                    score_color, score_tag = "yellow", "值得尝试"
                else:
                    score_color, score_tag = "red", "待提升"

                console.print(
                    f"  [bold][{score_color}]●[/[{score_color}][/bold]] "
                    f"[bold]{j}. {job.job_name}[/bold]"
                )
                console.print(
                    f"      {job.brand_name or '—'}"
                    f"  |  {job.salary_desc or '面议'}"
                    f"  |  匹配度 [{score_color}]{result.total_score:.0f}%[/{score_color}]"
                    f" ({score_tag})"
                )
                # 匹配维度
                dims = []
                if result.skill_overlap is not None:
                    dims.append(f"技能 {result.skill_overlap:.0%}")
                if result.experience_match is not None:
                    dims.append(f"经验 {result.experience_match:.0%}")
                if result.salary_fit is not None:
                    dims.append(f"薪资 {result.salary_fit:.0%}")
                if dims:
                    console.print(f"      维度: {' / '.join(dims)}")
                # 技能详情
                if result.matched_skills:
                    console.print(
                        f"      匹配技能: {', '.join(result.matched_skills[:6])}"
                    )
                if result.missing_skills:
                    console.print(
                        f"      缺少技能: [yellow]{', '.join(result.missing_skills[:4])}[/yellow]"
                    )
                # 公司信息
                extras = []
                if job.city_name:
                    extras.append(job.city_name)
                if job.industry_name:
                    extras.append(job.industry_name)
                if job.company_scale:
                    extras.append(job.company_scale)
                if job.company_stage:
                    extras.append(job.company_stage)
                if job.job_experience:
                    extras.append(f"要求: {job.job_experience}")
                if job.job_degree:
                    extras.append(f"学历: {job.job_degree}")
                if extras:
                    console.print(f"      {' | '.join(extras)}")
                console.print()

    # 打印总览
    console.print()
    console.print(summary_table)


def _infer_level_display(years: int) -> str:
    if years >= 8:
        return "Senior"
    if years >= 5:
        return "Mid-Senior"
    if years >= 3:
        return "Mid"
    return "Junior"


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
