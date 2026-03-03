# app.py —— 所有逻辑放在一个文件里，极简且兼容 2026 年 Streamlit Cloud 版本

import streamlit as st
import os
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter   # 修正：使用新路径
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatDashScope
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ────────────────────────────────────────────────
# 配置（可根据需要微调）
# ────────────────────────────────────────────────
DATA_DIR = "data"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
EMBEDDING_MODEL = "text-embedding-v2"
LLM_MODEL = "qwen-max"           # 可改为 qwen-plus 或 qwen-turbo 降低成本
RETRIEVER_K = 6

# ────────────────────────────────────────────────
# 文档加载与切分
# ────────────────────────────────────────────────
@st.cache_resource(show_spinner="正在读取制度文档...")
def load_documents():
    if not os.path.exists(DATA_DIR):
        st.error(f"目录 '{DATA_DIR}' 不存在，请确认仓库中包含 data/ 文件夹和 .docx 文件")
        st.stop()

    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )

    found_files = False
    for filename in os.listdir(DATA_DIR):
        if filename.lower().endswith(".docx"):
            found_files = True
            path = os.path.join(DATA_DIR, filename)
            try:
                loader = Docx2txtLoader(path)
                raw = loader.load()
                split = splitter.split_documents(raw)
                for d in split:
                    d.metadata["source_file"] = filename
                docs.extend(split)
            except Exception as e:
                st.warning(f"加载文件 {filename} 失败：{str(e)}")

    if not found_files:
        st.error("data/ 目录下没有找到任何 .docx 文件")
        st.stop()
    if not docs:
        st.error("所有 .docx 文件内容为空或解析失败")
        st.stop()

    return docs

# ────────────────────────────────────────────────
# 向量数据库
# ────────────────────────────────────────────────
@st.cache_resource(show_spinner="正在构建/加载向量数据库...")
def get_vectorstore(docs):
    try:
        embeddings = DashScopeEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="policy_rag_collection"
        )
        return vectorstore
    except Exception as e:
        st.error(f"向量数据库创建失败：{str(e)}\n可能原因：DashScope API Key 无效或网络问题")
        st.stop()

# ────────────────────────────────────────────────
# RAG 链
# ────────────────────────────────────────────────
@st.cache_resource
def create_rag_chain(retriever):
    llm = ChatDashScope(
        model=LLM_MODEL,
        temperature=0.3,
        streaming=True
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位严格的企业制度培训助手。
只能基于下面检索到的制度条款内容回答问题。
请尽量引用条款编号、标题或原文关键句。
如果问题与三份制度汇编无关，或检索内容不足以回答，
请回复：“此问题超出当前制度培训知识库范围，请咨询人力资源部或相关负责人。”

已检索内容：
{context}

当前问题：{question}"""),
        ("human", "{question}")
    ])

    def format_docs(docs):
        return "\n\n".join(
            f"【来源：{d.metadata.get('source_file', '未知文件')}】\n{d.page_content.strip()}"
            for d in docs
        )

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

# ────────────────────────────────────────────────
# 主界面
# ────────────────────────────────────────────────
st.title("企业制度学习助手")
st.caption("基于《同润制度汇编202602》、《同登制度汇编202602》、《北极星制度汇编202602》")

# 初始化（只执行一次）
if "rag_chain" not in st.session_state:
    with st.spinner("首次加载知识库（需要 1–3 分钟，请耐心等待）..."):
        try:
            docs = load_documents()
            vectorstore = get_vectorstore(docs)
            retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
            st.session_state.rag_chain = create_rag_chain(retriever)
            st.session_state.retriever = retriever
            st.success("知识库加载完成，可以开始提问")
        except Exception as e:
            st.error(f"知识库初始化失败：{str(e)}")
            st.stop()

# 聊天历史显示
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if question := st.chat_input("请输入制度相关问题，例如：年假怎么计算？"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("查询中..."):
            try:
                answer = st.session_state.rag_chain.invoke(question)
                st.markdown(answer)

                # 简单推荐功能：显示 Top-3 相关片段
                relevant_docs = st.session_state.retriever.invoke(question)
                if relevant_docs:
                    st.markdown("**相关制度片段参考：**")
                    for i, doc in enumerate(relevant_docs[:3], 1):
                        src = doc.metadata.get("source_file", "未知文件")
                        preview = doc.page_content[:180].replace("\n", " ").strip() + "..."
                        st.markdown(f"{i}. **{src}** · {preview}")
            except Exception as e:
                st.error(f"生成回答失败：{str(e)}")

    # 保存回答到历史
    st.session_state.messages.append({"role": "assistant", "content": answer})
