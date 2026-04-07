"""Upload ANAMNESIS SE to Nexus Mods via API v3.

Usage:
    python upload_nexus.py <version> [description]

Examples:
    python upload_nexus.py 1.1.0 "Visual agent skill tree, inventory editor, bug fixes"
    python upload_nexus.py 1.1.0

API key is read from the companion project's .nexus_api_key file or NEXUS_API_KEY env var.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE = "https://api.nexusmods.com/v3"
GROUP_ID = "7228420"
FILE_NAME = "ANAMNESIS_SE.zip"
FILE_CATEGORY = "main"

MULTIPART_THRESHOLD = 100 * 1024 * 1024


def _load_api_key():
    key = os.environ.get("NEXUS_API_KEY", "").strip()
    if key:
        return key

    # Check local key file first, then companion project
    for path in [
        os.path.join(SCRIPT_DIR, ".nexus_api_key"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "DigimonCompanion", ".nexus_api_key"),
    ]:
        if os.path.isfile(path):
            with open(path) as f:
                key = f.read().strip()
            if key:
                return key

    print("ERROR: No API key found.")
    print("  Set NEXUS_API_KEY environment variable, or")
    print("  create .nexus_api_key with your key.")
    sys.exit(1)


def _api_request(path, api_key, method="GET", body=None):
    url = f"{API_BASE}{path}"
    headers = {
        "apikey": api_key,
        "User-Agent": "ANAMNESIS-SE-uploader/1.0",
        "Content-Type": "application/json",
    }

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            if isinstance(result, dict) and "data" in result and len(result) <= 2:
                return result["data"]
            return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  API error {e.code}: {error_body}")
        sys.exit(1)


def _put_binary(url, data):
    req = urllib.request.Request(url, data=data, method="PUT")
    req.add_header("Content-Type", "application/octet-stream")
    req.add_header("Content-Length", str(len(data)))

    with urllib.request.urlopen(req) as resp:
        etag = resp.headers.get("ETag", "").strip('"')
        return etag


def _post_xml(url, xml_data):
    req = urllib.request.Request(url, data=xml_data.encode(), method="POST")
    req.add_header("Content-Type", "application/xml")

    with urllib.request.urlopen(req) as resp:
        return resp.read()


def _find_zip():
    dist_path = os.path.join(SCRIPT_DIR, "dist", "ANAMNESIS_SE.zip")
    if os.path.isfile(dist_path):
        return dist_path

    print("ERROR: Could not find dist/ANAMNESIS_SE.zip")
    print("  Build first: pyinstaller ANAMNESIS_SaveEditor.spec --noconfirm")
    sys.exit(1)


def upload_simple(file_path, file_size, api_key):
    print("  Creating upload session...")
    result = _api_request("/uploads", api_key, method="POST", body={
        "filename": FILE_NAME,
        "size_bytes": file_size,
    })
    upload_id = result["id"]
    presigned_url = result["presigned_url"]
    print(f"  Upload ID: {upload_id}")

    print(f"  Uploading {file_size / (1024*1024):.1f} MB...")
    with open(file_path, "rb") as f:
        file_data = f.read()
    _put_binary(presigned_url, file_data)
    print("  Upload complete.")

    return upload_id


def upload_multipart(file_path, file_size, api_key):
    print("  Creating multipart upload session...")
    result = _api_request("/uploads/multipart", api_key, method="POST", body={
        "filename": FILE_NAME,
        "size_bytes": file_size,
    })
    upload_id = result["id"]
    part_urls = result["parts_presigned_url"]
    part_size = result["parts_size"]
    complete_url = result["complete_presigned_url"]
    print(f"  Upload ID: {upload_id} ({len(part_urls)} parts, {part_size // (1024*1024)} MB each)")

    with open(file_path, "rb") as f:
        file_data = f.read()

    parts = []
    for i, url in enumerate(part_urls):
        part_num = i + 1
        start = i * part_size
        end = min(start + part_size, file_size)
        chunk = file_data[start:end]
        print(f"  Uploading part {part_num}/{len(part_urls)} ({len(chunk) // 1024} KB)...")
        etag = _put_binary(url, chunk)
        parts.append((part_num, etag))

    print("  Completing multipart upload...")
    xml_parts = "\n".join(
        f"  <Part>\n    <PartNumber>{num}</PartNumber>\n    <ETag>{etag}</ETag>\n  </Part>"
        for num, etag in parts
    )
    xml = f"<CompleteMultipartUpload>\n{xml_parts}\n</CompleteMultipartUpload>"
    _post_xml(complete_url, xml)
    print("  Multipart complete.")

    return upload_id


def finalize_and_poll(upload_id, api_key):
    print("  Finalizing upload...")
    _api_request(f"/uploads/{upload_id}/finalise", api_key, method="POST")

    print("  Waiting for processing...", end="", flush=True)
    for attempt in range(60):
        result = _api_request(f"/uploads/{upload_id}", api_key)
        if result["state"] == "available":
            print(" ready!")
            return
        delay = min(2 * (1.5 ** attempt), 30)
        print(".", end="", flush=True)
        time.sleep(delay)

    print("\nERROR: Upload processing timed out.")
    sys.exit(1)


def create_version(upload_id, version, description, api_key):
    print(f"  Publishing version {version}...")
    body = {
        "upload_id": upload_id,
        "name": FILE_NAME,
        "version": version,
        "file_category": FILE_CATEGORY,
    }
    if description:
        body["description"] = description

    result = _api_request(
        f"/mod-file-update-groups/{GROUP_ID}/versions",
        api_key, method="POST", body=body,
    )
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_nexus.py <version> [description]")
        print('Example: python upload_nexus.py 1.1.0 "Visual skill tree, inventory editor"')
        sys.exit(1)

    version = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"ANAMNESIS SE — Nexus Mods Uploader")
    print(f"  Version: {version}")
    if description:
        print(f"  Description: {description}")
    print()

    api_key = _load_api_key()
    print("[1/4] Locating zip...")
    zip_path = _find_zip()
    file_size = os.path.getsize(zip_path)
    print(f"  Found: {zip_path} ({file_size / (1024*1024):.1f} MB)")

    print(f"\n[2/4] Uploading to Nexus Mods...")
    if file_size > MULTIPART_THRESHOLD:
        upload_id = upload_multipart(zip_path, file_size, api_key)
    else:
        upload_id = upload_simple(zip_path, file_size, api_key)

    print(f"\n[3/4] Finalizing...")
    finalize_and_poll(upload_id, api_key)

    print(f"\n[4/4] Publishing...")
    result = create_version(upload_id, version, description, api_key)
    file_id = result.get("id", "unknown")
    print(f"  Published! File ID: {file_id}")

    print(f"\nDone! ANAMNESIS SE v{version} is live on Nexus Mods.")


if __name__ == "__main__":
    main()
