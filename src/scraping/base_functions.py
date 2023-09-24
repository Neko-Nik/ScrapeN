import os
import zipfile
import shutil
import hashlib

def zip_folder_and_verify(folder_path):
    # Check if the folder exists
    if not os.path.exists(folder_path):
        return None

    # Create a zip file with the same name as the folder
    zip_filename = f"{folder_path}.zip"
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname=arcname)

    # Calculate the hash of the zip file for integrity verification
    hash_md5 = hashlib.md5()
    with open(zip_filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    zip_hash = hash_md5.hexdigest()

    # Remove the original folder after creating the zip file
    if os.path.exists(zip_filename):
        shutil.rmtree(folder_path)

    return zip_filename, zip_hash

