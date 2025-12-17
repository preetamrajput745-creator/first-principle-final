import urllib.request
import zipfile
import os
import shutil

# Grafana
grafana_url = "https://dl.grafana.com/oss/release/grafana-10.2.0.windows-amd64.zip"
grafana_zip = "grafana.zip"

# Prometheus (for promtool)
prom_url = "https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.windows-amd64.zip"
prom_zip = "prometheus.zip"

def download_and_extract(url, zip_name, extract_root, target_name):
    print(f"Downloading {url}...")
    try:
        urllib.request.urlretrieve(url, zip_name)
        print("Download complete.")
        print(f"Extracting to {extract_root}...")
        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            zip_ref.extractall(extract_root)
        
        # Renaissance move: find the extracted folder (it usually has version name) and rename/symlink
        items = os.listdir(extract_root)
        for item in items:
            if target_name in item and os.path.isdir(os.path.join(extract_root, item)):
                # If target dir exists, remove it first
                final_path = os.path.join(extract_root, target_name)
                source_path = os.path.join(extract_root, item)
                if os.path.exists(final_path) and final_path != source_path:
                   # This logic is a bit flaky if we extract multiple times. 
                   # Just looking for the exe
                   pass
        print(f"Extracted. Please verify {target_name} binary.")
    except Exception as e:
        print(f"Error: {e}")

# Create temp dir for tools
if not os.path.exists("tools"):
    os.makedirs("tools")

if not os.path.exists("tools/grafana"):
    download_and_extract(grafana_url, "tools/" + grafana_zip, "tools", "grafana")

if not os.path.exists("tools/prometheus"):
    download_and_extract(prom_url, "tools/" + prom_zip, "tools", "prometheus")
