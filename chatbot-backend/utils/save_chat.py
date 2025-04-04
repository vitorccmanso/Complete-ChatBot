import json
import os
from langchain_core.messages import AIMessage, HumanMessage
from datetime import datetime

def save_chat_history_json(chat_history, file_path):
    """
    Save chat history to a JSON file.

    Parameters:
    - chat_history (list): List of chat messages.
    - file_path (str): Path to the JSON file where chat history will be saved.
    """
    with open(file_path, "w") as f:
        json_data = [message.dict() for message in chat_history]
        json.dump(json_data, f)

def load_chat_history_json(file_path):
    """
    Load chat history from a JSON file.

    Parameters:
    - file_path (str): Path to the JSON file from which chat history will be loaded.

    Returns:
    - messages (list): List of chat messages.
    """
    if not os.path.exists(file_path):
        return []  # Return an empty list if the file does not exist

    with open(file_path, "r") as f:
        json_data = json.load(f)
        messages = [
            HumanMessage(**message) if message["type"] == "human" else AIMessage(**message)
            for message in json_data
        ]
        return messages

def get_timestamp():
    """
    Get the current timestamp in a specific format.

    Returns:
    - str: Current timestamp formatted as "dd-mm-yyyy".
    """
    return datetime.now().strftime("%d-%m-%Y")