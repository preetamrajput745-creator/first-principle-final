import urllib.request
import zipfile
import os

url = "https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_windows_amd64.zip"
zip_path = "vault.zip"
extract_path = "."

print(f"Downloading Vault from {url}...")
try:
    urllib.request.urlretrieve(url, zip_path)
    print("Download complete.")

    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Extraction complete. vault.exe should be in current dir.")
except Exception as e:
    print(f"Error: {e}")
