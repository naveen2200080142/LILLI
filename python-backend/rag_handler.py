import os
import requests
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings
from typing import List
from storage import load_history

# Configuration
GEMINI_API_KEY = os.environ.get("API_KEY")
KNOWLEDGE_BASE_PATH = "basic_data.txt"  # Initial knowledge base file
VECTOR_STORE_PATH = "vectorstore"
HF_TOKEN = "your-hf-token-here"  # Optional, replace if needed

# Embedding wrapper
class SentenceTransformerWrapper(Embeddings):
    def __init__(self, model_name: str, token: str = None):
        self.model = SentenceTransformer(model_name, token=token)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_tensor=False).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode([text], convert_to_tensor=False)[0].tolist()

embeddings_model = SentenceTransformerWrapper("all-MiniLM-L6-v2", token=HF_TOKEN)
vectorstore = None
BASE_CONTEXT = "JARVIS is an AI assistant inspired by Tony Stark’s companion, designed to help users with tasks."

def initialize_vector_store():
    global vectorstore
    if vectorstore is not None:
        return vectorstore

    try:
        if os.path.exists(VECTOR_STORE_PATH):
            vectorstore = FAISS.load_local(VECTOR_STORE_PATH, embeddings_model, allow_dangerous_deserialization=True)
        else:
            docs = load_and_split_documents(KNOWLEDGE_BASE_PATH)
            if not docs:
                raise ValueError("No documents loaded.")
            vectorstore = FAISS.from_texts(docs, embeddings_model)
            vectorstore.save_local(VECTOR_STORE_PATH)
        return vectorstore
    except Exception as e:
        logging.error(f"Vector store error: {str(e)}")
        return None

def load_and_split_documents(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        return splitter.split_text(text)
    except Exception as e:
        logging.error(f"Error loading documents: {str(e)}")
        return []

def update_rag_context(new_text):
    global vectorstore
    if vectorstore is None:
        vectorstore = initialize_vector_store()
    docs = [new_text]  # Treat new text as a single document
    vectorstore.add_texts(docs)
    vectorstore.save_local(VECTOR_STORE_PATH)
    logging.info(f"RAG context updated with: {new_text[:50]}...")

def get_session_chat_history(session_id):
    history = load_history()
    # Filter by session_id if implemented; for now, return all
    return [{"question": entry["user_input"], "response": entry["assistant_response"]} for entry in history[-10:]]

def call_gemini_api_with_history(session_id, query, context):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}

    chat_history = get_session_chat_history(session_id)
    history_text = "\nHistory:\n" + "\n".join([f"Q: {entry['question']}\nA: {entry['response']}" for entry in chat_history]) if chat_history else ""

    prompt = f"You are JARVIS, a helpful AI. Answer in 20-30 words.\nContext: {BASE_CONTEXT} {context}\n{history_text}\nQuery: {query}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, headers=headers, params=params, json=payload)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(f"Gemini API error: {str(e)}")
        return "JARVIS: Apologies, sir, an error occurred."

def get_response_from_rag_with_history(user_id, session_id, query):
    global vectorstore
    if vectorstore is None:
        vectorstore = initialize_vector_store()
        if vectorstore is None:
            return "JARVIS: Error loading knowledge base, sir."

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    docs = retriever.invoke(query)
    context = " ".join([doc.page_content for doc in docs])
    return call_gemini_api_with_history(session_id, query, context)