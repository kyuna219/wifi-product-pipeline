# scripts/gdrive_upload.py
import os
import json
import sys
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_service_from_sa_json(sa_json_path):
    creds = service_account.Credentials.from_service_account_file(sa_json_path, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return service

def find_folder(service, parent_id, folder_name):
    # search for folder with given name under parent_id (supports drives)
    q = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and '{parent_id}' in parents and trashed=false"
    resp = service.files().list(q=q, fields="files(id, name)").execute()
    items = resp.get('files', [])
    if items:
        return items[0]['id']
    return None

def create_folder(service, parent_id, folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_file(service, local_path, parent_id, drive_filename, mime_type=None):
    media = MediaFileUpload(local_path, mimetype=mime_type or None, resumable=True)
    file_metadata = {
        'name': drive_filename,
        'parents': [parent_id]
    }
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def main():
    # args: parent_id local_file_path year_folder_name drive_file_name mime_type
    if len(sys.argv) < 5:
        print("Usage: python gdrive_upload.py <parent_id> <local_file_path> <year_folder_name> <drive_file_name> [mime_type]")
        sys.exit(1)

    parent_id = sys.argv[1]
    local_file = sys.argv[2]
    year_folder = sys.argv[3]
    drive_file_name = sys.argv[4]
    mime_type = sys.argv[5] if len(sys.argv) > 5 else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    sa_json_path = os.environ.get("GDRIVE_SA_JSON_PATH")
    if not sa_json_path or not os.path.exists(sa_json_path):
        print("Service account JSON not found. Ensure GDRIVE_SA_JSON_PATH is set and file exists.")
        sys.exit(1)

    service = get_service_from_sa_json(sa_json_path)

    # 1) find or create year folder under parent
    folder_id = find_folder(service, parent_id, year_folder)
    if folder_id:
        print(f"Found existing folder: {year_folder} -> {folder_id}")
    else:
        print(f"Creating folder: {year_folder} under parent {parent_id}")
        folder_id = create_folder(service, parent_id, year_folder)
        print(f"Created folder id: {folder_id}")

    # 2) upload file into folder
    if not Path(local_file).exists():
        print(f"Local file not found: {local_file}")
        sys.exit(1)

    uploaded_id = upload_file(service, local_file, folder_id, drive_file_name, mime_type)
    print(f"Uploaded file id: {uploaded_id}")

if __name__ == "__main__":
    main()
