from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
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

@app.on_event("startup")
async def startup_event():
    initialize_directories()

@app.post("/upload")
async def upload_docs(pdfs: list[UploadFile] = File(...)):
    upload_docs = os.listdir(DOCS_PATH)
    try:
        print("try")
        print(upload_docs)
        save_docs_to_vectordb(pdfs, upload_docs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "message": "Documents uploaded successfully"}

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
    chat_file = f"chat_sessions/{session_key}.json"

    # Load chat history
    chat_history = load_chat_history_json(chat_file)

    # Initialize vectorstore
    if os.path.exists(VECTORSTORE_PATH):
        vectordb, _ = initialize_vectorstore()
    else:
        vectordb = None

    # Get response from chatbot
    response, document_info = chat(chat_history, vectordb, user_query)

    # Save updated chat history
    save_chat_history_json(chat_history, chat_file)
    
    return {"response": response, "document_info": document_info}

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
        # Get documents from metadata file (much faster)
        documents = list_documents_from_vectorstore()
        return {
            "status": "success", 
            "documents": documents
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