# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
# 配置区（已适配你的仓库）
# =============================================================================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_policy"
BRANCH = "master"

# 三个制度文件的精确路径
POLICY_FILES = [
    "data/同登制度汇编202602.docx",
    "data/同润制度汇编202602.docx",
    "data/北极星制度汇编202602.docx",
]

# 系统提示词
SYSTEM_PROMPT = """你是一位专业、严谨的企业制度咨询助手。
你的全部知识仅来源于下方提供的三份制度文件，不得使用任何外部知识或编造内容。
回答时请尽量引用原文条款、章节编号或具体表述，保持客观中立。
如果用户问题与公司制度无关，请礼貌回复：
“抱歉，本助手仅回答与公司制度相关的问题，请提出制度相关咨询。”"""

# =============================================================================
# 阿里通义千问客户端
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))

if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Cloud → Settings → Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-max"

# =============================================================================
# 从 GitHub 下载并解析制度文件 + 后台自动截断（不显示任何提醒）
# =============================================================================
@st.cache_data(show_spinner="正在从 GitHub 下载并解析制度文件...")
def load_policies():
    documents = []
    for rel_path in POLICY_FILES:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{rel_path}"
        
        try:
            r = requests.get(raw_url, timeout=15)
            r.raise_for_status()
            
            doc = Document(BytesIO(r.content))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            
            if text:
                display_name = rel_path.split("/")[-1].replace(".docx", "")
                documents.append(f"【{display_name}】\n{text}\n{'─' * 80}\n")
            else:
                st.warning(f"文件内容为空：{rel_path}")
        except Exception as e:
            st.error(f"读取失败 {rel_path}：{str(e)}")
            continue

    if not documents:
        st.error("三个制度文件全部加载失败！")
        st.stop()

    full_text = "".join(documents)
    
    # 后台自动截断（不显示任何提醒）
    MAX_CHARS = 25000
    if len(full_text) > MAX_CHARS:
        full_text = full_text[:MAX_CHARS] + "\n\n【注意：制度全文已自动截断。若问题涉及未显示部分，请具体说明条款名称】"
    
    return full_text


# 执行加载（只返回文本）
POLICIES_TEXT = load_policies()

# =============================================================================
# Streamlit 界面（只剩主标题 + 聊天框）
# =============================================================================
st.set_page_config(page_title="企业制度问答助手", layout="wide")
st.title("🏢 企业制度智能问答助手")

# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": SYSTEM_PROMPT + "\n\n以下是公司全部制度文本（请严格依据此内容回答）：\n\n" + POLICIES_TEXT
    }]

# 显示历史消息
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("请输入关于公司制度的问题，例如：年假如何计算？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("正在查询制度原文..."):
            try:
                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages,
                    temperature=0.25,
                    max_tokens=2000,
                    stream=True
                )
                
                response_container = st.empty()
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_container.markdown(full_response + "▌")
                
                response_container.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"模型调用失败：{str(e)}")
                if "401" in str(e):
                    st.warning("API Key 无效或未设置，请检查 Streamlit Secrets")
       

