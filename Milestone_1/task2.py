import os
import json
import re
from datasets import load_dataset
from langchain.schema import Document



def sentence_splitter(text: str):
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]



def load_hf_dataset(dataset_name="NahOR102/Indian-IPC-Laws", split="train"):
    dataset = load_dataset(dataset_name, split=split)
    docs = []

    for row in dataset:
        q, a = "", ""

        
        if "question" in row and "answer" in row:
            q, a = row["question"], row["answer"]

        elif "Q" in row and "A" in row:
            q, a = row["Q"], row["A"]

        
        elif "messages" in row:
            for msg in row["messages"]:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                if role == "user":
                    q = content
                elif role == "assistant":
                    a = content

        if not q and not a:
            continue

        # Split Q into sentences
        for sent in sentence_splitter(q):
            docs.append(Document(
                page_content=sent,
                metadata={"type": "question", "question": q, "answer": a}
            ))

        # Split A into sentences
        for sent in sentence_splitter(a):
            docs.append(Document(
                page_content=sent,
                metadata={"type": "answer", "question": q, "answer": a}
            ))

    return docs


# -------- Main ----------
if __name__ == "__main__":
    project_root = os.path.dirname(os.getcwd())
    output_folder = os.path.join(project_root, "output_json")
    os.makedirs(output_folder, exist_ok=True)

    
    hf_docs = load_hf_dataset()

    output = [
        {
            "sentence": d.page_content,
            "type": d.metadata["type"],  
            "question": d.metadata["question"],
            "answer": d.metadata["answer"]
        }
        for d in hf_docs
    ]

    output_file = os.path.join(output_folder, "ipc_laws_sentence_chunks.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f" Saved HuggingFace dataset into {output_file}")
