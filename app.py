import os
import streamlit as st
from dotenv import load_dotenv

# 引入我们刚才写好的两个核心模块
from core.jira_client import JiraFetcher
from core.llm_analyzer import LlmAnalyzer

# Load environment variables from .env file (if present)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="Jira Insight Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化 Session State，用于存储抓取和分析的结果，避免页面刷新丢失数据
if "jira_issues" not in st.session_state:
    st.session_state.jira_issues = []
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []
if "is_analyzing" not in st.session_state:
    st.session_state.is_analyzing = False

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
    else: # Ollama 
        llm_model = st.text_input("本地模型名称 (如 qwen2.5:7b)", value="qwen2.5:7b")
        api_key = "ollama" # Ollama generally doesn't require API key, but litellm might need a placeholder
        st.info("💡 请确保已在本地运行 Ollama 服务: `ollama run qwen2.5:7b`")

    st.subheader("查询配置 (JQL)")
    default_jql = "project = 'AIT' ORDER BY updated DESC" # 使用你刚才测试成功的简单查询
    jql_query = st.text_area("自定义 JQL", value=default_jql, height=100, help="定义要拉取哪些已完成的工单进行分析")
    
    # 获取拉取数量上限
    max_results = st.number_input("单次拉取最大工单数", min_value=1, max_value=50, value=5)

    st.markdown("---")
    st.markdown("🔒 您的配置仅在本地运行，不会上传到任何外部服务器。")

# --- Main Content Area ---
st.title("Jira Insight Bot 🤖")
st.markdown("### 帮助产品经理从繁杂的工单中提炼高价值的产品改进建议。")

st.markdown("---")

# 计算当前统计数据
total_analyzed = len(st.session_state.analysis_results)
need_attention = sum(1 for res in st.session_state.analysis_results if res.get('is_pm_attention_needed', False))

# 预留用于展示状态和结果的区域
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="高优改进建议 (需PM关注)", value=f"{need_attention} 项")
with col2:
    st.metric(label="已分析工单数", value=f"{total_analyzed} 条")
with col3:
    st.metric(label="当前使用模型", value=llm_model)

st.markdown("---")

# 分析触发按钮
if st.button("🚀 开始拉取工单并分析", use_container_width=True, type="primary", disabled=st.session_state.is_analyzing):
    if not jira_server or not jira_username or not jira_api_token:
        st.error("❌ 请先在侧边栏完善 Jira 认证信息！")
    elif llm_provider != "Ollama (本地)" and not api_key:
        st.error(f"❌ 请在侧边栏配置 {llm_provider} 的 API Key！")
    else:
        st.session_state.is_analyzing = True
        
        try:
            # 1. 抓取 Jira 数据
            with st.spinner(f"🔄 正在连接 {jira_server} 拉取数据..."):
                fetcher = JiraFetcher(jira_server, jira_username, jira_api_token)
                issues = fetcher.fetch_resolved_issues(jql_query, max_results=max_results)
                
                if not issues:
                    st.warning("⚠️ 没有找到符合该 JQL 条件的工单数据，请尝试修改查询语句。")
                    st.session_state.is_analyzing = False
                    st.stop()
                    
                st.session_state.jira_issues = issues
                st.success(f"成功获取到 {len(issues)} 条工单数据！")
            
            # 2. 调用 LLM 分析
            st.session_state.analysis_results = []
            analyzer = LlmAnalyzer()
            
            # 使用进度条显示分析进度
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, issue in enumerate(issues):
                status_text.text(f"🧠 {llm_model} 正在分析工单 {issue['key']} ({idx+1}/{len(issues)})...")
                
                result = analyzer.analyze_issue(
                    issue_data=issue,
                    model_provider=llm_provider,
                    model_name=llm_model,
                    api_key=api_key
                )
                
                # 将原始工单信息合并进结果中方便展示
                result['issue_key'] = issue['key']
                result['issue_url'] = issue['url']
                result['issue_summary'] = issue['summary']
                
                st.session_state.analysis_results.append(result)
                
                # 更新进度条
                progress = (idx + 1) / len(issues)
                progress_bar.progress(progress)
                
            status_text.text("✅ AI 分析全部完成！")
            
        except Exception as e:
            st.error(f"🚨 分析过程中发生错误: {e}")
            
        finally:
            st.session_state.is_analyzing = False
            st.rerun() # 重新渲染页面以显示结果

# --- 展示分析结果 ---
if st.session_state.analysis_results:
    st.subheader("🔥 产品优化洞察看板")
    
    # 将需要关注的和不需要关注的拆分展示
    attention_issues = [res for res in st.session_state.analysis_results if res.get('is_pm_attention_needed', False)]
    other_issues = [res for res in st.session_state.analysis_results if not res.get('is_pm_attention_needed', False)]
    
    tab1, tab2 = st.tabs([f"🚨 需改进建议 ({len(attention_issues)})", f"✅ 常规工单 ({len(other_issues)})"])
    
    with tab1:
        if not attention_issues:
            st.info("太棒了，本次分析的工单中没有发现明显的共性产品问题或设计缺陷。🎉")
        else:
            for item in attention_issues:
                with st.expander(f"[{item['issue_key']}] {item['issue_summary']} - 标签: {item['issue_type']}", expanded=True):
                    st.markdown(f"**🔗 Jira 链接:** [{item['issue_key']}]({item['issue_url']})")
                    st.markdown(f"**🔍 根因分析:** {item['root_cause_summary']}")
                    st.markdown(f"**💡 产品建议:** `{item['product_improvement_suggestion']}`")
                    
    with tab2:
        if not other_issues:
            st.info("所有工单均被标记为需要产品关注。")
        else:
            for item in other_issues:
                with st.expander(f"[{item['issue_key']}] {item['issue_summary']}"):
                    st.markdown(f"**🔍 根因概括:** {item['root_cause_summary']}")
                    st.markdown("*AI 判定结论: 偏向常规研发/运维操作，暂无需特殊跟进。*")

