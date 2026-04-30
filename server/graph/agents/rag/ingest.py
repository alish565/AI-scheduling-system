from pathlib import Path
# Text loading
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data.txt"
VECTOR_DB_PATH = BASE_DIR / "chroma_db"

def ingest():
    # 1️⃣ Load document
    loader = TextLoader(str(DATA_PATH), encoding="utf-8")
    documents = loader.load()

    # 2️⃣ Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,          # slightly bigger for policies
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "]
    )

    chunks = splitter.split_documents(documents)

    # 3️⃣ Add metadata (VERY important for filtering later)
    for chunk in chunks:
        chunk.metadata["source"] = "medical_center_knowledge"

    # 4️⃣ Embeddings
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small"
    )

    # 5️⃣ Create & persist vector DB
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(VECTOR_DB_PATH)
    )

    vectorstore.persist()

    print("✅ Knowledge base created successfully.")

if __name__ == "__main__":
    ingest()
