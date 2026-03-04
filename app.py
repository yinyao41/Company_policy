import streamlit as st
import requests
import json

# ==================== 配置区（只需修改这里）====================
# 1. 修改为你的 GitHub 用户名和仓库名
GITHUB_USERNAME = "yinyao41"  # 例如: "zhangsan"
GITHUB_REPO = "Company_policy"          # 例如: "company-chatbot"

# 2. 文档文件名（确保这些文件已上传到 GitHub 仓库根目录）
DOCUMENT_FILES = [
    "北极星制度汇编202602.docx",
    "同登制度汇编202602.docx", 
    "同登制度汇编202602.docx"
]
# ===========================================================

st.set_page_config(page_title="企业制度助手", page_icon="📚", layout="wide")

st.title("📚 企业制度智能助手")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    api_key = st.text_input("阿里云千问 API Key", type="password", 
                            help="在 https://bailian.console.aliyun.com/ 获取")
    
    st.markdown("---")
    st.info(f"""
    ### 📄 文档配置
    **GitHub**: {GITHUB_USERNAME}/{GITHUB_REPO}
    
    **文档数量**: {len(DOCUMENT_FILES)} 个
    """)

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
                    {"role": "system", "content": "你是企业制度问答助手。"},
                    {"role": "user", "content": f"制度内容：\n{context[:5000]}\n\n问题：{question}"}
                ]
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ API错误 ({response.status_code}): {response.text[:200]}"
    except Exception as e:
        return f"❌ 错误: {str(e)}"

@st.cache_data
def load_docs():
    """从 GitHub 加载文档 - 简化版（只读取文本）"""
    all_text = ""
    base_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/main/"
    
    # 检查配置
    if GITHUB_USERNAME == "YOUR_USERNAME" or GITHUB_REPO == "YOUR_REPO":
        st.error("❌ 请先在代码中配置 GITHUB_USERNAME 和 GITHUB_REPO！")
        st.stop()
    
    for filename in DOCUMENT_FILES:
        url = base_url + filename
        try:
            # 尝试下载文件
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                # 简单文本提取（如果是 docx 需要特殊处理）
                if filename.endswith('.txt'):
                    all_text += f"\n\n=== {filename} ===\n{r.text}"
                else:
                    # 对于 docx 文件，需要 python-docx
                    from docx import Document
                    import io
                    doc = Document(io.BytesIO(r.content))
                    text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
                    all_text += f"\n\n=== {filename} ===\n{text}"
                st.success(f"✅ 加载成功: {filename}")
            else:
                st.warning(f"⚠️ 无法加载: {filename} (错误{r.status_code})")
        except Exception as e:
            st.error(f"❌ 加载失败: {filename} - {e}")
    
    return all_text

# 主界面
if not api_key:
    st.warning("👈 请在左侧输入 API Key")
    st.info("**快速开始：**\n1. 获取[阿里云千问API Key](https://bailian.console.aliyun.com/)\n2. 在左侧输入API Key\n3. 开始提问")
else:
    # 加载文档
    docs = load_docs()
    
    if len(docs) > 100:
        # 聊天界面
        if "msgs" not in st.session_state:
            st.session_state.msgs = []
        
        for msg in st.session_state.msgs:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        if prompt := st.chat_input("输入问题..."):
            st.session_state.msgs.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    reply = call_qwen(api_key, prompt, docs)
                    st.write(reply)
            
            st.session_state.msgs.append({"role": "assistant", "content": reply})
        
        if st.button("🗑️ 清空"):
            st.session_state.msgs = []
            st.rerun()
    else:
        st.error("❌ 文档加载失败，请检查配置")

st.caption("企业制度智能助手 | Powered by 阿里云千问")

