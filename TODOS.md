# TODOS — Job Detect

## 构建原则

**优先复用既有 GitHub 项目模块，不要从零实现。** 实施每个模块前，先搜索 PyPI / GitHub 上是否有成熟可用的库。只有找不到合适依赖时才自行编写。已知的复用目标：
- **boss-cli** (github.com/jackwener/boss-cli) — 数据采集层，只消费其 JSON 导出
- **Pydantic** — 数据模型 + 字段校验 + camelCase alias
- **Typer** — CLI 框架
- **Rich** — 终端美化输出
- **PyYAML** — 配置文件解析
- **Chinese calendar / number parsing** 等中文字符串解析场景优先找现有库
- 任何涉及"薪资字符串解析"、"经验字符串解析"等场景，先搜 GitHub 再决定是否自写

## AI 模型配置

- **模型:** 智谱 GLM-4.7-flash
- **推理模式:** 暂时关闭（reasoning/thinking off）
- **API Key:** 从环境变量 `ZHIPU_API_KEY` 读取，不要硬编码
- **用途:** Phase 2 语义匹配 + 可解释推荐。MVP 阶段预留接口但不调用

## BOSS 直聘数据采集配置

- **Cookie:** 预留配置项，用户手动填入 BOSS 直聘账号 cookie
- **配置方式:** 在 `profile.yaml` 或独立 `config.yaml` 中预留 `boss_cookie` 字段，值为空字符串，注释说明填写方法
- **数据采集:** MVP 阶段通过 boss-cli 手动导出 JSON，cookie 配置为后续自动化采集做准备

## P1 (MVP-blocking)

### CLI Unified Error Handler
- **What:** Add a Typer exception handler that catches FileNotFoundError, JSONDecodeError, YAMLError, pydantic.ValidationError and converts them to friendly Chinese error messages with actionable advice.
- **Why:** 4 CRITICAL GAPS where file parsing errors produce raw Python tracebacks. Users abandon tools after the first traceback.
- **Where:** `src/cli/main.py`
- **Effort:** S (human: ~2h / CC: ~10min)

### Experience String Parser
- **What:** Add `parse_experience()` to core/ that handles: "3-5年" → (3, 5), "经验不限" → (0, 999), "5年以上" → (5, 999), "应届生" → (0, 0), "1年以下" → (0, 1). Unknown formats return None (trigger weight redistribution).
- **Why:** Without it, experience_match (30% of score) fails on non-standard strings.
- **Where:** `src/core/experience_parser.py` (new file)
- **Effort:** S (human: ~2h / CC: ~10min)

### `job-detect init` Command
- **What:** Interactive CLI command that asks 5 questions (skills, experience, cities, salary range, target roles) and generates `profile.yaml`.
- **Why:** Outside voice flagged: YAML profile is a massive onboarding barrier. An init command makes the tool usable in 60 seconds.
- **Where:** `src/cli/main.py` (new Typer command)
- **Effort:** S (human: ~3h / CC: ~15min)

### Sample Boss-CLI JSON Fixture
- **What:** Create `data/samples/sample_jobs.json` with 10-20 realistic Chinese job listings matching boss-cli export format.
- **Why:** Can't develop a data pipeline without representative input data. Essential for testing and development.
- **Where:** `data/samples/sample_jobs.json`
- **Effort:** S (human: ~1h / CC: ~5min)

### Configurable Scoring Weights
- **What:** Add `scoring` section to profile.yaml: `{skill: 0.4, experience: 0.3, salary: 0.3}`. Default is 40/30/30. Read from profile and pass to scorer constructor.
- **Why:** Outside voice flagged: hardcoded weights have no justification. Different users value different signals.
- **Where:** `src/data/profile.py`, `src/core/scorer.py`
- **Effort:** S (human: ~2h / CC: ~10min)

### Score Normalization for Missing Signals
- **What:** When salary/experience parser returns None, redistribute that signal's weight proportionally to remaining signals. Normalize total to 0-100 regardless.
- **Why:** Outside voice flagged: scores become incomparable when some jobs scored on 3 signals and others on 2.
- **Where:** `src/core/scorer.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Pydantic Field Alias for boss-cli camelCase
- **What:** Configure Job model with `model_config = ConfigDict(populate_by_name=True)` and add `Field(alias="jobName")` style aliases for all fields. Ensure boss-cli JSON loads without manual key renaming.
- **Why:** Eng review: boss-cli exports camelCase, Pydantic model uses snake_case. Without alias config, field mapping fails at runtime.
- **Where:** `src/data/models.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### UserProfile Salary as Numeric
- **What:** Change `salary_min`/`salary_max` from `str` to `int` (monthly CNY). Parse "15K" → 15000 at profile load time in `profile.py`, reusing `salary_parser` logic.
- **Why:** Eng review: string salary fields require double parsing. Numeric types catch errors at config load, not at scoring time.
- **Where:** `src/data/models.py`, `src/data/profile.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### MatchResult Optional Signal Types
- **What:** Change `salary_fit` and `experience_match` in MatchResult from `float` to `float | None`. Update scorer to handle None in weight redistribution logic.
- **Why:** Eng review: type system should enforce handling of missing signals, not silently default to 0.
- **Where:** `src/core/scorer.py`
- **Effort:** XS (human: ~30min / CC: ~3min)

### Skill Alias Lookup Optimization
- **What:** Build flattened lookup dict from skill_aliases.yaml at module load time: `{"python3": "python", "python 3": "python", ...}`. O(1) per lookup instead of O(n) list traversal.
- **Why:** Eng review: nested list traversal for every skill normalization call is wasteful even for MVP.
- **Where:** `src/core/normalizer.py`
- **Effort:** XS (human: ~30min / CC: ~3min)

### Resource File Path via importlib.resources
- **What:** Use `importlib.resources` to locate `skill_aliases.yaml` so it works both in development and after `pip install`.
- **Why:** Eng review: hardcoded relative paths break after packaging. Standard Python pattern for bundled data files.
- **Where:** `src/core/normalizer.py`
- **Effort:** XS (human: ~30min / CC: ~3min)

### Test Suite — salary_parser
- **What:** Unit tests covering: "20-30K", "20-30K·14薪", "15-25K·16薪", "10-15K", "面议" → None, "200-300元/天" → None, empty string → None, None input → None.
- **Why:** Eng review: string parsing is highest bug density code. 6+ formats need explicit test coverage.
- **Where:** `tests/core/test_salary_parser.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Test Suite — experience_parser
- **What:** Unit tests covering: "3-5年", "1-3年", "经验不限", "5年以上", "应届生", "1年以下", unknown format → None, None input → None.
- **Why:** Eng review: mirrors salary_parser in risk profile. Must test all documented formats.
- **Where:** `tests/core/test_experience_parser.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Test Suite — normalizer
- **What:** Unit tests covering: exact alias match, case-insensitive match, unknown skill passthrough, empty list, multi-alias canonical resolution.
- **Why:** Eng review: skill normalization affects all matching scores. Wrong normalization silently degrades results.
- **Where:** `tests/core/test_normalizer.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Test Suite — scorer
- **What:** Unit tests covering: 3-signal full score, salary None → weight redistribution, experience None → weight redistribution, all None → fallback, custom weights from profile.
- **Why:** Eng review: scoring is the core value prop. Must prove weight redistribution and normalization work correctly.
- **Where:** `tests/core/test_scorer.py`
- **Effort:** S (human: ~2h / CC: ~10min)

### Test Suite — loader
- **What:** Integration test: load sample_jobs.json → list of Job models. Verify field alias mapping works. Test malformed JSON error.
- **Why:** Eng review: validates end-to-end data pipeline from file to model.
- **Where:** `tests/data/test_loader.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Test Suite — profile
- **What:** Unit tests: load valid YAML, missing optional fields get defaults, salary string parsing to int, invalid YAML error.
- **Why:** Eng review: profile loading is the user's first interaction. Bad UX here = tool abandoned.
- **Where:** `tests/data/test_profile.py`
- **Effort:** S (human: ~1h / CC: ~5min)

### Test Suite — conftest shared fixtures
- **What:** Create `tests/conftest.py` with shared fixtures: sample Job, sample UserProfile, sample profile YAML content.
- **Why:** Eng review: DRY test setup. All test files share the same sample data.
- **Where:** `tests/conftest.py`
- **Effort:** XS (human: ~30min / CC: ~3min)

## P2 (Day-1 improvement)

### Multi-file / Directory Data Loading
- **What:** Extend `--data` to accept a directory path or glob pattern, auto-merge all JSON files.
- **Why:** Real usage needs multiple boss-cli exports. Manual `jq -s 'add'` is friction.
- **Where:** `src/data/loader.py`
- **Effort:** S (human: ~3h / CC: ~15min)

### Data Flow Diagram in Design Doc
- **What:** Add Mermaid flowchart to design doc showing: Job JSON → Loader → Models → Normalizer → Scorer → Matcher → Recommender → CLI Output.
- **Why:** Eng review: missing data flow visualization makes it harder for future contributors (or Phase 2 upgrades) to understand the system.
- **Where:** Design doc
- **Effort:** XS (human: ~30min / CC: ~3min)

## Phase 2 (after MVP validation)

### Learning Path Recommendation
- Skill ROI calculation (frequency * projected_score_delta) + gap report enhancement
- Trigger: Phase 1 skill gap report validated as useful

### Explainable Recommendations
- Template-based natural language explanations for top-1 recommendation
- Template: "你的技能匹配度为 {score}%，主要差距在 {missing_skills}..."
- Trigger: Phase 1 score output validated, user wants more context

### Time-series Market Trend
- Compare skills demand across multiple data snapshots
- Requires: >= 3 snapshots accumulated at `data/snapshots/YYYY-MM-DD.json`
- Trigger: User has accumulated historical exports

## Deferred (no timeline)

### Multi-platform Data Loader
- 拉勾, 猎聘 JSON/CSV support
- Blocked by: data format research

### Career Path Trajectory Mapping
- Role transition graph from job title co-occurrence
- Blocked by: needs larger dataset

### Resume Parser Integration
- PDF → structured profile via convert2markdown
- Blocked by: MVP validation
