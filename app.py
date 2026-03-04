import streamlit as st
import requests
from docx import Document
import io
import os
from openai import OpenAI

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
    
    for doc_name, url in GITHUB_DOCS.items():
        try:
            response = requests.get(url)
            if response.status_code == 200:
                doc = Document(io.BytesIO(response.content))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
                all_text += f"\n\n=== {doc_name} ===\n{text}"
            else:
                st.warning(f"无法加载 {doc_name}")
        except Exception as e:
            st.error(f"加载 {doc_name} 时出错: {str(e)}")
    
    return all_text

def query_qwen(api_key, question, context):
    """调用阿里云千问 API"""
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 构建提示词
        prompt = f"""你是一个企业制度问答助手。请基于以下企业制度文档内容回答用户问题。
        
企业制度文档内容：
{context[:8000]}  # 限制上下文长度

用户问题：{question}

请提供准确、专业的回答，如果文档中没有相关信息，请明确说明。"""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "你是一个专业的企业制度问答助手，擅长解读和解释企业规章制度。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return completion.choices[0].message.content
    
    except Exception as e:
        return f"API 调用错误: {str(e)}"

# 主界面
if not api_key:
    st.warning("⚠️ 请在左侧输入阿里云千问 API Key")
else:
    # 加载文档
    with st.spinner("正在加载企业制度文档..."):
        documents_content = load_documents_from_github()
    
    if documents_content:
        st.success("✅ 文档加载成功！")
        
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
                    response = query_qwen(api_key, question, documents_content)
                    st.markdown(response)
            
            # 添加助手消息
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        # 清除对话按钮
        if st.button("🗑️ 清除对话历史"):
            st.session_state.messages = []
            st.rerun()
    else:
        st.error("❌ 无法加载文档，请检查 GitHub 仓库配置")

# 页脚
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>企业制度智能助手 | 基于阿里云千问 | Powered by Streamlit</small>
</div>
""", unsafe_allow_html=True)
