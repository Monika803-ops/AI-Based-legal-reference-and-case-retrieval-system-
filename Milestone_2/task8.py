import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain.chains import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from system_template import SYSTEM_TEMPLATE

# ---------------- CONFIG ----------------
INDEX_NAME = "legal-chatbot"

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# ---------------- RAG CHAIN ----------------
def create_rag_chain():
    print("Loading RAG chain resources...")

    # Setup embeddings and LLM
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        temperature=0.5,
        api_key=OPENAI_API_KEY
    )

    # Connect to Pinecone vectorstore
    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings
    )
    print("✅ Connected to Pinecone vectorstore successfully")

    # Retriever (top 5 chunks)
    retriever = vectorstore.as_retriever(k=5)
    print("✅ Created retriever with k=5")

    # History-aware rephrase prompt
    rephrase_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a concise, standalone search query to fetch relevant documents from the vector store.")
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, rephrase_prompt
    )

    # Final QA prompt with system template + retrieved context
    final_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE + "\n\n**Context from retrieved documents:**\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])

    # Create document chain
    question_answer_chain = create_stuff_documents_chain(llm, final_prompt)

    # Create retrieval-augmented generation (RAG) chain
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    print("✅ RAG chain loaded successfully.")
    return rag_chain

# ---------------- INTERACTIVE LEGAL SEARCH TOOL ----------------
if __name__ == "__main__":
    rag_chain = create_rag_chain()
    print("\n🔎 Interactive Legal RAG Search Tool")
    print("Type your query (or 'exit' to quit)\n")

    chat_history = []

    while True:
        query = input(" Enter Your Query: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("👋 Exiting search tool. Goodbye!")
            break

        try:
            # Pass query as dict with chat_history
            response = rag_chain.invoke({"input": query, "chat_history": chat_history})

            # Extract the answer text cleanly
            if isinstance(response, dict):
                answer_text = response.get("answer") or response.get("output_text") or str(response)
            else:
                answer_text = str(response)

            # Print formatted response
            print("\n" + answer_text + "\n")

            # Append user and assistant messages to history
            chat_history.append({"role": "user", "content": query})
            chat_history.append({"role": "assistant", "content": answer_text})

        except Exception as e:
            print(f"❌ Error retrieving results: {e}")
