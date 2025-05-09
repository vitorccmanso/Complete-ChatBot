# Document-Based Chat Application: AI Chatbot with Document Management, Markdown and LaTeX Support

A powerful chat application that allows users to have intelligent conversations with their documents. Built with FastAPI, React, Langchain, ChromaDB, and OpenAI embeddings, this application enables natural language interactions with PDF files through an elegant, user-friendly interface. The results from the images bellow are using gpt-4o-mini.

![Chat Application Screenshot 1](Images/chat_usage1.png)

![Chat Application Screenshot 2](Images/chat_usage2.png)

![Chat Application Screenshot 3](Images/chat_usage3.png)

## Features

### Document Management
- **Document Upload**: Easily upload PDF, DOCX, TXT, HTML documents through the interface
- **Document Persistence**: Uploaded documents remain available between sessions
- **Document Deletion**: Remove documents from the system with a simple click
- **Document Listing**: View all available documents in the side panel

### Intelligent Chat
- **Contextualized Responses**: The AI analyzes documents to provide accurate answers
- **Retrieval Augmented Generation (RAG)**: Toggle RAG on/off to control whether the AI uses documents
- **Agentic RAG Implementation**: Two-stage approach with a specialized agent that analyze queries, identify distinct topics, and select appropriate tools for each topic
- **Smart Context Retrieval**: Dynamically chooses between document retrieval and web search based on query analysis and available tools
- **Source References**: View document (including page numbers) and web search references
- **Structured Responses**: Smart formatting based on question complexity (simple answers for simple questions, structured sections for complex ones), with automatic language adaptation for section headers
- **Chat Sessions**: Create and manage multiple chat sessions
- **Conversation History**: Full chat history is preserved within each session
- **Model Selection**: Choose between different OpenAI models, including gpt-4o-mini as default
- **Topic Analysis**: Automatically breaks down complex queries into distinct topics for more accurate responses

### Image Processing
- **Image Upload**: Support for uploading images directly in the chat interface
- **Image Pasting**: Paste images from clipboard directly into chat
- **Image Drag-and-Drop**: Drag and drop images into the chat area
- **Multi-Image Support**: Upload multiple images with a single message
- **Visual Context**: AI uses image content to provide more relevant responses

### Web Search Integration
- **Multi-Source Knowledge**: Access information from both uploaded documents and the web
- **Search Type Selection**: Choose between web, academic, and social search types
- **Source Attribution**: Clear distinction between document information and web search results
- **Intelligent Query Optimization**: Automatic reformulation of search queries based on context

### Rich Text Support
- **Markdown Rendering**: Format messages with standard markdown syntax
- **Code Highlighting**: Beautiful syntax highlighting for code blocks with copy functionality
- **LaTeX Support**: Render mathematical formulas using LaTeX notation
- **Source References**: View document references for AI-generated responses
- **Structured Responses**: Smart formatting based on question complexity, with section headers for complex topics

### User Experience
- **Responsive Design**: Works seamlessly across different screen sizes
- **Dark Mode**: Easy on the eyes for extended usage
- **Real-time Feedback**: Status indicators for operations like uploads and deletions
- **Scroll Management**: Convenient scroll-to-bottom button for long conversations
- **Image Preview**: View thumbnails of images before sending
- **Search Type Toggles**: Simple checkbox interface for selecting search types

### In Development
- **Isolated Vector Databases**: Separate vector databases for each chat session
- **Better chunking strategy**:  Allow for better answers by improving the retrieved content from the vectordb
- **Chat Renaming**: Ability to rename chat sessions for better organization

## Architecture

The application is structured as a client-server system:

### Backend (FastAPI)
- **Document Processing**: Extracts text from PDF, DOCX, TXT, HTML files and creates vector embeddings
- **Vector Database**: Stores document embeddings for semantic search using ChromaDB
- **Chat Management**: Handles chat sessions, history, and AI interactions
- **File Management**: Manages document storage and retrieval
- **Web Search**: Interfaces with Tavily API for retrieving web content
- **Image Processing**: Handles image uploads and multimodal interactions
- **Topic Analysis**: Smart query breakdown for improved context retrieval

### Frontend (React)
- **Context Providers**: Manages global state for chat and documents
- **Component Structure**: Modular components for each section of the interface built with Next.js
- **Hooks and Effects**: Manages side effects and component lifecycle
- **Chat Rendering**: Specialized components for rendering different message types
- **Search Controls**: UI for selecting and configuring search options
- **Image Handling**: Components for image uploading, preview, and display
- **UI Improvements**: Syntax highlighting, and responsive design elements

### Data Flow
1. User uploads files to the system
2. Files are processed into text chunks and vectorized
3. When a question is asked, the system finds relevant document sections
4. If web search is enabled, the system also retrieves relevant web content
5. If images are uploaded, they are processed and added to the context
6. The AI model combines the retrieved context with the chat history and image content
7. The model generates a response that's displayed to the user with source attribution

## Technology Stack

- **Backend**:
  - FastAPI: High-performance Python web framework
  - Langchain: Framework for LLM application development
  - ChromaDB: Vector database for document embeddings
  - OpenAI Embeddings: For creating vector representations of text
  - PyPDFLoader, Docx2txtLoader, TextLoader and UnstructuredHTMLLoader: Text extraction utilities
  - Tavily API: For retrieving web search results
  - OpenAI multimodal models: For processing text and images together

- **Frontend**:
  - React: UI library for building the interface
  - Next.js: React framework for production
  - Chakra UI: Component library for styling
  - React Markdown: For rendering markdown content
  - KaTeX: For rendering mathematical formulas
  - React Syntax Highlighter: For code block formatting
  - React Icons: Icon library for UI elements

## Usage Guide

### Uploading Documents
1. Click the "+" button in the chat input area
2. Select one or more PDF, DOCX, TXT, or HTML files from your computer
3. Files will be processed and appear in the documents panel

### Managing Documents
1. Click the documents icon in the top-right to view uploaded files
2. Click the "X" on any document card to delete it
3. When a document is deleted, it is removed from both the file system and the vector database

### Using Images in Chat
1. Paste images from clipboard (Ctrl+V)
2. Preview images before sending and remove unwanted ones
3. Type your question along with the images for context

### Model Selection
1. Use the model dropdown menu to select your preferred AI model
2. gpt-4o-mini is set as the default for a balance of speed and quality
3. More powerful models like gpt-4o are available for complex queries

### Web Search
1. Toggle the "Web Search" option in the chat interface to enable online search
2. Select your preferred search type: Web (general), Academic (scholarly sources), or Social (discussions)
3. The AI will use both document context and web search results when answering your questions
4. Sources will be clearly indicated in the response

### Chat Interactions
1. Start chatting immediately - no document upload required to begin
2. Type your question in the chat input and press Enter or click the send button
3. Use the RAG toggle to control whether the AI uses your documents for answers
4. For mathematical formulas, use LaTeX syntax: `$E = mc^2$` for inline math or `$$E = mc^2$$` for block math
5. Use markdown for formatting: **bold**, *italic*, `code`, etc.

### Chat Sessions
1. Use the sidebar to create new chat sessions
2. Switch between different conversations while maintaining context
3. Delete conversations you no longer need
4. Chat renaming functionality will be implemented in a future update

## Project Structure

```
├── chatbot-backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── utils/
|   |   ├── __init__.py
│   │   ├── chatbot.py          # AI chat logic
│   │   ├── web_search.py       # Web search integration
│   │   ├── prepare_vectordb.py # Document embedding and vector operations
│   │   ├── save_chat.py        # Chat history persistence
│   │   ├── save_docs.py        # Document storage utilities
│   │   └── session_state.py    # Session management
│   └── chat_sessions/          # Stored chat sessions
├── chatbot-frontend/
│   ├── components/
│   │   ├── ChatArea.js         # Main chat interface
│   │   └── Sidebar.js          # Chat session management
│   │
│   ├── context/
│   │   └── ChatContext.js      # Global state management
│   └── ...                     # Node.js app configuration
├── docs/                       # Uploaded PDF files
├── Vector_DB - Documents/      # ChromaDB vector database
└── README.md                   # This file
``` 