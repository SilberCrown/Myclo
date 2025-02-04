# main.py
import os
import sqlite3
import calendar
import datetime

import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash



# ============== APIキーをここに設定してください ==============
OPENWEATHER_API_KEY = "bb232ad9a15414a92aa9678196206b13"
UNSPLASH_ACCESS_KEY = "ALmLnXL666dyaqW_rqwpINXImp9BYLS-YSnZYjqKWP0"

# アップロードされた服の画像を保存するフォルダ
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # フォルダがなければ作成

# Flaskアプリ設定
app = Flask(__name__)
app.secret_key = "any_secret_string_you_like"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# アップロード許可拡張子
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


# =========================================
# 1. データベース初期化
# =========================================
def init_db():
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()

    # users テーブル
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)

    # clothes テーブル (服の名前+画像パスを保持)
    c.execute("""
    CREATE TABLE IF NOT EXISTS clothes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        cloth_name TEXT NOT NULL,
        image_path TEXT,  -- 追加: 画像パスの列
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # favorites テーブル (AI提案のお気に入り)
    c.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        outfit_text TEXT,
        outfit_image_url TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # カレンダー用テーブル (ユーザーがイベント等を登録)
    c.execute("""
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # ユーザー設定テーブル
    # theme: 'default' or 'xp'
    # temp_unit: 'c' or 'f'
    # light_mode: 0 or 1 (画像表示などを抑制)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        theme TEXT DEFAULT 'default',
        temp_unit TEXT DEFAULT 'c',
        light_mode INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    conn.close()

init_db()


# =========================================
# 2. ユーティリティ関数
# =========================================

def allowed_file(filename):
    """アップロード画像の拡張子チェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_settings(user_id):
    """ユーザー設定を取得。無ければデフォルト値を作る。"""
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("SELECT theme, temp_unit, light_mode FROM user_settings WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row is None:
        # 無ければ作成
        c.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        c.execute("SELECT theme, temp_unit, light_mode FROM user_settings WHERE user_id=?", (user_id,))
        row = c.fetchone()
    conn.close()
    theme, temp_unit, light_mode = row
    return {
        "theme": theme,
        "temp_unit": temp_unit,
        "light_mode": bool(light_mode)
    }

def update_user_settings(user_id, theme=None, temp_unit=None, light_mode=None):
    """ユーザー設定を更新"""
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    current = get_user_settings(user_id)  # 既存を取得
    new_theme = theme if theme is not None else current["theme"]
    new_temp = temp_unit if temp_unit is not None else current["temp_unit"]
    new_light = 1 if light_mode else (1 if current["light_mode"] else 0)

    c.execute("""
        UPDATE user_settings
        SET theme=?, temp_unit=?, light_mode=?
        WHERE user_id=?
    """, (new_theme, new_temp, new_light, user_id))
    conn.commit()
    conn.close()

def convert_temp_if_needed(temp_c, user_settings):
    """ユーザー設定が華氏(f)の場合は温度を変換する"""
    if user_settings["temp_unit"] == "f":
        # 摂氏 -> 華氏
        return (temp_c * 9/5) + 32
    return temp_c

# -----------------------------------------
# AIによる服装提案（簡易サンプル版）
# -----------------------------------------
def get_ai_suggestion(weather_desc, temperature, user_clothes):
    """
    ダミーで実装:
      - 温度が低いほど厚着、高いほど薄着
      - user_clothesを一覧表示
    """
    suggestion = ""
    if temperature < 10:
        suggestion = f"現在の天気: {weather_desc} / 気温: {temperature:.1f}°。暖かいコートやセーターがおすすめです。"
    elif temperature < 20:
        suggestion = f"現在の天気: {weather_desc} / 気温: {temperature:.1f}°。少し肌寒いので軽めのジャケットがあると安心です。"
    else:
        suggestion = f"現在の天気: {weather_desc} / 気温: {temperature:.1f}°。Tシャツや薄手のシャツで快適に過ごせそうです。"

    if user_clothes:
        suggestion += f"\n登録済みの服: {', '.join(user_clothes)}"
    else:
        suggestion += "\nまだ服が登録されていません。"
    return suggestion


def search_clothes_image(keyword):
    """
    Unsplash APIで画像検索。最初の1枚を返す
    """
    url = "https://api.unsplash.com/search/photos"
    headers = {
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }
    params = {
        "query": keyword,
        "per_page": 1
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if data.get("results"):
        return data["results"][0]["urls"]["regular"]
    else:
        return None

def get_weather_data(lat, lon):
    """
    OpenWeatherMap APIから現在地(lat, lon)の天気情報を取得し、天気概要と気温(摂氏)を返す
    """
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # 摂氏
        "lang": "ja"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        weather_desc = data["weather"][0]["description"]
        temp_c = data["main"]["temp"]
        return weather_desc, temp_c
    else:
        return None, None


# =========================================
# 3. Flask ルーティング
# =========================================

@app.route("/")
def index():
    """
    トップページ。
    ログインしていればメイン画面を、未ログインなら新規登録/ログインフォームを表示
    """
    if "user_id" in session:
        user_settings = get_user_settings(session["user_id"])
        return render_template(
            "index.html",
            logged_in=True,
            username=session["username"],
            user_settings=user_settings
        )
    else:
        return render_template("index.html", logged_in=False, username=None)


@app.route("/register", methods=["POST"])
def register():
    """新規ユーザー登録"""
    username = request.form.get("username")
    password = request.form.get("password")

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        # user_settings も初期化される( init_db() でINSERTするが、ログイン後に確定)
    except sqlite3.IntegrityError:
        conn.close()
        return "このユーザー名は既に使われています。<br><a href='/'>戻る</a>"
    conn.close()
    return redirect(url_for("index"))


@app.route("/login", methods=["POST"])
def login():
    """ログイン処理"""
    username = request.form.get("username")
    password = request.form.get("password")

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("SELECT id, password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()

    if row:
        user_id, db_password = row
        if password == db_password:
            session["user_id"] = user_id
            session["username"] = username
            # user_settings がなければ作成される
            _ = get_user_settings(user_id)
            return redirect(url_for("index"))

    return "ログインに失敗しました。<br><a href='/'>戻る</a>"


@app.route("/logout")
def logout():
    """ログアウト"""
    session.clear()
    return redirect(url_for("index"))


@app.route("/delete_account", methods=["POST"])
def delete_account():
    """アカウント削除"""
    if "user_id" in session:
        user_id = session["user_id"]
        conn = sqlite3.connect("myclo.db")
        c = conn.cursor()
        # 関連データ削除
        c.execute("DELETE FROM favorites WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM clothes WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM calendar_events WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM user_settings WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        session.clear()
        return "アカウントを削除しました。<br><a href='/'>トップへ</a>"
    else:
        return redirect(url_for("index"))


# -----------------------------------------
# 3-1. Myクローゼット機能
# -----------------------------------------
@app.route("/my_closet")
def my_closet():
    """
    ユーザーが登録している服の一覧を表示（画像あり）。
    """
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("SELECT id, cloth_name, image_path FROM clothes WHERE user_id=?", (user_id,))
    clothes_list = c.fetchall()
    conn.close()

    user_settings = get_user_settings(user_id)

    return render_template(
        "closet.html",
        logged_in=True,
        username=session["username"],
        clothes_list=clothes_list,
        user_settings=user_settings
    )


@app.route("/upload_cloth", methods=["POST"])
def upload_cloth():

    """
    服（名前＋画像）を登録する
    """
    if "user_id" not in session:
        return "ログインしてください。"

    user_id = session["user_id"]
    cloth_name = request.form.get("cloth_name")
    file = request.files.get("cloth_image")

    image_path = None
    if file and allowed_file(file.filename):
        filename = file.filename
        # ファイルパスを一意にするため、日付時刻などを付加しても良い
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(save_path)
        # static/uploads/... のパスをDBに保存
        image_path = f"uploads/{filename}"

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO clothes (user_id, cloth_name, image_path) VALUES (?, ?, ?)
    """, (user_id, cloth_name, image_path))
    conn.commit()
    conn.close()

    return redirect(url_for("my_closet"))


# -----------------------------------------
# 3-2. カレンダー機能
# -----------------------------------------
@app.route("/calendar")
def calendar_view():
    """
    カレンダー画面を表示
    シンプルに「今月」のカレンダーを表示し、DBに登録されたイベントを表示
    """
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    user_settings = get_user_settings(user_id)

    # 今月の情報を生成
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month

    # 月の日数と週情報をcalendarで取得
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり(6) or 月曜始まり(0)
    month_days = cal.itermonthdates(current_year, current_month)
    # 例: itermonthdates(2025, 1) -> datetime.date(...) を列挙

    # イベントを取得（今月分だけ）
    start_date = datetime.date(current_year, current_month, 1).isoformat()
    end_day = calendar.monthrange(current_year, current_month)[1]  # 末日
    end_date = datetime.date(current_year, current_month, end_day).isoformat()

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("""
        SELECT date, description FROM calendar_events
        WHERE user_id=? AND date BETWEEN ? AND ?
    """, (user_id, start_date, end_date))
    events = c.fetchall()
    conn.close()

    # { "YYYY-MM-DD": [ "イベント1", "イベント2", ... ] } の形にまとめる
    events_dict = {}
    for date_str, desc in events:
        if date_str not in events_dict:
            events_dict[date_str] = []
        events_dict[date_str].append(desc)

    # テンプレートに渡す
    return render_template(
        "calendar.html",
        logged_in=True,
        username=session["username"],
        user_settings=user_settings,
        current_year=current_year,
        current_month=current_month,
        month_days=list(month_days),
        events_dict=events_dict
    )


@app.route("/add_calendar_event", methods=["POST"])
def add_calendar_event():
    """
    カレンダーにイベント(説明文)を登録
    フォームで指定された日付と説明をDBに保存
    """
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    date_str = request.form.get("date")
    description = request.form.get("description")

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO calendar_events (user_id, date, description)
        VALUES (?, ?, ?)
    """, (user_id, date_str, description))
    conn.commit()
    conn.close()

    return redirect(url_for("calendar_view"))


# -----------------------------------------
# 3-3. 設定（テーマ・温度単位・軽量化モード）
# -----------------------------------------
@app.route("/settings")
def settings_page():
    """
    設定画面
    """
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    user_settings = get_user_settings(user_id)
    return render_template(
        "settings.html",
        logged_in=True,
        username=session["username"],
        user_settings=user_settings
    )


@app.route("/update_settings", methods=["POST"])
def update_settings():
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    hidden_command = request.form.get("hidden_command", "").strip().lower()
    temp_unit = request.form.get("temp_unit", "c")
    light_mode = request.form.get("light_mode")


    if hidden_command == "windows xp":
        theme = "xp"
    elif hidden_command == "dark secret":
        theme = "dark"
    elif hidden_command == "でたらめ":
        theme = "detarame"
    elif hidden_command == "2048":
        theme = "game_2048"
    elif hidden_command == "テトリス":
        theme = "game_tetris"
    elif hidden_command == "mycra":
        theme = "game_mycra"
    else:
        theme = "default"

    update_user_settings(
        user_id=user_id,
        theme=theme,
        temp_unit=temp_unit,
        light_mode=(light_mode == "on")
    )

 
    if theme == "game_mycra":
        return redirect(url_for("game_mycra"))
    elif theme == "game_2048":
        return redirect(url_for("game_2048"))
    elif theme == "game_tetris":
        return redirect(url_for("game_tetris"))
    else:
        return redirect(url_for("settings_page"))



# -----------------------------------------
# 3-4. 天気から服装を提案
# -----------------------------------------
@app.route("/get_suggestion", methods=["POST"])
def get_suggestion():
    if "user_id" not in session:
        return jsonify({"error": "ログインが必要です"})

    lat = request.form.get("lat")
    lon = request.form.get("lon")
    user_id = session["user_id"]

    # ユーザーの所持服一覧
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("SELECT cloth_name FROM clothes WHERE user_id=?", (user_id,))
    clothes_rows = c.fetchall()
    conn.close()
    user_clothes = [row[0] for row in clothes_rows]

    # 設定を取得 (温度単位, 軽量化モードなど)
    user_settings = get_user_settings(user_id)

    # 天気情報取得(摂氏)
    weather_desc, temp_c = get_weather_data(lat, lon)
    if weather_desc is None:
        return jsonify({"error": "天気情報の取得に失敗しました。"})

    # 設定に応じて温度変換
    final_temp = convert_temp_if_needed(temp_c, user_settings)

    suggestion_text = get_ai_suggestion(weather_desc, final_temp, user_clothes)

    # 軽量化モードなら画像検索を行わない
    image_url = None
    if not user_settings["light_mode"]:
        # 気温(celsius)によってキーワードを変える (検索キーワード用に temp_c を使う)
        if temp_c < 10:
            keyword = "warm coat outfit"
        elif temp_c < 20:
            keyword = "light jacket outfit"
        else:
            keyword = "summer outfit"

        image_url = search_clothes_image(keyword)

    return jsonify({
        "suggestion_text": suggestion_text,
        "image_url": image_url
    })


# -----------------------------------------
# 3-5. お気に入り機能
# -----------------------------------------
@app.route("/add_favorite", methods=["POST"])
def add_favorite():
    if "user_id" not in session:
        return "ログインが必要です。"
    suggestion_text = request.form.get("suggestion_text")
    image_url = request.form.get("image_url")
    user_id = session["user_id"]

    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO favorites (user_id, outfit_text, outfit_image_url)
        VALUES (?, ?, ?)
    """, (user_id, suggestion_text, image_url))
    conn.commit()
    conn.close()

    return "お気に入りに追加しました。"


@app.route("/favorites")
def favorites():
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    conn = sqlite3.connect("myclo.db")
    c = conn.cursor()
    c.execute("SELECT outfit_text, outfit_image_url FROM favorites WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    user_settings = get_user_settings(user_id)
    return render_template(
        "index.html",
        logged_in=True,
        username=session["username"],
        favorites_list=rows,
        user_settings=user_settings
    )

@app.route("/game_2048")
def game_2048():
    """
    2048風ゲームを表示するページ
    """
    if "user_id" not in session:
        return redirect(url_for("index"))
    
    # user_settings を読んで、もし theme != "game_2048" なら
    # 「まだコマンドを入力してません」などのメッセージ表示してもOK
    user_id = session["user_id"]
    user_settings = get_user_settings(user_id)
    if user_settings["theme"] != "game_2048":
        # 隠しコマンド以外では来られないようにする(任意)
        return "隠しコマンドが入力されていません。<br><a href='/settings'>設定へ</a>"

    return render_template("game_2048.html")

@app.route("/game_tetris")
def game_tetris():
    """
    テトリス風ゲームを表示するページ
    """
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    user_settings = get_user_settings(user_id)
    if user_settings["theme"] != "game_tetris":
        return "隠しコマンドが入力されていません。<br><a href='/settings'>設定へ</a>"

    return render_template("game_tetris.html")

@app.route("/game_mycra")
def game_mycra():
    """
    Minecraft風（2D簡易版）ゲームを表示するページ
    """
    if "user_id" not in session:
        return redirect(url_for("index"))
    user_id = session["user_id"]
    user_settings = get_user_settings(user_id)
    if user_settings["theme"] != "game_mycra":
        return "隠しコマンドが入力されていません。<br><a href='/settings'>設定へ</a>"

    # テンプレート表示
    return render_template("game_mycra.html")




# =========================================
# 実行
# =========================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
