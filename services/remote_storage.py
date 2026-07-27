"""Cloudflare R2 storage client.

R2 is S3-compatible, so we talk to it with boto3 using an R2-specific
endpoint. Credentials are never hard-coded — they're read from Streamlit
secrets (.streamlit/secrets.toml locally, or the "Secrets" panel in
Community Cloud's app settings):

    [r2]
    account_id = "..."
    access_key_id = "..."
    secret_access_key = "..."
    bucket = "evol-space"

If no [r2] secrets are configured, every function in this module becomes a
no-op / returns None, so the app still runs locally on plain local files —
it only "goes remote" once you've set up R2.
"""
import io
import os

import boto3
import streamlit as st
from botocore.client import Config

_client = None
_bucket = None


def _enabled() -> bool:
    try:
        return "r2" in st.secrets
    except Exception:
        # No secrets.toml at all (common for local dev without R2 set up) —
        # st.secrets raises in that case rather than just being empty.
        return False


def _get_client():
    global _client, _bucket
    if _client is not None:
        return _client

    cfg = st.secrets["r2"]
    endpoint = f"https://{cfg['account_id']}.r2.cloudflarestorage.com"
    _client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=cfg["access_key_id"],
        aws_secret_access_key=cfg["secret_access_key"],
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )
    _bucket = cfg["bucket"]
    return _client


# ---------------------------------------------------------------------------
# Generic object helpers
# ---------------------------------------------------------------------------

def upload_bytes(key: str, data: bytes) -> None:
    if not _enabled():
        return
    client = _get_client()
    client.put_object(Bucket=_bucket, Key=key, Body=data)


def download_bytes(key: str) -> bytes :
    if not _enabled():
        return None
    client = _get_client()
    try:
        obj = client.get_object(Bucket=_bucket, Key=key)
        return obj["Body"].read()
    except client.exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def delete_object(key: str) -> None:
    if not _enabled():
        return
    client = _get_client()
    client.delete_object(Bucket=_bucket, Key=key)


# ---------------------------------------------------------------------------
# Photo helpers
# ---------------------------------------------------------------------------

def upload_photo(filename: str, data: bytes) -> None:
    upload_bytes(f"photos/{filename}", data)


def download_photo(filename: str) -> bytes :
    return download_bytes(f"photos/{filename}")


def delete_photo(filename: str) -> None:
    delete_object(f"photos/{filename}")


# ---------------------------------------------------------------------------
# SQLite file sync (whole-file, fine for a low-write personal app)
# ---------------------------------------------------------------------------

DB_KEY = "data.db"


def pull_db(local_path: str) -> None:
    """Download the latest data.db from R2 to local_path, if one exists remotely."""
    data = download_bytes(DB_KEY)
    if data is not None:
        with open(local_path, "wb") as f:
            f.write(data)


def push_db(local_path: str) -> None:
    """Upload the current local data.db to R2."""
    if not _enabled() or not os.path.exists(local_path):
        return
    with open(local_path, "rb") as f:
        upload_bytes(DB_KEY, f.read())
