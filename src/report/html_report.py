"""生成可视化 HTML 职业路径推荐报告"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def generate_html_report(report_data: dict | Path | str) -> str:
    """从 report_data 生成完整 HTML 报告，返回文件路径"""
    if isinstance(report_data, (str, Path)):
        with open(report_data, encoding="utf-8") as f:
            report_data = json.load(f)

    resume = report_data["resume"]
    paths = report_data["paths"]
    total_jobs = report_data["total_jobs"]

    # 技能标签 HTML
    skill_tags = " ".join(
        f'<span class="skill-tag">{s}</span>' for s in resume["skills"]
    )

    # 亮点 HTML
    highlights_html = ""
    for h in resume["highlights"][:5]:
        highlights_html += f'<div class="highlight-item">{h}</div>\n'

    # 路径卡片 HTML
    path_cards_html = ""
    path_colors = ["#6366f1", "#06b6d4", "#f59e0b"]
    path_icons = ["&#x1f9e0;", "&#x1f4ca;", "&#x1f9ea;"]

    for i, path in enumerate(paths):
        color = path_colors[i % len(path_colors)]
        icon = path_icons[i % len(path_icons)]

        # 市场薪资
        salary = path["market_salary"]
        salary_html = ""
        if salary.get("median"):
            salary_html = f"""
            <div class="stat">
                <div class="stat-label">薪资中位数</div>
                <div class="stat-value">{salary['median']:,}元</div>
            </div>
            <div class="stat">
                <div class="stat-label">薪资范围</div>
                <div class="stat-value">{salary['min']:,}-{salary['max']:,}元</div>
            </div>
            """

        # 需补充技能
        req_skills_html = " ".join(
            f'<span class="req-skill">{s}</span>'
            for s in (path.get("required_skills") or [])
        )

        # 岗位列表
        jobs_html = ""
        for j in path["top_jobs"][:8]:
            score = j["total_score"]
            if score >= 70:
                score_class = "high"
                tag = "强烈推荐"
            elif score >= 55:
                score_class = "mid"
                tag = "值得尝试"
            else:
                score_class = "low"
                tag = "待提升"

            # 三维分数条
            dims_html = ""
            for dim_name, dim_key, dim_color in [
                ("技能", "skill_overlap", "#6366f1"),
                ("经验", "experience_match", "#10b981"),
                ("薪资", "salary_fit", "#f59e0b"),
            ]:
                val = j.get(dim_key)
                if val is not None:
                    dims_html += f"""
                    <div class="dim-item">
                        <span class="dim-label">{dim_name}</span>
                        <div class="dim-bar-bg">
                            <div class="dim-bar" style="width:{val}%;background:{dim_color}"></div>
                        </div>
                        <span class="dim-val">{val}%</span>
                    </div>
                    """

            matched_html = ""
            if j.get("matched_skills"):
                tags = " ".join(
                    f'<span class="m-skill">{s}</span>'
                    for s in j["matched_skills"]
                )
                matched_html = f'<div class="job-skills matched">匹配: {tags}</div>'

            missing_html = ""
            if j.get("missing_skills"):
                tags = " ".join(
                    f'<span class="x-skill">{s}</span>'
                    for s in j["missing_skills"]
                )
                missing_html = f'<div class="job-skills missing">缺少: {tags}</div>'

            meta_parts = []
            if j.get("city_name"):
                meta_parts.append(j["city_name"])
            if j.get("job_experience"):
                meta_parts.append(f"要求: {j['job_experience']}")
            if j.get("job_degree"):
                meta_parts.append(f"学历: {j['job_degree']}")
            meta_html = " | ".join(meta_parts) if meta_parts else ""

            jobs_html += f"""
            <div class="job-card {score_class}">
                <div class="job-header">
                    <div class="job-title">{j['job_name']}</div>
                    <div class="job-score {score_class}">
                        <span class="score-num">{score:.0f}%</span>
                        <span class="score-tag">{tag}</span>
                    </div>
                </div>
                <div class="job-company">
                    <span class="company-name">{j['brand_name']}</span>
                    <span class="salary">{j['salary_desc']}</span>
                </div>
                <div class="job-dims">{dims_html}</div>
                {matched_html}
                {missing_html}
                <div class="job-meta">{meta_html}</div>
            </div>
            """

        path_cards_html += f"""
        <div class="path-card" data-path="{i}">
            <div class="path-header" style="border-left: 4px solid {color}">
                <div class="path-icon">{icon}</div>
                <div class="path-info">
                    <h3 class="path-title">{path['title']}</h3>
                    <p class="path-reason">{path['match_reason']}</p>
                </div>
                <div class="path-salary-badge">
                    {path.get('salary_range') or '面议'}
                </div>
            </div>
            <div class="path-stats">
                <div class="stat">
                    <div class="stat-label">相关岗位</div>
                    <div class="stat-value">{path['related_jobs']}</div>
                </div>
                {salary_html}
                <div class="stat">
                    <div class="stat-label">需补充技能</div>
                    <div class="stat-value req-skills">{req_skills_html}</div>
                </div>
            </div>
            <div class="path-jobs">
                <h4>推荐岗位 TOP 8</h4>
                {jobs_html}
            </div>
        </div>
        """

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Radar — 职业路径推荐报告</title>
<style>
:root {{
    --bg: #0f172a;
    --card: #1e293b;
    --card-hover: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text-dim: #94a3b8;
    --accent: #6366f1;
    --green: #10b981;
    --yellow: #f59e0b;
    --red: #ef4444;
    --cyan: #06b6d4;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: -apple-system, "PingFang SC", "Noto Sans SC", "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 0;
}}

.container {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 40px 24px;
}}

/* Hero */
.hero {{
    text-align: center;
    padding: 48px 0 32px;
}}
.hero h1 {{
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, var(--accent), var(--cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}}
.hero .subtitle {{
    color: var(--text-dim);
    font-size: 1rem;
}}
.hero .meta {{
    margin-top: 12px;
    font-size: 0.85rem;
    color: var(--text-dim);
}}

/* Profile Section */
.profile-section {{
    background: var(--card);
    border-radius: 16px;
    padding: 28px 32px;
    margin: 32px 0;
    border: 1px solid var(--border);
}}
.profile-section h2 {{
    font-size: 1.2rem;
    margin-bottom: 16px;
    color: var(--cyan);
}}
.profile-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}}
.profile-item {{
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 14px 18px;
}}
.profile-item .label {{
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-bottom: 4px;
}}
.profile-item .value {{
    font-size: 1.1rem;
    font-weight: 600;
}}
.skills-wrap {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
}}
.skill-tag {{
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.82rem;
    border: 1px solid rgba(99,102,241,0.25);
}}
.highlight-item {{
    font-size: 0.88rem;
    color: var(--text-dim);
    padding: 4px 0 4px 16px;
    border-left: 2px solid var(--accent);
    margin: 6px 0;
}}

/* Path Cards */
.path-card {{
    background: var(--card);
    border-radius: 16px;
    margin: 28px 0;
    border: 1px solid var(--border);
    overflow: hidden;
}}
.path-header {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 24px 28px;
    background: rgba(255,255,255,0.02);
}}
.path-icon {{
    font-size: 2rem;
    width: 48px;
    text-align: center;
    flex-shrink: 0;
}}
.path-info {{
    flex: 1;
    min-width: 0;
}}
.path-title {{
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 4px;
}}
.path-reason {{
    font-size: 0.88rem;
    color: var(--text-dim);
}}
.path-salary-badge {{
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(6,182,212,0.2));
    padding: 8px 18px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 1rem;
    white-space: nowrap;
    border: 1px solid rgba(99,102,241,0.3);
}}
.path-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px;
    padding: 16px 28px;
    border-bottom: 1px solid var(--border);
}}
.stat {{
    padding: 8px 0;
}}
.stat-label {{
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-bottom: 4px;
}}
.stat-value {{
    font-size: 1rem;
    font-weight: 600;
}}
.req-skills {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}}
.req-skill {{
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    border: 1px solid rgba(245,158,11,0.25);
}}

/* Jobs */
.path-jobs {{
    padding: 20px 28px 28px;
}}
.path-jobs h4 {{
    font-size: 1rem;
    margin-bottom: 16px;
    color: var(--cyan);
}}
.job-card {{
    background: rgba(255,255,255,0.03);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
    border: 1px solid var(--border);
    transition: border-color 0.2s;
}}
.job-card:hover {{
    border-color: var(--accent);
}}
.job-card.high {{ border-left: 3px solid var(--green); }}
.job-card.mid {{ border-left: 3px solid var(--yellow); }}
.job-card.low {{ border-left: 3px solid var(--red); }}

.job-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}}
.job-title {{
    font-size: 1rem;
    font-weight: 600;
}}
.job-score {{
    display: flex;
    align-items: center;
    gap: 8px;
}}
.score-num {{
    font-size: 1.2rem;
    font-weight: 800;
}}
.job-score.high .score-num {{ color: var(--green); }}
.job-score.mid .score-num {{ color: var(--yellow); }}
.job-score.low .score-num {{ color: var(--red); }}
.score-tag {{
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 8px;
}}
.job-score.high .score-tag {{ background: rgba(16,185,129,0.15); color: #6ee7b7; }}
.job-score.mid .score-tag {{ background: rgba(245,158,11,0.15); color: #fcd34d; }}
.job-score.low .score-tag {{ background: rgba(239,68,68,0.15); color: #fca5a5; }}

.job-company {{
    display: flex;
    gap: 16px;
    align-items: center;
    margin-bottom: 10px;
    font-size: 0.9rem;
}}
.company-name {{ color: var(--text-dim); }}
.salary {{
    color: var(--green);
    font-weight: 600;
}}

/* Dimension bars */
.job-dims {{
    display: flex;
    gap: 12px;
    margin-bottom: 10px;
    flex-wrap: wrap;
}}
.dim-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.78rem;
    min-width: 140px;
}}
.dim-label {{
    color: var(--text-dim);
    width: 24px;
    text-align: right;
}}
.dim-bar-bg {{
    flex: 1;
    height: 6px;
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    overflow: hidden;
}}
.dim-bar {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease;
}}
.dim-val {{
    color: var(--text-dim);
    width: 32px;
}}

/* Skills */
.job-skills {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    margin: 6px 0;
    font-size: 0.8rem;
}}
.m-skill {{
    background: rgba(16,185,129,0.12);
    color: #6ee7b7;
    padding: 1px 8px;
    border-radius: 8px;
    font-size: 0.75rem;
}}
.x-skill {{
    background: rgba(239,68,68,0.1);
    color: #fca5a5;
    padding: 1px 8px;
    border-radius: 8px;
    font-size: 0.75rem;
}}
.job-meta {{
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-top: 6px;
}}

/* Summary table */
.summary-table {{
    background: var(--card);
    border-radius: 16px;
    padding: 28px 32px;
    margin: 32px 0;
    border: 1px solid var(--border);
    overflow-x: auto;
}}
.summary-table h2 {{
    font-size: 1.2rem;
    margin-bottom: 16px;
    color: var(--cyan);
}}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}}
th {{
    text-align: left;
    padding: 10px 12px;
    border-bottom: 2px solid var(--border);
    color: var(--text-dim);
    font-weight: 600;
    font-size: 0.82rem;
}}
td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}}

/* Footer */
.footer {{
    text-align: center;
    padding: 32px 0;
    color: var(--text-dim);
    font-size: 0.82rem;
}}

/* Print */
@media print {{
    body {{ background: #fff; color: #1e293b; }}
    .path-card, .profile-section, .summary-table {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }}
    .job-card {{ background: #fff; border-color: #e2e8f0; }}
}}

/* Responsive */
@media (max-width: 768px) {{
    .path-header {{ flex-direction: column; text-align: center; }}
    .path-stats {{ grid-template-columns: 1fr 1fr; }}
    .job-header {{ flex-direction: column; gap: 8px; align-items: flex-start; }}
    .profile-grid {{ grid-template-columns: 1fr 1fr; }}
}}
</style>
</head>
<body>
<div class="container">

<!-- Hero -->
<div class="hero">
    <h1>Job Radar 职业路径推荐报告</h1>
    <div class="subtitle">基于简历 AI 分析 + {total_jobs} 个杭州岗位市场数据</div>
    <div class="meta">生成时间: {now} | 数据来源: BOSS直聘</div>
</div>

<!-- Profile -->
<div class="profile-section">
    <h2>简历画像</h2>
    <div class="profile-grid">
        <div class="profile-item">
            <div class="label">工作年限</div>
            <div class="value">{resume['experience_years']} 年</div>
        </div>
        <div class="profile-item">
            <div class="label">最高学历</div>
            <div class="value">{resume['education']}</div>
        </div>
        <div class="profile-item">
            <div class="label">工作经历</div>
            <div class="value">{', '.join(resume['work_history'])}</div>
        </div>
        <div class="profile-item">
            <div class="label">技能数量</div>
            <div class="value">{len(resume['skills'])} 项</div>
        </div>
    </div>
    <div class="skills-wrap">{skill_tags}</div>
    <div style="margin-top:16px">
        <div class="label" style="color:var(--text-dim);font-size:0.82rem;
        margin-bottom:8px">核心亮点</div>
        {highlights_html}
    </div>
</div>

<!-- Path Cards -->
{path_cards_html}

<!-- Summary Table -->
<div class="summary-table">
    <h2>路径总览对比</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>职业方向</th>
                <th>相关岗位</th>
                <th>薪资中位数</th>
                <th>预估薪资</th>
                <th>核心差距</th>
            </tr>
        </thead>
        <tbody>
"""

    for i, path in enumerate(paths):
        salary = path["market_salary"]
        salary_display = (
            f"{salary['median']:,}元" if salary.get("median") else "—"
        )
        gap_skills = "、".join(
            s.split("（")[0][:8] for s in (path.get("required_skills") or [])[:3]
        )
        html += f"""
            <tr>
                <td>{i + 1}</td>
                <td><strong>{path['title']}</strong></td>
                <td>{path['related_jobs']}</td>
                <td>{salary_display}</td>
                <td>{path.get('salary_range') or '—'}</td>
                <td style="color:var(--yellow)">{gap_skills}</td>
            </tr>
"""

    html += """
        </tbody>
    </table>
</div>

<div class="footer">
    Job Radar — 岗位雷达，不是搜索工具，是决策工具 | 数据仅供参考
</div>

</div>
</body>
</html>
"""

    # 保存
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "career_report.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path.resolve())
