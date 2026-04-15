# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
pytest                          # 运行全部测试（160 个用例）
pytest tests/core/test_scorer.py -x   # 运行单个测试文件
pytest -k "test_salary"         # 按名称匹配运行测试
python -m src.cli.main --help   # 运行 CLI（开发模式）
boss-login                      # BOSS直聘 CDP 登录（安装后）
boss-analyze                    # 完整分析（安装后）
```

AI 功能需要环境变量 `ZHIPU_API_KEY`。

## 架构

两条入口管线，共享核心评分引擎：

**管线 1: advisor（简历驱动）** — `src/cli/main.py:advisor`
```
PDF → pymupdf4llm → Markdown
  → Chain 1 (GLM-4-flash): 结构化提取 → ResumeExtract
  → Chain 2 (GLM-4-flash): 职业路径推荐 → CareerRecommendation
  → profile_builder: 每条路径 → 虚拟 UserProfile
  → Matcher + RuleBasedScorer: 三维度匹配打分
  → MarketAnalysis: 市场统计
  → CLI 输出 / HTML 报告
```

**管线 2: match/analyze（配置文件驱动）** — `src/cli/main.py:match`
```
YAML profile → UserProfile → Matcher + RuleBasedScorer → 排名输出
```

## 关键设计决策

**LLM 集成方式**: 智谱 GLM-4-flash 通过 langchain-openai ChatOpenAI 调用（OpenAI 兼容接口）。不支持 tool calling / structured output，因此使用 prompt 要求 JSON 输出 + `_extract_json_from_text()` 手动解析 + Pydantic 校验 + 3 次重试。

**Prompt 模板**: LangChain ChatPromptTemplate 中 JSON 示例的 `{}` 会被解释为模板变量，必须用 `{{` `}}` 转义。见 `src/ai/prompts.py`。

**评分权重重分配**: 当信号缺失时（如薪资"面议"），该信号权重按比例重分配到其他信号，总分计算始终基于 0-1 区间。见 `RuleBasedScorer._compute_total()`。

**技能归一化**: `src/config/skill_aliases.yaml` 定义别名映射，所有技能比较前经过 `normalize_skills()` 统一为标准名。

**数据格式兼容**: `load_jobs()` 支持 boss-cli envelope、flat list、纯数组、单对象四种 JSON 结构。

**Job 模型字段映射**: BOSS直聘导出为 camelCase（如 `jobName`），Pydantic 模型用 `Field(alias=...)` 映射，内部统一用 snake_case。

## 目录约定

- `src/` 源码，`tests/` 测试，二者目录结构保持一致
- `data/samples/` 测试用模拟数据（在 git 中），其他 data 目录已 gitignore（含简历、真实岗位数据等敏感信息）
- `scripts/fetch_jobs.py` BOSS直聘数据采集脚本，使用 `boss_cli.client.BossClient` 直接 API 调用
- `src/auth/playwright_login.py` BOSS直聘登录模块（CDP 自动提取 / 手动 Cookie 导入）
- `reports/` 生成的 HTML 报告（已 gitignore）
- `src/report/html_report.py` HTML 报告生成器，接收 dict 数据输出完整 HTML 文件
