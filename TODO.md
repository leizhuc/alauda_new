# Project TODOs (Vibe Coding)

## Backlog

### Phase 1: 基础设施与 UI 框架搭建
- [ ] 创建 `requirements.txt` (包含 streamlit, jira, litellm, pydantic, python-dotenv)。
- [ ] 创建 `app.py` 作为 Streamlit 主入口。
- [ ] 开发基础 UI 侧边栏：
  - [ ] Jira 认证信息配置 (URL, Token/Password)。
  - [ ] LLM 模型选择下拉框及 API Key 配置。
  - [ ] 自定义 JQL 输入框 (支持用户输入特定的 Project 或 Component 条件)。
- [ ] 确保敏感信息使用 `.env` 和 Streamlit secrets 机制安全管理。

### Phase 2: Jira 数据抓取模块 (`core/jira_client.py`)
- [ ] 实现连接 Jira 实例的鉴权逻辑。
- [ ] 实现接收前端传入的自定义 JQL 并执行查询的功能。
- [ ] 解析工单数据，提取核心字段 (Summary, Description, Comments)。
- [ ] 编写数据清洗逻辑，过滤系统自动生成的无用评论。

### Phase 3: AI 分析模块 (`core/llm_analyzer.py`)
- [ ] 设计核心 Prompt (赋予架构师/PM 视角，判断分类、提取根本原因及产品建议)。
- [ ] 集成 `litellm`，配置 `gemini-2.5-flash` 为默认主力模型。
- [ ] 实现 LLM 结构化输出解析 (要求返回 JSON 格式)。
- [ ] 增加模型切换逻辑 (支持切换到其他模型接口)。

### Phase 4: 整合与数据展示
- [ ] 将抓取的 Jira 数据传递给 LLM 模块进行批量分析。
- [ ] 在 Streamlit 主界面渲染分析结果 (卡片或表格形式展示需关注的工单)。
- [ ] 实现本地历史记录缓存机制。

## In Progress
- [ ] 确认最终架构设计与 TODO 清单。

## Done
- [x] Initialize Git Repository
- [x] Setup Vibe Coding foundational files
- [x] 确定项目核心方向为 Jira 工单智能分析 (方向一)
- [x] 确定核心技术栈 (Streamlit + LiteLLM + Python) 和主力模型 (gemini-2.5-flash)
- [x] 确认系统为纯本地运行 UI，不支持外部 CI/CD 触发
- [x] 确认 JQL 需要支持用户在 UI 端动态配置
- [x] 更新架构文档和 TODO 列表
