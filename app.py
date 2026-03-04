import streamlit as st
import requests
import json

# ==================== 专属配置（已根据你的 GitHub 定制）====================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_policy"
GITHUB_BRANCH = "main"
FILE_FOLDER = "data"  # 文件在 data 文件夹里

# 文档文件名（根据截图看到的实际文件）
DOCUMENT_FILES = [
    "北极星制度汇编202602.docx",
    "同润制度汇编202602.docx",
    "同登制度汇编202602.docx",
]
# ========================================================================

st.set_page_config(page_title="企业制度助手", page_icon="📚", layout="wide")

st.title("📚 企业制度智能助手")

# 从 Streamlit Secrets 获取 API Key（必须在 Streamlit Cloud 配置）
try:
    api_key = st.secrets["QWEN_API_KEY"]
except:
    st.error("❌ 请在 Streamlit Cloud 配置 API Key")
    st.info("""
    ### 配置步骤：
    
    1. 点击右上角 **⚙️ Settings**
    2. 找到 **Secrets** 标签
    3. 添加以下内容：
    ```
    QWEN_API_KEY = "sk-你的API-Key"
    ```
    4. 保存并重启应用
    
    **获取 API Key：** https://bailian.console.aliyun.com/
    """)
    st.stop()

# 显示配置信息
with st.sidebar:
    st.success("✅ API Key 已配置")
    st.markdown("---")
    st.info(f"""
    ### 📄 GitHub 配置
    **仓库**: {GITHUB_USERNAME}/{GITHUB_REPO}  
    **分支**: {GITHUB_BRANCH}  
    **文件夹**: {FILE_FOLDER}/  
    **文档**: {len(DOCUMENT_FILES)} 个
    """)
    
    if st.button("🔄 重新加载文档"):
        st.cache_data.clear()
        st.rerun()

def call_qwen(api_key, question, context):
    """调用千问 API"""
    try:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "qwen-plus",
                "messages": [
                    {"role": "system", "content": "你是企业制度问答助手，请基于提供的制度文档准确回答问题。"},
                    {"role": "user", "content": f"企业制度文档：\n{context[:6000]}\n\n用户问题：{question}\n\n请根据文档内容回答。"}
                ],
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ API 错误 ({response.status_code}): {response.text[:200]}"
    except Exception as e:
        return f"❌ 调用失败: {str(e)}"

@st.cache_data(show_spinner=False)
def load_docs():
    """从 GitHub 加载文档"""
    all_text = ""
    success_files = []
    failed_files = []
    
    # 构建基础 URL（包含 data 文件夹）
    base_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{GITHUB_BRANCH}/{FILE_FOLDER}/"
    
    for filename in DOCUMENT_FILES:
        url = base_url + filename
        
        with st.spinner(f"正在加载 {filename}..."):
            try:
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    # 处理 Word 文档
                    from docx import Document
                    import io
                    doc = Document(io.BytesIO(response.content))
                    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    
                    all_text += f"\n\n{'='*50}\n文档：{filename}\n{'='*50}\n{text}"
                    success_files.append(filename)
                    st.success(f"✅ {filename}")
                else:
                    failed_files.append((filename, f"HTTP {response.status_code}"))
                    st.error(f"❌ {filename} - 错误 {response.status_code}")
                    
            except Exception as e:
                failed_files.append((filename, str(e)))
                st.error(f"❌ {filename} - {str(e)}")
    
    # 显示加载结果
    if success_files:
        st.success(f"📄 成功加载 {len(success_files)}/{len(DOCUMENT_FILES)} 个文档")
    
    if failed_files:
        st.warning("⚠️ 部分文件加载失败，但可以继续使用已加载的文档")
    
    return all_text, success_files

# 主界面
st.markdown("### 📚 正在加载文档...")
docs, success_files = load_docs()

if len(docs) > 100 and success_files:
    st.success(f"✅ 准备就绪！已加载 {len(success_files)} 个制度文档")
    
    # 聊天界面
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    
    # 显示历史消息
    for msg in st.session_state.msgs:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # 用户输入
    if prompt := st.chat_input("请输入关于企业制度的问题..."):
        # 用户消息
        st.session_state.msgs.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 回复
        with st.chat_message("assistant"):
            with st.spinner("正在思考..."):
                reply = call_qwen(api_key, prompt, docs)
                st.write(reply)
        
        st.session_state.msgs.append({"role": "assistant", "content": reply})
    
    # 底部按钮
    if st.button("🗑️ 清空对话历史"):
        st.session_state.msgs = []
        st.rerun()

else:
    st.error("❌ 文档加载失败")
    st.info("""
    ### 可能的原因：
    1. 网络连接问题
    2. GitHub 访问受限
    3. 文件格式问题
    
    请稍后重试或检查文件配置
    """)

# 页脚
st.markdown("---")
st.caption("企业制度智能助手 | Powered by 阿里云千问 & Streamlit")


