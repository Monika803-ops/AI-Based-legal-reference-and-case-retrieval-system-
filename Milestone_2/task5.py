import os
import json
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredHTMLLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pinecone import Pinecone, ServerlessSpec

# ---------------- CONFIG ----------------
INDEX_NAME = "legal-chatbot"
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ---------------- PATHS ----------------
# Base directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Parent directory (project root)
PARENT_DIR = os.path.dirname(BASE_DIR)

# DATA_FOLDER is in parent directory
DATA_FOLDER = os.path.join(PARENT_DIR, "data")

# Task2 chunks file is in project root's task2_output folder
IPC_CHUNKS_FILE = os.path.join(PARENT_DIR, "task2_output", "ipc_laws_sentence_chunks.json")

# Output file in parent directory -> task5_output
OUTPUT_FILE = os.path.join(PARENT_DIR, "task5_output", "all_chunks_embeddings.json")

# ---------------- ENV ----------------
# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")  # not directly used with ServerlessSpec

# ---------------- HELPERS ----------------
def load_document(path: str):
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(path)
        return loader.load()
    elif ext == ".txt":
        loader = TextLoader(path, encoding="utf-8")
        return loader.load()
    elif ext in [".doc", ".docx"]:
        loader = UnstructuredWordDocumentLoader(path)
        return loader.load()
    elif ext == ".html":
        loader = UnstructuredHTMLLoader(path)
        return loader.load()
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def get_all_task1_chunks(data_folder, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    all_docs = []
    if not os.path.exists(data_folder):
        raise FileNotFoundError(f"Data folder not found: {data_folder}")

    for file in os.listdir(data_folder):
        path = os.path.join(data_folder, file)
        try:
            docs = load_document(path)
            for d in docs:
                d.metadata["source_file"] = file
            all_docs.extend(docs)
            print(f"✅ Loaded {len(docs)} docs from {file}")
        except Exception as e:
            print(f"❌ Could not load {file}: {e}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    split_docs = splitter.split_documents(all_docs)
    print(f"✂️ Task1 docs split into {len(split_docs)} chunks")
    return [{"text": doc.page_content, "metadata": doc.metadata} for doc in split_docs]

def get_task2_chunks(ipc_chunks_file):
    if not os.path.exists(ipc_chunks_file):
        raise FileNotFoundError(f"Task2 chunks file not found: {ipc_chunks_file}")
    with open(ipc_chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    out = []
    for c in chunks:
        meta = {k: v for k, v in c.items() if k != "content"}
        out.append({"text": c.get("content", ""), "metadata": meta})
    print(f"✅ Loaded {len(out)} Task2 chunks from {ipc_chunks_file}")
    return out

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Embedding model
    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing:
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    index = pc.Index(INDEX_NAME)

    # Load chunks
    all_chunks = []
    all_chunks.extend(get_all_task1_chunks(DATA_FOLDER))
    all_chunks.extend(get_task2_chunks(IPC_CHUNKS_FILE))
    print(f"📊 Total chunks to embed and upload: {len(all_chunks)}")

    # Upsert embeddings in batches
    batch_size = 100
    last_vectors = []  # keep track of the last batch for fetch verification
    for start in range(0, len(all_chunks), batch_size):
        batch = all_chunks[start:start + batch_size]
        texts = [c["text"] for c in batch]
        embeddings = embedder.embed_documents(texts)

        vectors = []
        for j, (emb, chunk) in enumerate(zip(embeddings, batch)):
            meta = dict(chunk.get("metadata", {}) or {})
            meta["text"] = chunk["text"]
            if "source_file" in meta and "source" not in meta:
                meta["source"] = meta.pop("source_file")
            vec_id = str(meta.get("id")) if meta.get("id") else f"chunk-{start + j + 1}"
            vectors.append({
                "id": vec_id,
                "values": emb,
                "metadata": meta
            })

        index.upsert(vectors=vectors)
        last_vectors = vectors  # store last batch
        print(f"⬆️ Upserted vectors {start+1} to {start+len(vectors)}")

    # Save locally as backup in parent/task5_output
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    # Quick verification
    if last_vectors:
        sample_id = last_vectors[0]["id"]
        fetched = index.fetch(ids=[sample_id])
        if sample_id in fetched.vectors:
            print("✅ Fetched metadata for", sample_id, "->", fetched.vectors[sample_id].metadata)
        else:
            print("❌ Could not fetch sample vector:", sample_id)

    print(f"🎉 All chunks uploaded to Pinecone index '{INDEX_NAME}' and saved locally at '{OUTPUT_FILE}'.")
