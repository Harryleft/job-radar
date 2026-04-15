"""LangChain Prompt 模板 — Chain 1 结构化提取 + Chain 2 职业路径推荐"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

# ─── Chain 1: 简历结构化提取 ───

EXTRACT_SYSTEM = (
    "你是一个专业的简历分析专家。你的任务是从简历文本中提取结构化信息，以 JSON 格式输出。\n"
    "你必须且只能返回一个 JSON 对象，不要包含任何其他文字说明。\n"
    "JSON 格式如下：\n"
    "{{\n"
    '  "skills": ["技能1", "技能2"],\n'
    '  "experience_years": 工作年限整数,\n'
    '  "education": "学历信息",\n'
    '  "work_history": ["公司A 职位A"],\n'
    '  "highlights": ["成就1", "成就2"]\n'
    "}}\n\n"
    "提取规则：\n"
    '1. skills: 所有技术技能和软技能，用标准名称（如 "Python" 而非 "python3"）\n'
    "2. experience_years: 根据工作经历推算总年限（取整）\n"
    "3. education: 最高学历\n"
    '4. work_history: 工作经历列表，格式 "公司名 职位"\n'
    "5. highlights: 关键成就或项目，最多 5 条"
)

EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", EXTRACT_SYSTEM),
        ("human", "以下是简历内容：\n\n{resume_markdown}"),
    ]
)

# ─── Chain 2: 职业路径推荐 ───

RECOMMEND_SYSTEM = (
    "你是一个职业规划顾问。根据候选人的技能和背景，推荐最适合的职业路径。\n"
    "你必须且只能返回一个 JSON 对象，不要包含任何其他文字说明。\n"
    "JSON 格式如下：\n"
    "{{\n"
    '  "paths": [\n'
    "    {{\n"
    '      "title": "岗位名称",\n'
    '      "match_reason": "匹配理由",\n'
    '      "required_skills": ["额外需要的技能"],\n'
    '      "salary_range": "15-30K 或 null"\n'
    "    }}\n"
    "  ]\n"
    "}}\n\n"
    "要求：\n"
    '1. 每条路径必须是具体、可搜索的岗位名称（如"数据分析师"，而非"数据分析方向"）\n'
    "2. match_reason 基于候选人实际技能和经历说明匹配原因\n"
    "3. required_skills 是这个路径额外需要但候选人可能不具备的技能\n"
    "4. salary_range: 无法推断时设为 null，不要编造\n"
    "5. 路径之间要有差异化"
)

RECOMMEND_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RECOMMEND_SYSTEM),
        ("human", "候选人信息：\n{extract_json}\n\n请推荐 {num_paths} 条职业路径。"),
    ]
)

# ─── Chain 1b: 自由文本背景提取 ───

BACKGROUND_EXTRACT_SYSTEM = (
    "你是一个专业的职业背景分析师。"
    "你的任务是从用户自由描述的个人背景中提取结构化信息，以 JSON 格式输出。\n"
    "你必须且只能返回一个 JSON 对象，不要包含任何其他文字说明。\n"
    "JSON 格式如下：\n"
    "{{\n"
    '  "skills": ["技能1", "技能2"],\n'
    '  "experience_years": 工作年限整数,\n'
    '  "education": "学历信息",\n'
    '  "work_history": ["公司A 职位A"],\n'
    '  "highlights": ["成就1", "成就2"],\n'
    '  "location_preferences": ["城市-原因"],\n'
    '  "life_context": "生活背景概述",\n'
    '  "career_goals": "职业目标"\n'
    "}}\n\n"
    "提取规则：\n"
    '1. skills: 从叙述中推断所有技术技能和软技能，用标准名称\n'
    "2. experience_years: 根据描述推算总工作年限（取整），无法推断时填 0\n"
    "3. education: 最高学历，未提及时填空字符串\n"
    '4. work_history: 工作经历列表，格式 "公司名 职位"，未提及则为空数组\n'
    "5. highlights: 关键成就、项目或荣誉，最多 5 条\n"
    '6. location_preferences: 候选人提到的城市偏好，格式 "城市-原因"，如 "杭州-互联网机会多"\n'
    "7. life_context: 家庭状况、生活约束、个人情况等背景信息\n"
    "8. career_goals: 职业目标和期望\n\n"
    "注意：用户可能用口语化、非结构化方式描述，你需要从中推断出结构化信息。"
    "没有提到的字段使用默认值（空字符串或空数组）。"
)

BACKGROUND_EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", BACKGROUND_EXTRACT_SYSTEM),
        ("human", "以下是个人背景描述：\n\n{background_text}"),
    ]
)
