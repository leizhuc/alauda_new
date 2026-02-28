import re
from typing import List, Dict, Optional
from jira import JIRA
from jira.exceptions import JIRAError

class JiraFetcher:
    def __init__(self, server: str, username: str, api_token: str):
        """
        初始化 Jira 客户端连接。
        
        Args:
            server: Jira 服务器地址 (例如: 'https://jira.your-company.com')
            username: Jira 用户名或邮箱
            api_token: Jira API Token (Cloud) 或 密码 (Server/Data Center)
        """
        self.server = server
        self.username = username
        self.api_token = api_token
        self.client = self._connect()

    def _connect(self) -> Optional[JIRA]:
        """建立 Jira 连接并返回客户端实例"""
        try:
            # 兼容 Cloud 版的 basic_auth 和部分 Server 版的鉴权
            import os
            import urllib.parse
            
            # 解析 Jira 域名
            parsed_url = urllib.parse.urlparse(self.server)
            jira_host = parsed_url.hostname or "jira.alauda.cn"
            
            # 仅将 Jira 内网域名加入 NO_PROXY 免代理名单，防止影响外网大模型 API 的调用
            original_no_proxy = os.environ.get('NO_PROXY', '')
            if original_no_proxy and jira_host not in original_no_proxy:
                os.environ['NO_PROXY'] = f"{original_no_proxy},{jira_host}"
            elif not original_no_proxy:
                os.environ['NO_PROXY'] = jira_host
            
            client = JIRA(
                server=self.server,
                basic_auth=(self.username, self.api_token),
                # 某些内网环境可能需要关闭 SSL 验证，但为了安全默认开启
                options={'verify': True},
                proxies={
                    "http": None,
                    "https": None,
                },
                timeout=10 # 添加强制超时 10 秒
            )
            return client
        except JIRAError as e:
            print(f"Jira Connection Error: {e.text}")
            return None
        except Exception as e:
            print(f"Unexpected error connecting to Jira: {e}")
            return None

    def fetch_resolved_issues(self, jql_query: str, max_results: int = 50) -> List[Dict]:
        """
        根据自定义 JQL 查询已解决的工单，并提取核心字段和评论。
        
        Args:
            jql_query: 用户自定义的 JQL 字符串
            max_results: 最大返回数量，防止单次请求过大
            
        Returns:
            包含工单信息的字典列表
        """
        if not self.client:
            raise ConnectionError("Jira client is not connected. Check your credentials.")

        try:
            # 执行 JQL 查询，展开 comments 字段以获取评论内容
            issues = self.client.search_issues(
                jql_query,
                maxResults=max_results,
                fields="summary,description,comment,resolution,assignee"
            )
        except JIRAError as e:
            raise ValueError(f"JQL Error: {e.text}")

        extracted_data = []
        for issue in issues: # type: ignore
            issue_dict = {
                "key": issue.key,
                "url": f"{self.server}/browse/{issue.key}",
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "resolution": issue.fields.resolution.name if issue.fields.resolution else "None",
                "comments": self._extract_and_clean_comments(issue)
            }
            extracted_data.append(issue_dict)
            
        return extracted_data

    def _extract_and_clean_comments(self, issue) -> str:
        """
        提取工单的所有评论，并进行初步的清洗，过滤掉系统自动生成的无用信息。
        将多个评论合并为一个字符串供 LLM 分析。
        """
        if not hasattr(issue.fields, 'comment') or not issue.fields.comment.comments:
            return "No comments available."

        cleaned_comments = []
        for comment in issue.fields.comment.comments:
            author = comment.author.displayName if comment.author else "System"
            body = comment.body
            
            # 清洗逻辑 (可以根据公司 Jira 实际情况扩展)
            # 1. 过滤掉过短的评论 (例如 "ok", "done")
            if len(body.strip()) < 10:
                continue
                
            # 2. 过滤掉常见的系统自动回复关键字
            # (例如 Gitlab Webhook 自动回复, Jenkins 构建通知)
            system_keywords = [
                "Pipeline has passed",
                "SonarQube analysis reported",
                "This issue was automatically closed",
                "Pull request created"
            ]
            if any(keyword in body for keyword in system_keywords):
                continue
                
            # 3. 去除引用块内容 (可选，有时引用原问题会增加干扰)
            # body = re.sub(r'\{quote\}.*?\{quote\}', '[Quoted text removed]', body, flags=re.DOTALL)

            cleaned_comments.append(f"[{author}]: {body.strip()}")

        return "\n---\n".join(cleaned_comments) if cleaned_comments else "No meaningful comments found."

# 测试入口 (当直接运行此文件时)
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    SERVER = os.getenv("JIRA_SERVER")
    USER = os.getenv("JIRA_USERNAME")
    TOKEN = os.getenv("JIRA_API_TOKEN")
    
    if SERVER and USER and TOKEN:
        print(f"Testing connection to {SERVER}...")
        fetcher = JiraFetcher(SERVER, USER, TOKEN)
        
        # 使用一个极简的测试 JQL (请根据实际情况替换 YOUR_PROJECT)
        test_jql = "project = 'AIT' ORDER BY updated DESC"
        print(f"Executing JQL: {test_jql}")
        try:
            results = fetcher.fetch_resolved_issues(test_jql, max_results=2)
            if not results:
                print(f"⚠️ 警告: JQL 执行成功，但在您的 Jira 中没有找到符合条件的工单。")
                print(f"👉 请尝试将 'TEST' 替换为您真实的 Project Key (例如: project='PROJ')")
            for res in results:
                print(f"Key: {res['key']}")
                print(f"Summary: {res['summary']}")
                print(f"Comments extracted: {len(res['comments'])} chars")
                print("-" * 20)
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print("Missing Jira credentials in .env file. Skipping test.")
