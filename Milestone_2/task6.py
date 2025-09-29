import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


# ---------------- CONFIG ----------------
INDEX_NAME = "legal-chatbot"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Embedding model
    embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

    # Connect to Pinecone vectorstore
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embedding
    )
    print("✅ Connected to Pinecone vectorstore successfully")

    # Create retriever
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    print("\n🔎 Interactive Legal Search Tool")
    print("Type your query (or 'exit' to quit)\n")

    while True:
        query = input(" Enter Your Query: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("👋 Exiting search tool. Goodbye!")
            break

        try:
            results = retriever.invoke(query)

            print(f"\nTop {len(results)} results for: {query}\n")
            for i, doc in enumerate(results, start=1):
                print(f"Result {i}:\n{doc.page_content[:1000]}\n{'-'*80}\n")
        except Exception as e:
            print(f"❌ Error retrieving results: {e}")
