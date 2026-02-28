# Jira Insight Bot 🤖

**Jira Insight Bot** 是一个基于大模型驱动的敏捷研发辅助工具，专为产品经理（PM）和系统架构师设计。它能够自动抓取 Jira 中每天流转、解决的工单，并利用 AI 的深度阅读理解能力，从海量的研发讨论、报错日志和排查评论中，**自动提炼出对产品迭代有高价值的改进建议**。

👉 **项目 Git 地址**: [https://github.com/your-org/jira-insight-bot](https://github.com/your-org/jira-insight-bot) *(请替换为您的实际远程仓库地址)*

---

## 🎯 解决的问题 (The Problem)

在大型云原生或企业级软件产品中，每天会产生大量的 Jira 工单（包括客户支持、缺陷报告、内部排查等）。产品经理通常面临以下痛点：
1. **信息噪音极大**：80% 的工单可能只是纯粹的运维操作（如重启 Pod、清理磁盘）、客户网络抖动、或者纯粹的个人配置失误。
2. **错失优化良机**：在剩下的 20% 工单中，隐藏着真正的产品缺陷（如：报错提示极其容易误导用户、默认参数设计不合理、某个表单缺少前置校验导致系统假死）。
3. **精力分散**：PM 无法每天逐行阅读研发人员长篇大论的代码级讨论和报错堆栈。

**本工具完美解决了这一问题**：它扮演了一位极其敏锐的“资深架构师”，自动滤除基础设施波动引发的噪音，一针见血地指出哪些问题需要落实到具体的 UI 交互改进或功能迭代上。

---

## ✨ 核心亮点 (Key Features)

- 🧠 **内置 PM/架构师人格**：精心调优的 Prompt 能够准确区分“纯环境故障”与“产品交互缺陷”。
- 🔄 **全网大模型无缝切换**：基于 `litellm` 底层，一键支持 OpenAI (ChatGPT)、Zhipu AI (智谱 GLM-4全系)、Google Gemini、DeepSeek、Groq 以及本地部署的 Ollama，丰俭由人。
- 🛡️ **极致的鲁棒性 (Robustness)**：
  - **智能 JSON 提取**：无视部分大模型（尤其是具备深度推理 Reasoning 能力的国产模型）喜欢在输出前后附加无关闲聊或 Markdown 标记的毛病，强力截取合法 JSON。
  - **优雅降级**：当遇到不可抗力的网络断流或模型输出截断时，单条工单会优雅 fallback，绝不会导致整个分析任务崩溃断头。
  - **动态清洗**：抓取 Jira 数据时，自动过滤短评（如 "ok"）和机器人工单（Gitlab/Jenkins 自动回复），大幅节省 Token 消耗。
- 🌐 **极其友好的网络适配**：UI 层直接暴露代理配置和自定义 API Base URL（完美支持国内中转 API 以及突破企业内网限制，实现了精准的“访问 Jira 不走代理，访问国外 LLM 走代理”的分流路由）。
- 🔒 **数据隐私优先**：采用 Streamlit 纯本地化运行架构，无需上传凭据至任何云端，极度适合具有保密要求的企业内部网络。

---

## 🛠️ 技术栈 (Tech Stack)

- **前端/交互**: [Streamlit](https://streamlit.io/) (纯 Python 构建的现代数据应用框架)
- **大模型网关**: [LiteLLM](https://github.com/BerriAI/litellm) (统一不同 LLM 厂商的 API 调用标准)
- **工单集成**: `jira` (官方 Jira Python SDK，兼容 Server/Data Center 和 Cloud 版)
- **数据结构约束**: `Pydantic` & 原生 `json` 解析
- **环境要求**: Python 3.9+

---

## 🚀 使用方法 (How to Use)

### 1. 环境准备
克隆本项目到本地后，建议创建一个 Python 虚拟环境并激活：
```bash
git clone <your-repo-url>
cd alauda_new
python3 -m venv venv
source venv/bin/activate  # Windows 用户请使用 venv\Scripts\activate
```

### 2. 安装依赖
```bash
# 由于 urllib3 版本与 Mac 自带 LibreSSL 的兼容问题，此项目已锁定安全的 1.x 版本
pip install -r requirements.txt
```

### 3. 配置凭据 (可选但推荐)
您可以将根目录下的 `.env.example` 复制一份重命名为 `.env`，并在其中填入默认的 Jira 凭据和各种大模型 API Key。
*注：即使不填，您也可以在启动后的网页侧边栏中随时手动输入并覆盖。*
```bash
cp .env.example .env
```

### 4. 启动应用
```bash
streamlit run app.py
```
运行后，浏览器将自动打开 `http://localhost:8501`。

### 5. 开始智能分析
1. 在左侧边栏确认您的 **Jira 认证信息** (支持内网地址及账号密码/Token)。
2. 选择您心仪的 **大模型提供商** (如选用 OpenAI 或智谱并填入相应的 Key)。
3. *(可选)* 如果您的网络无法直连外部接口，在**网络配置**栏填入本地翻墙代理（如 `http://127.0.0.1:7890`）。
4. 在 **查询配置** 中输入符合您业务诉求的 JQL (例如：`project = 'AIT' ORDER BY updated DESC`)。
5. 点击主界面的 **“🚀 开始拉取工单并分析”**。
6. 喝杯咖啡，查看大模型在右侧生成的 **“🔥 产品优化洞察看板”**！

---
*Built with ❤️ via Vibe Coding*