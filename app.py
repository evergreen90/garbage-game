import os
import csv
import time
import random
from io import StringIO
from typing import List, Dict
from flask import Flask, jsonify, render_template, send_from_directory, request

BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "services", "hiraizumi_garbage_dic.csv")

# 10分キャッシュ（不要なら 0 に）
_CACHE = {"data": None, "fetched": 0.0}
CACHE_TTL_SEC = 60 * 10

app = Flask(__name__, static_folder="static", template_folder="templates")


# 文字コードの読み込み対応
def _read_csv_text_utf8_only(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # BOM付きUTF-8で再試行
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()


# カテゴリ5分類
def simplify_category(s: str) -> str:
    s = (s or "").strip()
    allowed = {"燃やすごみ", "燃やさないごみ", "資源ごみ", "粗大ごみ"}
    if s in allowed:
        return s
    return "その他"


# 期待ヘッダ: ["_id","品名","ゴミの種類","出し方の注意点"]
def _parse_csv_fixed_columns(csv_text: str) -> List[Dict]:
    f = StringIO(csv_text)
    reader = csv.DictReader(f)
    required = {"_id", "品名", "ゴミの種類", "出し方の注意点"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise RuntimeError("CSVヘッダが想定と異なります。必要: _id, 品名, ゴミの種類, 出し方の注意点")

    out, seen = [], set()
    for row in reader:
        item = (row.get("品名") or "").strip()
        full = (row.get("ゴミの種類") or "").strip()
        note = (row.get("出し方の注意点") or "").strip()
        if not item or not full:
            continue
        key = (item, full)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "item": item,
                "category": simplify_category(full),  # 5分類
                "fullCategory": full,  # 元の分類
                "note": note,  # 注意点（今は未表示だが保持）
            }
        )
    return out


def get_dataset() -> List[Dict]:
    now = time.time()
    if _CACHE["data"] is not None and (now - _CACHE["fetched"] < CACHE_TTL_SEC):
        return _CACHE["data"]
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"{CSV_PATH} not found.")
    text = _read_csv_text_utf8_only(CSV_PATH)
    records = _parse_csv_fixed_columns(text)
    _CACHE["data"] = records
    _CACHE["fetched"] = now
    return records


@app.route("/")
def index():
    return render_template("index.html")


# データを返す
@app.route("/api/quiz")
def api_quiz():
    limit = request.args.get("limit", default=100, type=int)
    data = get_dataset()[:]
    random.shuffle(data)
    if limit > 0:
        data = data[:limit]
    return jsonify({"count": len(data), "items": data})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
