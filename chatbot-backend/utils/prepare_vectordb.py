from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
import os
import json

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

def extract_pdf_text(pdfs):
    """Extract text from PDF documents and store them."""
    docs = []
    for pdf in pdfs:
        if hasattr(pdf, 'filename'):  # Check if it's an UploadFile object
            pdf_path = os.path.join(DOCS_PATH, pdf.filename)
            with open(pdf_path, "wb") as f:
                f.write(pdf.file.read())
        else:  # It's a filename
            pdf_path = os.path.join(DOCS_PATH, pdf)

        # Load text from the PDF and extend the list of documents
        docs.extend(PyPDFLoader(pdf_path).load())
    return docs

def get_text_chunks(docs):
    """Split text into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=800, separators=["\n\n", "\n", " ", ""])
    return text_splitter.split_documents(docs)

def get_vectorstore(pdfs, use_existing=False):
    """Create or retrieve a vectorstore from PDF documents."""
    load_dotenv()
    embedding = OpenAIEmbeddings()
    
    if use_existing and os.path.exists(VECTORSTORE_PATH):
        return Chroma(persist_directory=VECTORSTORE_PATH, embedding_function=embedding)

    docs = extract_pdf_text(pdfs)
    chunks = get_text_chunks(docs)

    # Create vectorstore and save it
    vectordb = Chroma.from_documents(documents=chunks, embedding=embedding, persist_directory=VECTORSTORE_PATH)

    collection = vectordb._collection
    result = collection.get(include=["metadatas"])  # Removed "ids"
    metadatas = result["metadatas"]

    # Update metadata.json with filenames and generated IDs
    metadata = load_metadata()
    for i, metadata_entry in enumerate(metadatas):
        source = metadata_entry.get("source", "")
        filename = os.path.basename(source)
        if filename:
            metadata[filename] = f"doc_{i}"  # Assign an index-based ID

    save_metadata(metadata)

    return vectordb

def list_documents_from_vectorstore():
    """List all documents in the vectorstore from metadata.json."""
    metadata = load_metadata()
    # embedding = OpenAIEmbeddings()
    # vectordb = Chroma(persist_directory=VECTORSTORE_PATH, embedding_function=embedding)
    # collection = vectordb._collection

    # # Only include metadatas — IDs come by default
    # result = collection.get(include=["metadatas"])
    # ids = result["ids"]
    # metadatas = result["metadatas"]
    # print(collection)
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
    ids_to_delete = [
        doc_id for doc_id, metadata_entry in zip(ids, metadatas)
        if os.path.basename(metadata_entry.get("source", "")) == filename
    ]

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