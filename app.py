import os
import csv
import time
import random
import sqlite3
from flask import Flask, jsonify, render_template, request

# ファイルの場所を決める
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "services", "hiraizumi_garbage_dic.csv")
DB_PATH = os.path.join(BASE_DIR, "results.db")

# かんたんなキャッシュ（10分）
CACHE_TTL_SEC = 60 * 10
_CACHE_DATA = None
_CACHE_TIME = 0.0

app = Flask(__name__, static_folder="static", template_folder="templates")

# 履歴を保存するためのDB準備
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            correct INTEGER NOT NULL,
            total INTEGER NOT NULL,
            accuracy REAL NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()

#CSVをUTF-8系で読み込めるように
init_db()

def read_csv_text(csv_path):
    # まずは UTF-8 で読んで、だめなら UTF-8-SIG でもう一回試す
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return f.read()

# 表記のゆれを許容する部分
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
        "びん": "リサイクル",
        "缶": "リサイクル",
        "ペットボトル": "リサイクル",
        "プラ": "リサイクル",
        "容器包装プラ": "リサイクル",
        }
    s = synonyms.get(s, s)
    allowed = ["燃やすごみ", "燃やせないごみ", "リサイクル", "粗大ごみ"]
    if s in allowed:
        return s
    return "その他"


def parse_csv_to_records(csv_text):
    # 期待するヘッダ: _id, 品名, ゴミの種類, 出し方の注意点
    f = csv_text.splitlines()       # CSVの中身を行ごとに分割してリスト化
    reader = csv.DictReader(f)
    need = {"_id", "品名", "ゴミの種類", "出し方の注意点"} #CSVに必須のヘッダ定義
    if not reader.fieldnames or not need.issuperset(set(need)) or not need.issubset(set(reader.fieldnames)):
        raise RuntimeError("CSVヘッダが想定と異なります。必要: _id, 品名, ゴミの種類, 出し方の注意点")

    records = []
    seen = set()  # （品名, 元分類）の重複を防ぐ
    for row in reader:
        item = (row.get("品名") or "").strip()  #strip()は前後の空白を除去
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


@app.route("/api/results", methods=["POST"])
def save_result():
    """
    POST {correct, total} を保存。accuracy はサーバ側で計算。
    """
    data = request.get_json(silent=True) or {}
    try:
        correct = int(data.get("correct", 0))
        total = int(data.get("total", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "invalid payload"}), 400

    if total <= 0:
        return jsonify({"ok": False, "error": "total must be > 0"}), 400

    accuracy = round(correct / total, 4)
    ts = int(time.time())

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO results(ts, correct, total, accuracy) VALUES(?,?,?,?)",
        (ts, correct, total, accuracy),
    )
    conn.commit()
    conn.close()

    return jsonify(
        {"ok": True, "saved": {"ts": ts, "correct": correct, "total": total, "accuracy": accuracy}}
    )


@app.route("/api/results", methods=["GET"])
def list_results():
    """
    GET /api/results?limit=200 で新しい順に履歴を返す
    """
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 1000))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT ts, correct, total, accuracy FROM results ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()

    items = [{"ts": ts, "correct": c, "total": t, "accuracy": a} for (ts, c, t, a) in rows]
    return jsonify({"count": len(items), "items": items})


@app.route("/history")
def history_page():
    return render_template("history.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
