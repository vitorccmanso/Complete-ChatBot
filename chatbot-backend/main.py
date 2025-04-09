from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
from dotenv import load_dotenv
from utils.save_docs import save_docs_to_vectordb
from utils.prepare_vectordb import list_documents_from_vectorstore, delete_document_from_vectorstore, DOCS_PATH, VECTORSTORE_PATH
from utils.chatbot import chat
from utils.save_chat import save_chat_history_json, load_chat_history_json
from utils.session_state import (
    initialize_directories,
    initialize_vectorstore,
    get_existing_chat_sessions,
    get_new_chat_name
)
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    session_key: str
    query: str
    enable_web_search: bool = False
    enable_rag: bool = True  # Default to using RAG if available
    search_types: List[str] = ["web"]  # Default to web search type

@app.on_event("startup")
async def startup_event():
    initialize_directories()

@app.post("/upload")
async def upload_docs(pdfs: list[UploadFile] = File(...)):
    try:
        # Check if docs directory exists and create if not
        if not os.path.exists(DOCS_PATH):
            os.makedirs(DOCS_PATH, exist_ok=True)
            
        # Get list of existing documents
        upload_docs = os.listdir(DOCS_PATH)
        
        # Save uploaded documents to vectorstore
        save_docs_to_vectordb(pdfs, upload_docs)
        
        return {"status": "success", "message": "Documents uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create_chat")
async def create_chat():
    session_key = get_new_chat_name()
    chat_file = f"chat_sessions/{session_key}.json"
    if not os.path.exists(chat_file):
        with open(chat_file, "w") as f:
            json.dump([], f)
    return {"status": "success", "session_key": session_key, "message": "Chat session created successfully"}

@app.post("/chat")
async def chat_with_pdf(chat_request: ChatRequest):
    session_key = chat_request.session_key
    user_query = chat_request.query
    enable_web_search = chat_request.enable_web_search
    enable_rag = chat_request.enable_rag
    search_types = chat_request.search_types
    chat_file = f"chat_sessions/{session_key}.json"

    # Load chat history
    chat_history = load_chat_history_json(chat_file)

    # Initialize vectorstore if it exists
    vectordb = None
    if os.path.exists(VECTORSTORE_PATH):
        try:
            vectordb, _ = initialize_vectorstore()
        except Exception as e:
            print(f"Error initializing vectorstore: {str(e)}")
            # Continue without vectorstore if there's an error

    # Process the chat request with the new parameters
    response, document_info, web_info = chat(
        chat_history=chat_history,
        vectordb=vectordb,
        user_query=user_query,
        web_results=None,  # Let the chat function handle web search
        use_rag=enable_rag,
        use_web_search=enable_web_search,
        search_types=search_types
    )

    # Save updated chat history
    save_chat_history_json(chat_history, chat_file)
    
    # Add has_documents flag to indicate if documents are available
    has_documents = os.path.exists(VECTORSTORE_PATH) and vectordb is not None
    
    return {
        "response": response, 
        "document_info": document_info, 
        "web_info": web_info,
        "has_documents": has_documents
    }

@app.post("/clear_chat")
async def clear_chat(session_key: str):
    chat_file = f"chat_sessions/{session_key}.json"
    if os.path.exists(chat_file):
        with open(chat_file, "w") as f:
            # Write an empty list to the file to clear it
            json.dump([], f)
    return {"status": "success", "message": "Chat cleared successfully"}

@app.post("/delete_chat")
async def delete_chat(session_key: str):
    chat_file = f"chat_sessions/{session_key}.json"
    if os.path.exists(chat_file):
        os.remove(chat_file)
    return {"status": "success", "message": "Chat deleted successfully"}

@app.get("/chat_history")
async def get_chat_history(session_key: str):
    chat_file = f"chat_sessions/{session_key}.json"
    if os.path.exists(chat_file):
        with open(chat_file, "r") as f:
            history = json.load(f)
        return {"status": "success", "history": history}
    else:
        raise HTTPException(status_code=404, detail="Chat session not found")

@app.get("/list_chats")
async def list_chats():
    chat_sessions = get_existing_chat_sessions()
    return {"status": "success", "chat_sessions": chat_sessions}

@app.get("/list_vectorstore_docs")
async def list_vectorstore_docs():
    try:
        # Check if vectorstore exists
        has_documents = os.path.exists(VECTORSTORE_PATH)
        
        if has_documents:
            # Get documents from metadata file (much faster)
            documents = list_documents_from_vectorstore()
            return {
                "status": "success", 
                "documents": documents,
                "has_documents": has_documents
            }
        else:
            return {
                "status": "success",
                "documents": [],
                "has_documents": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete_document")
async def delete_document(filename: str):
    try:
        # Delete document from vectorstore and metadata
        success = delete_document_from_vectorstore(filename)
                
        return {
            "status": "success" if success else "error",
            "message": "Document deleted successfully" if success else "Document not found or could not be deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)