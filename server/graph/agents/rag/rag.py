from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.messages import SystemMessage, HumanMessage




BASE_DIR = Path(__file__).resolve().parent

RAG_PROMPT = """
You are an AI assistant for a medical center.
you can talk with pateints normally,except if the user is asking informative questions about the clinic and the doctors where you have access to a knowledge base with important information about doctors, specialties, and booking procedures.
Answer ONLY using the provided context.
If the answer is not in the context, say:
"I don't have that information."

Context:
{context}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", RAG_PROMPT),
    ("human", "{question}")
])

def get_retriever():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=str(BASE_DIR / "chroma_db"),
        embedding_function=embeddings
    )
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    return retriever

retriever = get_retriever()


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def rag_chain_node(state: dict) -> dict:

    history = state["messages"][:-1]
    last_message = state["messages"][-1]

    raw_question = last_message.content if hasattr(last_message, "content") else str(last_message)

    if len(history) > 0:
        system_rewrite = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )

        rewrite_response = llm.invoke([
            SystemMessage(content=system_rewrite),
            *history,
            HumanMessage(content=raw_question)
        ])
        search_query = rewrite_response.content
    else:
        search_query = raw_question


    docs = retriever.invoke(search_query)
    context_text = "\n".join([d.page_content for d in docs])

    response = llm.invoke([
        {"role": "system", "content": RAG_PROMPT.format(context=context_text)},
        {"role": "user", "content": raw_question}
    ])

  
    state["messages"].append(response)
    return state