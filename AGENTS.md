# Repository Guidelines

## Project Structure & Module Organization
`src/` 是主代码目录，按领域拆分为 `ai/`、`analysis/`、`cli/`、`core/`、`data/`、`report/`。CLI 入口在 `src/cli/main.py`。测试放在 `tests/`，目录结构尽量与 `src/` 对齐，例如 `src/core/scorer.py` 对应 `tests/core/test_scorer.py`。辅助脚本放在 `scripts/`，样例输入优先使用 `data/samples/`，生成的 HTML 报告输出到 `reports/`。

## Build, Test, and Development Commands
先安装开发依赖：

```bash
pip install -e ".[dev]"
```

常用命令：

```bash
pytest
pytest tests/core/test_scorer.py -x
ruff check src/ tests/
ruff format src/ tests/
python -m src.cli.main --help
```

`pytest` 运行全部测试；第二条命令用于快速定位单文件失败；`ruff` 负责检查与格式化；`python -m src.cli.main` 用于开发态调试 CLI。

## Coding Style & Naming Conventions
使用 Python 3.10+，缩进为 4 个空格，行宽遵循 Ruff 配置的 100。包导入使用绝对路径，不使用相对导入。模块、函数、文件名使用 `snake_case`，类名使用 `PascalCase`。新功能优先放入已有领域目录，避免在根目录堆积脚本或通用逻辑。

## Testing Guidelines
统一使用 `pytest`，测试文件命名为 `test_*.py`。新增功能时，优先覆盖评分规则、解析器、数据加载、CLI 分支和 AI 适配层的边界情况。提交前至少运行受影响目录的测试；修改核心匹配逻辑时，建议直接运行 `pytest` 全量验证。

## Commit & Pull Request Guidelines
当前历史以简洁前缀开头，如 `feat:`、`refactor:`。建议继续使用祈使式摘要，例如 `fix: handle empty salary range`。PR 说明应包含：变更目的、影响模块、测试命令与结果；如果修改 CLI 输出或 HTML 报告，附上示例输出或截图。

## Security & Configuration Tips
AI 能力依赖环境变量 `ZHIPU_API_KEY`。不要提交真实简历、抓取到的岗位原始数据或生成报告；演示和测试请优先使用 `data/samples/` 中的样例文件。
