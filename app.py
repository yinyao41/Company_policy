import streamlit as st
import os
from utils import load_and_split_docs, build_or_load_vectorstore, get_recommendations
from rag_chain import create_rag_chain

st.set_page_config(
    page_title="企业制度学习助手",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("企业制度学习与培训助手")
st.caption("基于《同润制度汇编202602》、《同登制度汇编202602》、《北极星制度汇编202602》")

# ─── 检查 data 目录是否存在文件 ────────────────────────────────
data_dir = "data"
if not os.path.exists(data_dir) or not any(f.endswith(".docx") for f in os.listdir(data_dir)):
    st.error("未找到任何制度文档！\n请确认仓库的 data/ 目录中已包含三份 .docx 文件。")
    st.stop()

# ─── 只在第一次执行向量库构建 ────────────────────────────────
if "rag_chain" not in st.session_state:
    with st.status("正在初始化制度知识库（首次加载较慢，请耐心等待）...", expanded=True) as status:
        try:
            status.update(label="步骤1/3：读取制度文档...", state="running")
            docs = load_and_split_docs(data_dir)
            status.update(label=f"已读取 {len(docs)} 个文本片段", state="running")

            status.update(label="步骤2/3：构建/加载向量数据库...", state="running")
            vectorstore = build_or_load_vectorstore(docs)
            status.update(label="向量库准备完成", state="running")

            status.update(label="步骤3/3：创建 RAG 问答链...", state="running")
            retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
            st.session_state.retriever = retriever
            st.session_state.rag_chain = create_rag_chain(retriever)

            status.update(label="制度知识库初始化完成！", state="complete", expanded=False)
            st.success("知识库加载成功，可以开始提问啦～")
        except Exception as e:
            status.update(label=f"初始化失败：{str(e)}", state="error")
            st.error("知识库加载失败，可能原因：\n1. docx 文件损坏\n2. 依赖库问题\n3. DashScope API Key 无效\n请联系管理员检查。")
            st.stop()

# ─── 侧边栏快速信息 ───────────────────────────────────────────
with st.sidebar:
    st.markdown("**当前制度文件**")
    for f in os.listdir(data_dir):
        if f.endswith(".docx"):
            st.markdown(f"- {f}")

# ─── 聊天历史与交互（保持不变） ────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("请输入制度相关问题，例如：加班费如何计算？"):
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("正在查询制度内容..."):
            try:
                answer = st.session_state.rag_chain.invoke(question)
                
                rec_docs = get_recommendations(question, st.session_state.retriever)
                
                st.markdown(answer)
                
                if rec_docs:
                    st.markdown("**📌 相关制度推荐**")
                    for i, doc in enumerate(rec_docs, 1):
                        src = doc.metadata.get("source_file", "未知")
                        preview = doc.page_content[:180].replace("\n", " ").strip() + " ..."
                        st.markdown(f"{i}. **{src}**  ·  {preview}")
            except Exception as e:
                st.error(f"回答生成失败：{str(e)}")

    st.session_state.messages.append({"role": "assistant", "content": answer})
