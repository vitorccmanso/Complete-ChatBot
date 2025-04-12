import os
from utils.prepare_vectordb import get_vectorstore

def save_docs_to_vectordb(files, upload_docs):
    """
    Save uploaded documents to the 'docs' folder and create or update the vectorstore.
    Supports PDF, DOCX, TXT, and HTML file formats.

    Parameters:
    - files (list): List of uploaded documents (FastAPI's UploadFile objects).
    - upload_docs (list): List of names of previously uploaded documents.
    """
    # Filter for new files that haven't been uploaded yet
    new_files = [file for file in files if file.filename not in upload_docs]
    new_files_names = [file.filename for file in new_files]
    print("arquivo")
    print(new_files_names)

    if new_files:
        # Iterate through the new files and save them to the docs folder
        for file in new_files:
            file_path = os.path.join("../docs", file.filename)
            with open(file_path, "wb") as f:
                f.write(file.file.read())

        # Create or update the vectorstore with the newly uploaded documents
        get_vectorstore(new_files_names)

        return {"status": "success", "message": f"Uploaded {len(new_files)} new documents."}
    else:
        return {"status": "no_new_files", "message": "No new documents to upload."}