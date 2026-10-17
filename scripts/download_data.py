"""Baixa os quatro CSVs oficiais necessários, sem extração arbitrária do ZIP."""
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
NAMES = ["olist_order_reviews_dataset.csv", "olist_orders_dataset.csv",
         "olist_order_items_dataset.csv", "olist_products_dataset.csv"]

if __name__ == "__main__":
    try:
        print("Baixando base Olist do Kaggle…")
        with urllib.request.urlopen(URL, timeout=180) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        raw = ROOT / "data" / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            temporary = raw / (name + ".tmp")
            temporary.write_bytes(archive.read(name))
            temporary.replace(raw / name)
            print("Salvo em", raw / name)
    except Exception as exc:
        sys.exit(f"Download falhou: {exc}. Baixe manualmente no Kaggle e coloque os quatro CSVs em data/raw/.")
