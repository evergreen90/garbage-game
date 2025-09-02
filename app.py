import os
import csv
import time
import random
from flask import Flask, jsonify, render_template, request

# ファイルの場所を決める
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "services", "hiraizumi_garbage_dic.csv")

# かんたんなキャッシュ（10分）
CACHE_TTL_SEC = 60 * 10
_CACHE_DATA = None
_CACHE_TIME = 0.0

app = Flask(__name__, static_folder="static", template_folder="templates")


def read_csv_text(csv_path):
    # まずは UTF-8 で読んで、だめなら UTF-8-SIG でもう一回試す
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return f.read()


def make_simple_category(original_category):
    # 5つの分類にそろえる。なければ「その他」
    s = (original_category or "").strip()
    # 表記ゆれを「リサイクル」に統一
    synonyms = {
        "燃えるごみ": "燃やすごみ",
        "可燃ごみ": "燃やすごみ",
        "もやすごみ": "燃やすごみ",
        "燃やさないごみ": "燃やせないごみ",
        "不燃ごみ": "燃やせないごみ",
        "資源ごみ": "リサイクル",
        "資源ゴミ": "リサイクル",
        "資源": "リサイクル",
    }
    s = synonyms.get(s, s)
    allowed = ["燃やすごみ", "燃やせないごみ", "リサイクル", "粗大ごみ"]
    if s in allowed:
        return s
    return "その他"


def parse_csv_to_records(csv_text):
    # 期待するヘッダ: _id, 品名, ゴミの種類, 出し方の注意点
    f = csv_text.splitlines()
    reader = csv.DictReader(f)
    need = {"_id", "品名", "ゴミの種類", "出し方の注意点"}
    if not reader.fieldnames or not need.issuperset(set(need)) or not need.issubset(set(reader.fieldnames)):
        raise RuntimeError("CSVヘッダが想定と異なります。必要: _id, 品名, ゴミの種類, 出し方の注意点")

    records = []
    seen = set()  # （品名, 元分類）の重複を防ぐ
    for row in reader:
        item = (row.get("品名") or "").strip()
        full_category = (row.get("ゴミの種類") or "").strip()
        note = (row.get("出し方の注意点") or "").strip()

        if not item or not full_category:
            continue

        key = (item, full_category)
        if key in seen:
            continue
        seen.add(key)

        records.append(
            {
                "item": item,
                "category": make_simple_category(full_category),
                "fullCategory": full_category,
                "note": note,
            }
        )

    return records


def load_dataset():
    # キャッシュがあれば使う
    global _CACHE_DATA, _CACHE_TIME
    now = time.time()
    if _CACHE_DATA is not None and (now - _CACHE_TIME) < CACHE_TTL_SEC:
        return _CACHE_DATA

    # CSV を読んでパース
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"{CSV_PATH} not found.")
    text = read_csv_text(CSV_PATH)
    data = parse_csv_to_records(text)

    # キャッシュ更新
    _CACHE_DATA = data
    _CACHE_TIME = now
    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/quiz")
def api_quiz():
    # データを読み込んで、ランダムにして、limit件返す
    limit = request.args.get("limit", default=100, type=int)
    data = load_dataset()[:]
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
