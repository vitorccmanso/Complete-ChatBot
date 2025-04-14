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
        json_data = []
        for message in chat_history:
            msg_dict = message.dict()
            
            # Handle multimodal content
            if isinstance(message.content, list) and message.type == "human":
                # Extract image data from multimodal content
                text_content = ""
                image_data_list = []
                
                for content_item in message.content:
                    if content_item.get("type") == "text":
                        text_content = content_item.get("text", "")
                    elif content_item.get("type") == "image_url":
                        image_url = content_item.get("image_url", {}).get("url")
                        if image_url:
                            image_data_list.append(image_url)
                
                # Store in a consistent format
                msg_dict["content"] = text_content
                if image_data_list:
                    msg_dict["image_data"] = image_data_list if len(image_data_list) > 1 else image_data_list[0]
            
            json_data.append(msg_dict)
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
        return []
        
    with open(file_path, "r") as f:
        json_data = json.load(f)
        messages = []
        for message in json_data:
            # Extract image data if it exists
            image_data = message.pop('image_data', None)
            
            if message["type"] == "human":
                if image_data:
                    # Normalize image_data to a list
                    image_data_list = image_data if isinstance(image_data, list) else [image_data]
                    # Create a message with multimodal content
                    content = [{"type": "text", "text": message["content"]}]
                    # Add each image
                    for img in image_data_list:
                        content.append({"type": "image_url", "image_url": {"url": img}})
                    msg = HumanMessage(content=content)
                else:
                    # Create a standard text message
                    msg = HumanMessage(content=message["content"])
            else:
                # Create an AI message
                msg = AIMessage(content=message["content"])
                
            messages.append(msg)
        return messages

def get_timestamp():
    """
    Get the current timestamp in a specific format.

    Returns:
    - str: Current timestamp formatted as "dd-mm-yyyy".
    """
    return datetime.now().strftime("%d-%m-%Y")