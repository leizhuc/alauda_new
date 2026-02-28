import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Jira Insight Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    
    st.subheader("Jira 连接配置")
    jira_server = st.text_input("Jira 服务器地址", value=os.getenv("JIRA_SERVER", ""), placeholder="https://jira.your-company.com")
    jira_username = st.text_input("Jira 用户名/邮箱", value=os.getenv("JIRA_USERNAME", ""), placeholder="yourname@company.com")
    jira_api_token = st.text_input("Jira Token 或密码", value=os.getenv("JIRA_API_TOKEN", ""), type="password", help="使用个人访问令牌 (PAT) 或密码")

    st.subheader("大模型配置")
    llm_provider = st.selectbox("选择模型提供商", options=["Google Gemini", "Groq", "DeepSeek", "Ollama (本地)"], index=0)
    
    # 动态显示模型选择和 API Key 输入框
    if llm_provider == "Google Gemini":
        llm_model = st.selectbox("选择模型", ["gemini-2.5-flash", "gemini-3.1-pro-preview"])
        api_key = st.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    elif llm_provider == "Groq":
        llm_model = st.selectbox("选择模型", ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"])
        api_key = st.text_input("Groq API Key", value=os.getenv("GROQ_API_KEY", ""), type="password")
    elif llm_provider == "DeepSeek":
        llm_model = st.selectbox("选择模型", ["deepseek-chat", "deepseek-reasoner"])
        api_key = st.text_input("DeepSeek API Key", value=os.getenv("DEEPSEEK_API_KEY", ""), type="password")
    elif llm_provider == "Ollama (本地)":
        llm_model = st.text_input("本地模型名称 (如 qwen2.5:7b)", value="qwen2.5:7b")
        api_key = "ollama" # Ollama generally doesn't require API key, but litellm might need a placeholder
        st.info("💡 请确保已在本地运行 Ollama 服务: `ollama run qwen2.5:7b`")

    st.subheader("查询配置 (JQL)")
    default_jql = "project = 'YOUR_PROJECT' AND status changed to Resolved during (-24h, now())"
    jql_query = st.text_area("自定义 JQL", value=default_jql, height=100, help="定义要拉取哪些已完成的工单进行分析")

    st.markdown("---")
    st.markdown("🔒 您的配置仅在本地运行，不会上传到任何外部服务器。")

# --- Main Content Area ---
st.title("Jira Insight Bot 🤖")
st.markdown("### 帮助产品经理从繁杂的工单中提炼高价值的产品改进建议。")

st.markdown("---")

# 预留用于展示状态和结果的区域
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="今日需关注工单", value="--")
with col2:
    st.metric(label="总分析工单数", value="--")
with col3:
    st.metric(label="当前使用模型", value=llm_model)

st.markdown("---")

# 分析触发按钮
if st.button("🚀 开始分析今日工单", use_container_width=True, type="primary"):
    if not jira_server or not jira_username or not jira_api_token:
        st.error("❌ 请先在侧边栏完善 Jira 认证信息！")
    elif llm_provider != "Ollama (本地)" and not api_key:
        st.error(f"❌ 请在侧边栏配置 {llm_provider} 的 API Key！")
    else:
        with st.spinner("🔄 正在连接 Jira 拉取工单数据..."):
            # 这里后续会调用 core/jira_client.py 
            st.info(f"Mock: 执行 JQL -> `{jql_query}`")
            st.success("成功连接 Jira 并拉取到 15 条已解决工单 (演示数据)。")
            
        with st.spinner(f"🧠 {llm_model} 正在深度分析工单评论..."):
            # 这里后续会调用 core/llm_analyzer.py
            import time
            time.sleep(2) # 模拟 AI 处理时间
            st.success("✅ AI 分析完成！")
            
        # 预留结果展示表格
        st.subheader("🔥 需要产品经理关注的改进点")
        st.markdown(
            """
            * **[PROJ-102] 容器网络配置导致偶发断流** 
              * **AI 根因分析:** 用户在使用自定义 CNI 插件时，文档说明不清晰，导致配置遗漏。
              * **💡 产品建议:** 在网络配置 UI 增加对于自定义 CNI 的强提示，并在文档中补充具体示例。
            * **[PROJ-145] 存储卷扩容操作失败**
              * **AI 根因分析:** 底层存储类 (StorageClass) 不支持在线扩容，但界面上未禁用该按钮，导致用户误操作。
              * **💡 产品建议:** 前端调用 API 校验 StorageClass 的 `allowVolumeExpansion` 属性，如果不为 true，直接将扩容按钮置灰并提示原因。
            """
        )

