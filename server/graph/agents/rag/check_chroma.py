import os
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

BASE_DIR = Path(__file__).resolve().parent
db_path = str(BASE_DIR / "chroma_db")

print(f"📦 Checking path: {db_path}")
print(f"📂 Path exists? {os.path.exists(db_path)}")

try:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings
    )
    
    # Get all data inside the default collection
    data = vectorstore.get()
    ids = data.get("ids", [])
    print(f"🔢 Total documents found in vector store: {len(ids)}")
    if ids:
        print(f"📄 Sample document snippet: {data.get('documents', [None])[0]}")
except Exception as e:
    print(f"❌ Error connecting to Chroma: {e}")