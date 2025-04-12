from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader, UnstructuredHTMLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import os
import json
import re
import unicodedata

# File paths
VECTORSTORE_PATH = "../Vector_DB - Documents"
DOCS_PATH = "../docs"
METADATA_FILE = "metadata.json"

def load_metadata():
    """Load metadata from JSON file."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save metadata to JSON file."""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f)

def get_document_loader(file_path):
    """Returns the appropriate document loader based on file extension."""
    file_extension = os.path.splitext(file_path)[1].lower()
    print(f"File extension: {file_extension}")
    print(f"File path: {file_path}")
    
    # Make sure the file path is absolute (this avoids relative path issues)
    #absolute_path = os.path.abspath(file_path)
    
    if file_extension == '.pdf':
        return PyPDFLoader(file_path)
    elif file_extension == '.docx':
        return Docx2txtLoader(file_path)
    elif file_extension == '.txt':
        return TextLoader(file_path, encoding='utf-8', autodetect_encoding=True)
    elif file_extension in ['.html', '.htm']:
        return UnstructuredHTMLLoader(file_path)
    else:
        # Default to PDF loader if extension not recognized
        # You could raise an exception here instead if preferred
        return PyPDFLoader(file_path)
def clean_text(text):
    """
    Clean and normalize text extracted from documents.
    """
    # Normalize unicode (accents, etc.)
    text = unicodedata.normalize("NFKC", text)
    
    # Replace multiple newlines with a single newline
    text = re.sub(r"\n\s*\n+", "\n", text)
    
    # Remove line breaks in the middle of sentences (join hyphenated words too)
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,;:!?)])', r'\1', text)
    text = re.sub(r'([({])\s+', r'\1', text)

    # Fix bullet points and numbered lists that got separated
    text = re.sub(r'\n• ', '\n\n• ', text)
    text = re.sub(r'\n(\d+\.) ', '\n\n\\1 ', text)

    # Remove repeated punctuation
    text = re.sub(r'([.,;:!?]){2,}', r'\1', text)

    # Collapse multiple spaces into one
    text = re.sub(r"\s+", " ", text)


    return text.strip()

def extract_document_text(files):
    """Extract text from various document types and store them."""
    docs = []
    for file in files:
        if hasattr(file, 'filename'):  # Check if it's an UploadFile object
            file_path = os.path.join(DOCS_PATH, file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())
        else:  # It's a filename
            file_path = os.path.join(DOCS_PATH, file)
        print(f"File path: {file_path}")
        # Use the appropriate loader based on file type
        loader = get_document_loader(file_path)
        raw_docs = loader.load()
        
        # Clean the text in each document
        for doc in raw_docs:
            doc.page_content = clean_text(doc.page_content)
            
        docs.extend(raw_docs)
    return docs

def get_text_chunks(docs):
    """Split text into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000, 
        chunk_overlap=400, 
        separators=["\n\n", "\n", ".", "?", "!", " ", ""])
    return text_splitter.split_documents(docs)

def get_vectorstore(files, use_existing=False):
    """Create or retrieve a vectorstore from document files."""
    load_dotenv()
    embedding = OpenAIEmbeddings()
    
    if use_existing and os.path.exists(VECTORSTORE_PATH):
        return Chroma(persist_directory=VECTORSTORE_PATH, embedding_function=embedding)

    docs = extract_document_text(files)
    chunks = get_text_chunks(docs)

    # Create vectorstore and save it
    vectordb = Chroma.from_documents(documents=chunks, embedding=embedding, persist_directory=VECTORSTORE_PATH)

    collection = vectordb._collection
    result = collection.get(include=["metadatas"])
    metadatas = result["metadatas"]

    # Update metadata.json with filenames and generated IDs
    metadata = load_metadata()
    for i, metadata_entry in enumerate(metadatas):
        source = metadata_entry.get("source", "")
        filename = os.path.basename(source)
        if filename:
            metadata[filename] = f"doc_{i}"

    save_metadata(metadata)

    return vectordb

def list_documents_from_vectorstore():
    """List all documents in the vectorstore from metadata.json."""
    metadata = load_metadata()
    return list(metadata.keys())  # Just return the filenames

def delete_document_from_vectorstore(filename):
    """Delete all chunks of a document from the vectorstore and update metadata."""
    load_dotenv()

    metadata = load_metadata()
    if filename not in metadata:
        return False  # File not found in metadata

    embedding = OpenAIEmbeddings()
    vectordb = Chroma(persist_directory=VECTORSTORE_PATH, embedding_function=embedding)
    collection = vectordb._collection

    # Only include metadatas — IDs come by default
    result = collection.get(include=["metadatas"])
    ids = result["ids"]
    metadatas = result["metadatas"]

    # Match all chunks that belong to the same file
    ids_to_delete = [doc_id for doc_id, metadata_entry in zip(ids, metadatas) if os.path.basename(metadata_entry.get("source", "")) == filename]

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
        vectordb.persist()

    # Delete the file from the system
    file_path = os.path.join(DOCS_PATH, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Update metadata
    del metadata[filename]
    save_metadata(metadata)

    return True