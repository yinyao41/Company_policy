import streamlit as st
import requests
from docx import Document
import io
import json

# 页面配置
st.set_page_config(
    page_title="企业制度智能助手",
    page_icon="📚",
    layout="wide"
)

# 标题
st.title("📚 企业制度智能助手")
st.markdown("基于阿里云千问的企业制度文档问答系统")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 配置")
    
    # API Key 输入
    api_key = st.text_input(
        "阿里云千问 API Key",
        type="password",
        help="请输入您的阿里云千问 API Key"
    )
    
    st.markdown("---")
    st.markdown("### 📄 已加载的制度文档")
    st.markdown("""
    - 北极星制度汇编202602
    - 同登制度汇编202602 (2份)
    """)
    
    st.markdown("---")
    st.markdown("### 💡 使用提示")
    st.markdown("""
    1. 输入阿里云千问 API Key
    2. 在下方输入您的问题
    3. 系统会基于企业制度文档回答
    """)

# GitHub 文档 URL 配置
GITHUB_DOCS = {
    "北极星制度汇编202602": "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/北极星制度汇编202602.docx",
    "同登制度汇编202602_1": "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/同登制度汇编202602_1.docx",
    "同登制度汇编202602_2": "https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/同登制度汇编202602_2.docx",
}

@st.cache_data
def load_documents_from_github():
    """从 GitHub 加载 Word 文档"""
    all_text = ""
    success_count = 0
    
    for doc_name, url in GITHUB_DOCS.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                doc = Document(io.BytesIO(response.content))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
                all_text += f"\n\n=== {doc_name} ===\n{text}"
                success_count += 1
            else:
                st.warning(f"⚠️ 无法加载 {doc_name} (状态码: {response.status_code})")
        except Exception as e:
            st.error(f"❌ 加载 {doc_name} 时出错: {str(e)}")
    
    if success_count > 0:
        st.success(f"✅ 成功加载 {success_count}/{len(GITHUB_DOCS)} 个文档")
    
    return all_text

def query_qwen_api(api_key, question, context):
    """使用 requests 直接调用阿里云千问 API"""
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 构建提示词
        prompt = f"""你是一个企业制度问答助手。请基于以下企业制度文档内容回答用户问题。

企业制度文档内容：
{context[:6000]}

用户问题：{question}

请提供准确、专业的回答，如果文档中没有相关信息，请明确说明。"""

        data = {
            "model": "qwen-plus",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的企业制度问答助手，擅长解读和解释企业规章制度。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1500
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_msg = f"API 调用失败 (状态码: {response.status_code})"
            try:
                error_detail = response.json()
                error_msg += f"\n错误详情: {error_detail}"
            except:
                error_msg += f"\n响应内容: {response.text[:200]}"
            return error_msg
    
    except requests.exceptions.Timeout:
        return "❌ 请求超时，请稍后重试"
    except requests.exceptions.ConnectionError:
        return "❌ 网络连接错误，请检查网络设置"
    except Exception as e:
        return f"❌ 发生错误: {str(e)}"

# 主界面
if not api_key:
    st.warning("⚠️ 请在左侧输入阿里云千问 API Key")
    st.info("""
    ### 如何获取 API Key：
    1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/)
    2. 登录并开通 DashScope 服务
    3. 在 API-KEY 管理中创建新的 API Key
    4. 复制 API Key 并粘贴到左侧输入框
    """)
else:
    # 加载文档
    with st.spinner("正在从 GitHub 加载企业制度文档..."):
        documents_content = load_documents_from_github()
    
    if documents_content and len(documents_content) > 100:
        # 初始化聊天历史
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 显示聊天历史
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 用户输入
        if question := st.chat_input("请输入您关于企业制度的问题..."):
            # 添加用户消息
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)
            
            # 获取回答
            with st.chat_message("assistant"):
                with st.spinner("正在思考..."):
                    response = query_qwen_api(api_key, question, documents_content)
                    st.markdown(response)
            
            # 添加助手消息
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        # 清除对话按钮
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("🗑️ 清除对话"):
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("🔄 刷新文档"):
                st.cache_data.clear()
                st.rerun()
    else:
        st.error("❌ 无法加载文档，请检查以下配置：")
        st.markdown("""
        ### 检查清单：
        1. ✅ GitHub 仓库是否设为 **Public**（公开）
        2. ✅ 文档文件是否已上传到仓库
        3. ✅ app.py 中的 GitHub 链接是否正确
        4. ✅ 文件名是否与代码中配置一致
        
        ### 正确的 URL 格式：
        ```
        https://raw.githubusercontent.com/用户名/仓库名/main/文件名.docx
        ```
        
        ### 当前配置的 URL：
        """)
        for name, url in GITHUB_DOCS.items():
            st.code(f"{name}: {url}")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>企业制度智能助手 v1.1 | 基于阿里云千问 | Powered by Streamlit</small>
</div>
""", unsafe_allow_html=True)

