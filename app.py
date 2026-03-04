# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
#  配置区（最重要三项请务必修改/确认）
# =============================================================================

GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_policy"
BRANCH = "main"   # 确认你的默认分支是 main 还是 master

# 三个制度文件的相对路径（请与 GitHub 上的实际文件名完全一致）
POLICY_FILES = [
    "data/同登制度汇编202602.docx",
    "data/同润制度汇编202602.docx",
    # 如果第三个文件名不同，请在这里修改，例如：
    # "data/同昇制度汇编202602.docx",
    "data/同登制度汇编202602.docx",   # ← 你描述中有重复，建议确认并修正
]

# 系统提示词（控制大模型行为）
SYSTEM_PROMPT = """你是一位专业、严谨、只回答公司制度相关问题的企业制度咨询助手。
你的全部知识来源于下方提供的制度文本，不得使用任何外部知识或编造内容。
回答时请尽量引用原文条款、章节或具体表述，并保持客观中立。
如果问题明显与公司制度无关，请礼貌回复：
“抱歉，本助手仅回答与公司制度相关的问题，请提出制度相关咨询。”"""

# =============================================================================
#  初始化大模型客户端（阿里通义千问 DashScope 兼容 OpenAI 接口）
# =============================================================================

# 强烈建议通过 Streamlit Secrets 或环境变量传入，不要硬编码！
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))

if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY。请在 Streamlit Cloud → Settings → Secrets 中添加密钥")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 常用模型选项（2026年主流选择，可根据配额/效果调整）
MODEL_NAME = "qwen-max"          # 推荐：qwen-max / qwen-plus / qwen2.5-max / qwen-turbo

# =============================================================================
#  从 GitHub 下载并解析所有制度文件 → 只执行一次并缓存
# =============================================================================

@st.cache_data(show_spinner="正在从 GitHub 下载并解析制度文件...")
def load_policies():
    documents = []

    for rel_path in POLICY_FILES:
        url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{rel_path}"
        
        try:
            r = requests.get(url, timeout=12)
            r.raise_for_status()
            
            doc = Document(BytesIO(r.content))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            
            if text:
                # 显示用文件名（去掉 data/ 前缀和 .docx）
                display_name = rel_path.split("/")[-1].replace(".docx", "")
                documents.append(f"【{display_name}】\n{text}\n{'─'*60}\n")
            else:
                st.warning(f"文件内容为空：{rel_path}")
                
        except Exception as e:
            st.error(f"无法读取文件 {rel_path}\n错误：{str(e)}")
            continue

    if not documents:
        st.error("所有制度文件加载失败，无法继续运行。请检查 GitHub 文件是否存在且可公开访问。")
        st.stop()

    full_text = "".join(documents)
    
    # 如果文本非常非常长，可以在这里简单截断（视模型上下文窗口而定）
    # full_text = full_text[:320000]   # 约 qwen-max 支持的 80% 容量，视情况开启
    
    return full_text


# 加载制度内容（缓存机制，部署后只加载一次）
POLICIES_TEXT = load_policies()


# =============================================================================
#               Streamlit 聊天界面
# =============================================================================

st.set_page_config(page_title="企业制度问答助手", layout="wide")

st.title("企业制度智能问答")
st.caption("基于 GitHub 上传的制度汇编文件 · 由通义千问驱动")

# 初始化会话历史
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n以下是完整的制度文本（请严格依据此内容回答）：\n\n" + POLICIES_TEXT}
    ]

# 显示历史对话
for message in st.session_state.messages[1:]:  # 跳过 system prompt
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 用户输入框
if user_input := st.chat_input("请输入关于公司制度的问题..."):
    
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("正在查询制度内容..."):
            try:
                stream = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=st.session_state.messages,
                    temperature=0.25,
                    max_tokens=1800,
                    stream=True
                )
                
                response_container = st.empty()
                full_response = ""
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        response_container.markdown(full_response + "▌")
                
                response_container.markdown(full_response)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"模型调用失败：{str(e)}")
                if "401" in str(e) or "invalid api key" in str(e).lower():
                    st.warning("API Key 可能无效或已过期，请检查 Streamlit Secrets 设置")

