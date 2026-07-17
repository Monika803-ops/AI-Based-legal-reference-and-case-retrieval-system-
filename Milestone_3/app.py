import os
from dotenv import load_dotenv
import streamlit as st

# Import your auth module
from auth import *


# Import RAG chain functions
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatOpenAI(
        model="gpt-3.5-turbo-1106",
        temperature=0.5,
        api_key=OPENAI_API_KEY
    )

    vectorstore = PineconeVectorStore.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings
    )
    print("✅ Connected to Pinecone vectorstore successfully")

    retriever = vectorstore.as_retriever(k=5)
    print("✅ Created retriever with k=5")

    rephrase_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}"),
        ("user", "Given the above conversation, generate a concise, standalone search query to fetch relevant documents from the vector store.")
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, rephrase_prompt
    )

    final_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE + "\n\n**Context from retrieved documents:**\n{context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", "{input}")
    ])

    question_answer_chain = create_stuff_documents_chain(llm, final_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    print("✅ RAG chain loaded successfully.")
    return rag_chain

# ---------------- MAIN APP ----------------
def main():
    st.set_page_config(page_title="LegalBot", page_icon="⚖️", layout="wide")

    # Initialize database
    init_db()
   
    init_chat_table()


    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "page" not in st.session_state:
        st.session_state.page = "login"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Initialize RAG chain only after login
    if st.session_state.logged_in and "rag_chain" not in st.session_state:
        st.session_state.rag_chain = create_rag_chain()

    # ---------------- ROUTING ----------------
    if not st.session_state.logged_in:
        if st.session_state.page == "signup":
            signup_page()
        else:
            login_page()
    else:
        if st.session_state.page == "profile":
            profile_page()
        elif st.session_state.page == "edit_profile":
            edit_profile_page()
        elif st.session_state.page == "about":
            about_page()
        else:
            # Main chat page
            chat_page()

if __name__ == "__main__":
    main()

 

