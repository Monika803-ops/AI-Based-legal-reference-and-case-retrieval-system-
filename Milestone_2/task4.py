import os
import json
from pathlib import Path
from dotenv import load_dotenv

# LangChain loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore

# Pinecone SDK
from pinecone import Pinecone, ServerlessSpec

# =========================
# Document Loaders
# =========================
def load_pdf_document(path: str):
    return PyPDFLoader(path).load()

def load_docx_document(path: str):
    return UnstructuredWordDocumentLoader(path).load()

# =========================
# Save Helper
# =========================
def save_output(filename: str, data):
    # Save in parent directory
    output_dir = Path(__file__).resolve().parent.parent / "task4_output"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Saved output → {filepath}")

# =========================
# Main Pipeline
# =========================
if __name__ == "__main__":
    # Load .env from parent folder
    BASE_DIR = Path(__file__).resolve().parent
    load_dotenv(BASE_DIR.parent / ".env")

    # Pinecone API Key
    PINECONE_API = os.getenv("PINECONE_API_KEY")
    if not PINECONE_API:
        raise ValueError("Pinecone API Key not found in .env file")

    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API)
    INDEX_NAME = "chatbot"

    # Create index if it doesn't exist
    if INDEX_NAME not in [idx["name"] for idx in pc.list_indexes()]:
        pc.create_index(
            name=INDEX_NAME,
            dimension=384,  # embedding dimension
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(" Index created")

    # Connect to index
    index = pc.Index(INDEX_NAME)

    # =========================
    # Step 1: Load Documents
    # =========================
    data_folder = BASE_DIR.parent / "data"
    pdf_path = data_folder / "Time_Management.pdf"
    docx_path = data_folder / "Book_Importance.docx"

    pdf_docs = load_pdf_document(pdf_path) if pdf_path.exists() else []
    docx_docs = load_docx_document(docx_path) if docx_path.exists() else []

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    pdf_chunks = splitter.split_documents(pdf_docs)
    docx_chunks = splitter.split_documents(docx_docs)

    # Assign IDs
    for i, doc in enumerate(pdf_chunks):
        doc.metadata["id"] = f"pdf_{i}"
    for i, doc in enumerate(docx_chunks):
        doc.metadata["id"] = f"docx_{i}"

    # =========================
    # Step 2: Embeddings + Store in Pinecone
    # =========================
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_store = PineconeVectorStore(index=index, embedding=embeddings, namespace="default")

    # Add documents to Pinecone
    if pdf_chunks:
        vector_store.add_documents(pdf_chunks)
    if docx_chunks:
        vector_store.add_documents(docx_chunks)

    # Save all document vectors locally
    pdf_vectors = [
        {"id": d.metadata["id"], "text": d.page_content, "vector": embeddings.embed_query(d.page_content), "metadata": d.metadata}
        for d in pdf_chunks
    ]
    docx_vectors = [
        {"id": d.metadata["id"], "text": d.page_content, "vector": embeddings.embed_query(d.page_content), "metadata": d.metadata}
        for d in docx_chunks
    ]

    save_output("Time_Management_vectors.json", pdf_vectors)
    save_output("Book_Importance_vectors.json", docx_vectors)

    # =========================
    # Step 3: CRUD Operations inside Pinecone
    # =========================
    query = "What is the definition of Book?"
    search_results = vector_store.similarity_search(query, k=2)

    # READ
    print("\n Query Results:")
    for res in search_results:
        print(f" - ID: {res.metadata.get('id')} | Text: {res.page_content[:60]}...")

    # UPDATE
    if search_results:
        first_doc = search_results[0]
        updated_text = "This is the updated  definition of Book."
        new_vector = embeddings.embed_query(updated_text)

        index.upsert([
            {
                "id": first_doc.metadata["id"],
                "values": new_vector,
                "metadata": {"id": first_doc.metadata["id"], "source": "manual_update"}
            }
        ], namespace="default")

        print(f"\n Updated document with ID {first_doc.metadata['id']}")

    # DELETE
    if len(search_results) > 1:
        second_doc = search_results[1]
        index.delete(ids=[second_doc.metadata["id"]], namespace="default")
        print(f" Deleted document with ID {second_doc.metadata['id']}")
