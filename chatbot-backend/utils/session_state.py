import os
from utils.prepare_vectordb import get_vectorstore, DOCS_PATH
from utils.save_chat import get_timestamp, load_chat_history_json, save_chat_history_json

def initialize_directories():
    """
    Ensure all necessary directories exist.
    """
    os.makedirs(DOCS_PATH, exist_ok=True)
    os.makedirs("chat_sessions", exist_ok=True)

def initialize_vectorstore():
    """
    Initialize the vectorstore from uploaded documents.
    """
    upload_docs = os.listdir(DOCS_PATH)
    vectordb = get_vectorstore(upload_docs, use_existing=True)
    return vectordb, upload_docs

def initialize_chat_session(session_key=None):
    """
    Initialize or load a chat session.

    Parameters:
    - session_key (str, optional): The session key for the chat. If None, a new session is created.

    Returns:
    - session_key (str): The session key for the chat.
    - chat_history (list): The chat history for the session.
    """
    chat_sessions = get_existing_chat_sessions()

    if session_key is None:
        if chat_sessions:
            # Load the most recent chat session (sorted by modification time)
            most_recent_session = sorted(
                chat_sessions,
                key=lambda x: os.path.getmtime(os.path.join("chat_sessions", x)),
                reverse=True
            )[0]
            session_key = most_recent_session.split('.')[0]
        else:
            # Create new session if none exist
            session_key = get_new_chat_name()

    # Load existing messages if available
    chat_file = f"chat_sessions/{session_key}.json"
    if os.path.exists(chat_file):
        chat_history = load_chat_history_json(chat_file)
    else:
        chat_history = []
        save_chat_history_json(chat_history, chat_file)

    return session_key, chat_history

def get_existing_chat_sessions():
    """
    Returns a list of existing chat session files sorted by creation time (newest first).
    """
    if os.path.exists("chat_sessions"):
        # Get all chat files
        chat_files = [f for f in os.listdir("chat_sessions") if f.endswith('.json')]
        
        # Sort by creation/modification time (newest first)
        sorted_chats = sorted(
            chat_files,
            key=lambda x: os.path.getmtime(os.path.join("chat_sessions", x)),
            reverse=True  # Newest first
        )
        
        return sorted_chats
    return []

def get_new_chat_name():
    """
    Generate a new chat name with timestamp and counter, resetting counter for new dates.

    Returns:
    - str: The new chat session name.
    """
    base_timestamp = get_timestamp()
    
    # Get the chat sessions without sorting, as we're looking for the counter
    existing_chats = []
    if os.path.exists("chat_sessions"):
        existing_chats = [f for f in os.listdir("chat_sessions") if f.endswith('.json')]

    # Filter chats with today's date
    today_chats = [chat for chat in existing_chats if base_timestamp in chat]

    if not today_chats:
        return f"{base_timestamp}-1"

    # Get the highest counter for today's chats
    max_count = 0
    for chat_name in today_chats:
        try:
            # Extract counter from format DD-MM-YYYY-counter.json
            current_count = int(chat_name.split('-')[-1].split('.')[0])
            max_count = max(max_count, current_count)
        except (ValueError, IndexError):
            continue

    return f"{base_timestamp}-{max_count + 1}"