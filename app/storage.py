import boto3
from botocore.config import Config
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APP_KEY")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")
B2_ENDPOINT = os.getenv("B2_ENDPOINT")

def get_b2_client():
    return boto3.client(
        "s3",
        endpoint_url=B2_ENDPOINT,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APP_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-005"
    )

def upload_file(file_bytes: bytes, filename: str, content_type: str) -> str:
    client = get_b2_client()
    unique_filename = f"{uuid.uuid4()}_{filename}"
    client.put_object(
        Bucket=B2_BUCKET_NAME,
        Key=unique_filename,
        Body=file_bytes,
        ContentType=content_type
    )
    public_url = f"{B2_ENDPOINT}/file/{B2_BUCKET_NAME}/{unique_filename}"
    return public_url

def get_signed_url(file_url: str, expires_in: int = 3600) -> str:
    try:
        client = get_b2_client()
        filename = file_url.split("/")[-1]
        signed_url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": B2_BUCKET_NAME,
                "Key": filename
            },
            ExpiresIn=expires_in
        )
        return signed_url
    except Exception as e:
        print(f"Error generating signed URL: {e}")
        return file_url

def delete_file(file_url: str):
    try:
        client = get_b2_client()
        filename = file_url.split("/")[-1]
        client.delete_object(
            Bucket=B2_BUCKET_NAME,
            Key=filename
        )
    except Exception as e:
        print(f"Error deleting file: {e}")