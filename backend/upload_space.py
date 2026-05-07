"""
upload_space.py — Chay trong thu muc hotelsense_project/backend
    python upload_space.py
"""
from huggingface_hub import HfApi

TOKEN = input("Nhap HF token cua ban: ").strip()

api = HfApi(token=TOKEN)

print("Dang upload backend len HF Space...")
api.upload_folder(
    folder_path = ".",
    repo_id     = "ntdat232205/hotel-absa-api",
    repo_type   = "space",
    ignore_patterns = ["__pycache__", "*.pyc", ".env", "*.db", "hf_cache"],
)
print("Upload xong!")
