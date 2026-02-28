import os
import json
from typing import Dict, Any, List
from litellm import completion
from pydantic import BaseModel, Field

# --- 定义结构化输出 (Pydantic Model) ---
class IssueAnalysisResult(BaseModel):
    is_pm_attention_needed: bool = Field(..., description="是否需要产品经理关注并改进产品？(纯运维误操作、底层网络波动、明确的非产品缺陷请设为 False)")
    issue_type: str = Field(..., description="问题分类标签，例如：UX设计缺陷, 文档缺失, 新需求, 偶发Bug, 配置错误, 第三方依赖故障等")
    root_cause_summary: str = Field(..., description="用一句话总结导致这个工单的根本原因 (Root Cause)")
    product_improvement_suggestion: str = Field(..., description="如果需要PM关注，用一句话提炼出具体的产品改进建议。如果不需要关注，填 '无'。")

class LlmAnalyzer:
    def __init__(self):
        """
        初始化 AI 分析器。
        使用 litellm，可以在运行时动态传入 model 和 api_key。
        """
        # 核心系统 Prompt：赋予 AI 角色和任务背景
        self.system_prompt = """
        你是一位资深的容器云平台（如 Kubernetes, Alauda, OpenShift）产品经理兼架构师。
        你的任务是：阅读每天已解决的 Jira 工单（包括标题、描述和运维人员的排查评论），
        并从中敏锐地洞察出【能够推动产品迭代和优化的建议】。

        评判标准 (极度重要)：
        1. 纯粹的运维操作（如：重启了Pod、清理了磁盘空间、网络专线抖动、用户的证书过期）-> 不需要 PM 关注 (is_pm_attention_needed=False)。
        2. 纯粹的用户配置错误（但如果是因为 UI 提示极其容易引发误解，或者文档严重缺失导致的共性配置错误）-> 需要 PM 关注 (is_pm_attention_needed=True)，并提出改进 UI 或补充校验逻辑的建议。
        3. 代码 Bug / 交互设计不合理 / 确实缺少某个功能 -> 需要 PM 关注 (is_pm_attention_needed=True)。

        输出格式：
        请严格输出一个符合以下结构的 JSON 对象，不要包含任何 markdown 标记或其他多余的文字：
        {
            "is_pm_attention_needed": true或false,
            "issue_type": "问题分类标签，例如：UX设计缺陷, 文档缺失, 新需求, 偶发Bug, 配置错误, 第三方依赖故障等",
            "root_cause_summary": "用一句话总结导致这个工单的根本原因 (Root Cause)",
            "product_improvement_suggestion": "如果需要PM关注，用一句话提炼出具体的产品改进建议。如果不需要关注，填 '无'。"
        }
        """

    def analyze_issue(self, issue_data: Dict[str, str], model_provider: str, model_name: str, api_key: str) -> Dict[str, Any]:
        """
        调用 LLM 分析单条工单记录。
        
        Args:
            issue_data: 包含 summary, description, comments 等字段的工单字典
            model_provider: 'Google Gemini', 'Groq', 'DeepSeek', 'Ollama (本地)'
            model_name: 具体的模型名称，如 'gemini-2.5-flash'
            api_key: 对应提供商的 API Key
            
        Returns:
            解析后的结构化分析结果 (字典)
        """
        # 组装发送给 LLM 的工单内容
        user_prompt = f"""
        请分析以下已解决的工单：
        
        【工单标题】: {issue_data.get('summary', '无标题')}
        【工单描述】: {issue_data.get('description', '无描述')[:1000]} ... (已截断)
        
        【排查过程与解决评论 (核心)】: 
        {issue_data.get('comments', '无评论')}
        
        请按照预设的 JSON 格式输出分析结果。
        """

        # 根据提供商适配 litellm 需要的模型名称前缀
        litellm_model = self._format_model_name(model_provider, model_name)
        
        # 准备环境变量供 litellm 读取 API Key
        self._set_api_key_env(model_provider, api_key)

        try:
            # 使用 litellm 发起调用
            # 针对各种模型，去除强行要求 response_format={"type": "json_object"}
            # 因为部分模型（如 Groq 和 DeepSeek 某些版本）或者通过代理转发时，
            # 开启强制 json 模式容易导致请求中途截断、超时或流关闭。
            response = completion(
                model=litellm_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1, # 保持输出的稳定性和一致性
                max_tokens=800
            )

            # 解析返回的 JSON 字符串
            result_str = response.choices[0].message.content or "{}"
            # 清理可能存在的 markdown 代码块包裹 (以防模型不遵守 JSON 模式)
            result_str = result_str.strip()
            
            # 找到第一个 { 和 最后一个 } 之间的内容
            start_idx = result_str.find('{')
            end_idx = result_str.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                result_str = result_str[start_idx:end_idx+1]
            
            try:
                parsed_result = json.loads(result_str)
            except json.JSONDecodeError as je:
                print(f"JSON 解析失败! 原始模型返回内容为:\n{result_str}")
                raise je
            
            # 简单的校验：确保包含我们需要的字段，如果不包含则使用默认值补充
            return {
                "is_pm_attention_needed": parsed_result.get("is_pm_attention_needed", False),
                "issue_type": parsed_result.get("issue_type", "未知类型"),
                "root_cause_summary": parsed_result.get("root_cause_summary", "解析失败或未提供"),
                "product_improvement_suggestion": parsed_result.get("product_improvement_suggestion", "无")
            }

        except Exception as e:
            print(f"\nLLM Analysis Error for issue {issue_data.get('key')}: {e}")
            # Instead of returning error json, returning a graceful fallback dict
            return {
                "is_pm_attention_needed": False,
                "issue_type": "分析失败/模型生成截断",
                "root_cause_summary": f"分析失败，可能是模型输出不完整或遇到非法字符导致 JSON 截断。",
                "product_improvement_suggestion": "无"
            }

    def _format_model_name(self, provider: str, raw_model_name: str) -> str:
        """为 litellm 格式化模型名称"""
        if provider == "Google Gemini":
            return f"gemini/{raw_model_name}"
        elif provider == "Groq":
            return f"groq/{raw_model_name}"
        elif provider == "DeepSeek":
            # DeepSeek 可以通过 openrouter 或 openai 兼容接口调用
            return f"deepseek/{raw_model_name}" 
        elif provider == "Ollama (本地)":
            return f"ollama/{raw_model_name}"
        return raw_model_name

    def _set_api_key_env(self, provider: str, api_key: str):
        """将前端传入的 API Key 临时设置为环境变量，供 litellm 读取"""
        if provider == "Google Gemini":
            os.environ["GEMINI_API_KEY"] = api_key
        elif provider == "Groq":
            os.environ["GROQ_API_KEY"] = api_key
        elif provider == "DeepSeek":
            os.environ["DEEPSEEK_API_KEY"] = api_key
        # Ollama 通常不需要 API key

# --- 测试代码 ---
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    analyzer = LlmAnalyzer()
    
    # 构建一条 Mock 数据
    mock_issue = {
        "key": "AIT-999",
        "summary": "用户创建 DCS 集群失败",
        "description": "客户在界面上点击创建集群，但一直卡在 pending 状态，没有明确报错信息。",
        "comments": "[开发者A] 查了后台日志，发现是因为用户填写的 VPC ID 在该 Region 下不存在，底层 API 报了 404，但是前端没捕获导致假死。\n[测试人员B] 好的，那前端应该增加对 VPC ID 格式和存在性的前置校验。"
    }
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("未找到 GEMINI_API_KEY，跳过测试")
    else:
        print(f"正在测试分析工单: {mock_issue['summary']} ...")
        # 测试 Gemini 模型
        result = analyzer.analyze_issue(
            issue_data=mock_issue,
            model_provider="Google Gemini",
            model_name="gemini-2.5-flash", # 回退到 2.5-flash 防止 3.1 免费额度不足
            api_key=api_key
        )
        print("\n分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
