# rag_chain.py
from langchain_community.chat_models import ChatDashScope
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def create_rag_chain(retriever):
    """
    创建 RAG 问答链
    - retriever: 已构建好的向量检索器
    返回: 可直接 .invoke() 的 chain
    """
    # 使用阿里通义千问模型
    llm = ChatDashScope(
        model="qwen-max",          # 或 qwen-plus / qwen-turbo，根据你的配额选择
        temperature=0.3,           # 较低温度 → 更严谨、少胡说
        streaming=True             # 支持流式输出（打字机效果）
    )

    # 系统提示词（非常重要！限制模型只能回答制度相关内容）
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一位严格的企业制度培训助手。
只能基于下面检索到的制度条款内容来回答问题。
回答要准确、严谨、条理清晰，尽量引用条款编号、标题或原文关键句。
如果问题与三份制度汇编（同润、同登、北极星）无关，或检索内容不足以回答，
请礼貌回复：“这个问题超出当前制度培训知识库范围，请咨询人力资源部或相关负责人。”

已检索到的上下文：
{context}

当前用户问题：{question}"""),
        ("human", "{question}")
    ])

    # 格式化检索到的文档（加来源标识，便于追溯）
    def format_docs(docs):
        return "\n\n".join(
            f"【来源文件：{d.metadata.get('source_file', '未知')}】\n{d.page_content.strip()}"
            for d in docs
        )

    # 构建 LangChain Runnable 链
    chain = (
        {
            "context": retriever | format_docs,   # 检索 → 格式化上下文
            "question": RunnablePassthrough()     # 直接透传用户问题
        }
        | prompt                                  # 应用提示词模板
        | llm                                     # 调用大模型生成
        | StrOutputParser()                       # 输出纯文本
    )

    return chain
