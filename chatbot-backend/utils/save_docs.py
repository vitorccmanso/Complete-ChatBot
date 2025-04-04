import os
from utils.prepare_vectordb import get_vectorstore

def save_docs_to_vectordb(pdf_docs, upload_docs):
    """
    Save uploaded PDF documents to the 'docs' folder and create or update the vectorstore.

    Parameters:
    - pdf_docs (list): List of uploaded PDF documents (FastAPI's UploadFile objects).
    - upload_docs (list): List of names of previously uploaded documents.
    """
    # Filter for new files that haven't been uploaded yet
    new_files = [pdf for pdf in pdf_docs if pdf.filename not in upload_docs]
    new_files_names = [pdf.filename for pdf in new_files]
    print("arquivo")
    print(new_files_names)

    if new_files:
        # Iterate through the new files and save them to the docs folder
        for pdf in new_files:
            pdf_path = os.path.join("../docs", pdf.filename)
            with open(pdf_path, "wb") as f:
                f.write(pdf.file.read())

        # Create or update the vectorstore with the newly uploaded documents
        get_vectorstore(new_files_names)

        return {"status": "success", "message": f"Uploaded {len(new_files)} new documents."}
    else:
        return {"status": "no_new_files", "message": "No new documents to upload."}