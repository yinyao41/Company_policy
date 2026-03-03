# app.py   ——  所有逻辑都放在一个文件里，极简版

import streamlit as st
import os
from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatDashScope
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# ────────────────────────────────────────────────
# 配置
# ────────────────────────────────────────────────
DATA_DIR = "data"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
EMBEDDING_MODEL = "text-embedding-v2"
LLM_MODEL = "qwen-max"
RETRIEVER_K = 6

# ────────────────────────────────────────────────
# 文档加载与切分（一次性执行）
# ────────────────────────────────────────────────
@st.cache_resource(show_spinner="正在读取制度文档...")
def load_documents():
    if not os.path.exists(DATA_DIR):
        st.error(f"目录 {DATA_DIR} 不存在")
        st.stop()
    
    docs = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
    )
    
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".docx"):
            path = os.path.join(DATA_DIR, filename)
            loader = Docx2txtLoader(path)
            raw = loader.load()
            split = splitter.split_documents(raw)
            for d in split:
                d.metadata["source_file"] = filename
            docs.extend(split)
    
    if not docs:
        st.error("没有找到任何 .docx 文件或内容为空")
        st.stop()
    
    return docs

# ────────────────────────────────────────────────
# 向量库（缓存）
# ────────────────────────────────────────────────
@st.cache_resource(show_spinner="正在构建/加载向量数据库...")
def get_vectorstore(docs):
    embeddings = DashScopeEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="policy_docs"
    )
    return vectorstore

# ────────────────────────────────────────────────
# RAG 链（一次性创建）
# ────────────────────────────────────────────────
@st.cache_resource
def create_rag_chain(_retriever):
    llm = ChatDashScope(model=LLM_MODEL, temperature=0.3, streaming=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位企业制度培训助手。
只能基于以下检索到的制度内容回答。
如果问题与制度无关或内容不足，请回复：“此问题超出制度培训范围，请咨询人力资源部。”

已检索内容：
{context}

问题：{question}"""),
        ("human", "{question}")
    ])

    def format_docs(docs):
        return "\n\n".join(
            f"【{d.metadata.get('source_file', '未知')}】\n{d.page_content.strip()}"
            for d in docs
        )

    chain = (
        {"context": _retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

# ────────────────────────────────────────────────
# 主程序
# ────────────────────────────────────────────────
st.title("企业制度学习助手")
st.caption("支持同润 / 同登 / 北极星 三份制度汇编")

# 初始化
try:
    docs = load_documents()
    vectorstore = get_vectorstore(docs)
    retriever = vectorstore.as_retriever(search_kwargs={"k": RETRIEVER_K})
    chain = create_rag_chain(retriever)
except Exception as e:
    st.error(f"初始化失败：{str(e)}")
    st.stop()

# 聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
if question := st.chat_input("请输入制度相关问题..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("查询中..."):
            try:
                answer = chain.invoke(question)
                st.markdown(answer)

                # 简单推荐（显示 Top-3 来源）
                docs = retriever.invoke(question)
                if docs:
                    st.markdown("**相关制度片段参考：**")
                    for i, d in enumerate(docs[:3], 1):
                        src = d.metadata.get("source_file", "未知")
                        text = d.page_content[:180].replace("\n", " ").strip() + "..."
                        st.markdown(f"{i}. **{src}**  ·  {text}")
            except Exception as e:
                st.error(f"生成回答失败：{str(e)}")

    st.session_state.messages.append({"role": "assistant", "content": answer})
