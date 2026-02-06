import boto3
from pathlib import Path
import mimetypes
import os

DEFAULT_BUCKET = "zappa-m3secjk20"
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "snapCopyFunction", "web", "templates")

def upload_file_to_s3(file_path, bucket_name):
    """Upload a file to an S3 bucket and make it publicly readable"""
    s3 = boto3.client('s3')
    file_name = Path(file_path).name
    content_type = mimetypes.guess_type(file_name)[0] or 'text/html'
    
    try:
        s3.upload_file(
            file_path,
            bucket_name,
            file_name,
            ExtraArgs={
                'ContentType': content_type,
                'ACL': 'public-read'
            }
        )
        print(f"Successfully uploaded {file_name} to {bucket_name}")
        print(f"Public URL: https://{bucket_name}.s3.amazonaws.com/{file_name}")
    except Exception as e:
        print(f"Error uploading {file_name}: {e}")

def upload_all_html_files(bucket_name):
    """Upload all HTML files from templates directory to S3"""
    html_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html')]
    
    if not html_files:
        print("No HTML files found in templates directory")
        return
    
    print(f"Found {len(html_files)} HTML files in templates directory")
    for html_file in html_files:
        file_path = os.path.join(TEMPLATES_DIR, html_file)
        upload_file_to_s3(file_path, bucket_name)

if __name__ == "__main__":
    bucket = input(f"Enter bucket name [{DEFAULT_BUCKET}]: ") or DEFAULT_BUCKET
    choice = input("Upload single file (1) or all templates (2)? [1]: ") or "1"
    
    if choice == "1":
        file_path = input("Enter file path to upload: ")
        upload_file_to_s3(file_path, bucket)
    else:
        upload_all_html_files(bucket)