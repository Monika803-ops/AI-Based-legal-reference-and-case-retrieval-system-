import os
import json
from pathlib import Path

# LangChain loaders & tools
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    TextLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter



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
   
    json_data = [
        {"text": chunk.page_content, "metadata": chunk.metadata}
        for chunk in chunks
    ]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    base_dir = Path(__file__).parent

    input_folder = base_dir.parent / "data"
    output_folder = base_dir.parent / "output"
    output_folder.mkdir(exist_ok=True)

    if not input_folder.exists():
        print(f" Data folder not found: {input_folder}")
    else:
        for file in input_folder.iterdir():
            if file.is_file():
                try:
                    print(f"Processing: {file.name}")

                    
                    docs = load_document(file)

                   
                    chunks = create_chunks(docs, chunk_size=2000, chunk_overlap=200)

                   
                    output_file = output_folder / f"{file.stem}_chunks.json"
                    save_chunks_to_json(chunks, output_file)

                    print(f" Saved {len(chunks)} chunks → {output_file}")
                except Exception as e:
                    print(f"Error processing {file.name}: {e}")
