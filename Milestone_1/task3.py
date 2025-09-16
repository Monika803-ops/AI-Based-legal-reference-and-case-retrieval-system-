import os
import json
from pathlib import Path
from tqdm import tqdm  # progress bar

# LangChain loaders & tools
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    TextLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter


from langchain_huggingface import HuggingFaceEmbeddings



def load_document(file_path: Path):
    """
    Load a document based on file extension.
    Supports: PDF, DOCX/DOC, CSV, HTML, TXT.
    """
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(str(file_path))
    elif ext in [".docx", ".doc"]:
        loader = Docx2txtLoader(str(file_path))
    elif ext == ".csv":
        loader = CSVLoader(str(file_path))
    elif ext in [".html", ".htm"]:
        loader = UnstructuredHTMLLoader(str(file_path))
    elif ext == ".txt":
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader.load()


def create_chunks(documents, chunk_size=2000, chunk_overlap=200):
    """
    Split documents into chunks using RecursiveCharacterTextSplitter.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return splitter.split_documents(documents)


def save_chunks_to_json(chunks, output_file: Path):
    """
    Save raw text chunks to JSON.
    """
    json_data = [
        {"text": chunk.page_content, "metadata": chunk.metadata}
        for chunk in chunks
    ]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)


def generate_embeddings(chunks, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """
    Generate embeddings for document chunks using HuggingFace sentence transformer.
    """
    embedding_model = HuggingFaceEmbeddings(model_name=model_name)
    data = []

    for i, chunk in enumerate(tqdm(chunks, desc="Embedding Chunks", unit="chunk")):
        vector = embedding_model.embed_query(chunk.page_content)
        data.append({
            "id": i,
            "text": chunk.page_content,
            "embedding": vector
        })

    return data


def save_embeddings_to_json(embeddings, output_file: Path):
    """
    Save embeddings to JSON file.
    """
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embeddings, f, ensure_ascii=False, indent=4)


# ---------- Main Execution ---------- #
if __name__ == "__main__":
    base_dir = Path(__file__).parent

    # Input documents folder
    input_folder = base_dir.parent / "data"

    # Output folders
    output_folder = base_dir.parent / "output"
    embedding_folder = base_dir.parent / "output_embeddings"
    output_folder.mkdir(exist_ok=True)
    embedding_folder.mkdir(exist_ok=True)

    if not input_folder.exists():
        print(f" Data folder not found: {input_folder}")
    else:
        for file in input_folder.iterdir():
            if file.is_file():
                try:
                    print(f"\n Processing: {file.name}")

                    # --- Step 1: Load document ---
                    docs = load_document(file)

                    # --- Step 2: Split into chunks ---
                    chunks = create_chunks(docs, chunk_size=2000, chunk_overlap=200)

                    # Save chunks
                    chunk_file = output_folder / f"{file.stem}_chunks.json"
                    save_chunks_to_json(chunks, chunk_file)
                    print(f"  Saved {len(chunks)} chunks → {chunk_file}")

                    # --- Step 3: Generate embeddings ---
                    embeddings = generate_embeddings(chunks)

                    # Save embeddings
                    embedding_file = embedding_folder / f"{file.stem}_embeddings.json"
                    save_embeddings_to_json(embeddings, embedding_file)
                    print(f"  Saved {len(embeddings)} embeddings → {embedding_file}")

                except Exception as e:
                    print(f" Error processing {file.name}: {e}")
