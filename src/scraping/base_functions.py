from src.utils.base.libraries import logging, os, zipfile, shutil, hashlib


def clean_job_data(job_data: list | dict) -> list | dict:
    if isinstance(job_data, list):
        new_list = []
        for each_job in job_data:
            new_list.append({
                "job_id": each_job["job_uid"].split("|")[1],
                "name": each_job["job_name"],
                "description": each_job["job_description"],
                "status": each_job["status"],
                "created_at": each_job["created_at"],
                "zip_file_url": each_job["zip_file_url"]
            })
        job_data = new_list

    if isinstance(job_data, dict):
        job_data = {
            "job_id": job_data["job_uid"].split("|")[1],
            "name": job_data["job_name"],
            "description": job_data["job_description"],
            "status": job_data["status"],
            "created_at": job_data["created_at"],
            "zip_file_url": job_data["zip_file_url"]
        }
    return job_data


def zip_folder_and_verify(folder_path):
    # Check if the folder exists
    if not os.path.exists(folder_path):
        logging.error(f"Folder {folder_path} doesn't exist")
        return None, None

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

