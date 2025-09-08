from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os, json, datetime, requests

app = Flask(__name__)
app.secret_key = "TaFoSecretKey"

# --- Константы ---
ADMIN_PASSWORD = "12345"
TAFO_FILE = "TaFo.json"
LOG_FILE = "TaFo.log"

# --- Инициализация файлов ---
if not os.path.exists(TAFO_FILE):
    data = {"users": [], "treasures": [], "admin_notes": ""}
    with open(TAFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("=== TaFo Logs ===\n")


# --- Логирование ---
def log_action(action, uid="", email=""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = request.remote_addr
    entry = f"[{now}] IP: {ip} UID: {uid} Email: {email} Action: {action}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


# --- Получение информации по IP ---
def get_ip_info(ip):
    try:
        if ip == "127.0.0.1":
            return "Локальная разработка"
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        response.raise_for_status()
        data = response.json()
        city = data.get("city", "Unknown")
        country = data.get("country_name", "Unknown")
        return f"{city}, {country}"
    except Exception as e:
        log_action(f"Error getting IP info for {ip}: {e}")
        return "Неизвестно"


# --- Главная страница ---
@app.route('/')
def index():
    return render_template("FF.html")


# --- Авторизация пользователя ---
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user = next((u for u in data["users"] if u["email"] == email and u["password"] == password), None)

    if user:
        session["logged_in"] = True
        session["uid"] = user["uid"]
        session["email"] = email
        log_action("User logged in", uid=user["uid"], email=email)
        return redirect(url_for('dashboard'))
    else:
        log_action("Failed login attempt", email=email)
        return render_template("FF.html", error="Неверный email или пароль.")


# --- Регистрация пользователя ---
@app.route('/register', methods=['POST'])
def register():
    email = request.form.get("email")
    uid = request.form.get("uid")
    password = request.form.get("password")

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if any(u["email"] == email for u in data["users"]):
        log_action("Failed registration: Email already exists", email=email)
        return render_template("FF.html", error="Этот email уже зарегистрирован.")

    ip_info = get_ip_info(request.remote_addr)

    new_user = {
        "email": email,
        "uid": uid,
        "password": password,
        "coins": 0,
        "diamonds": 0,
        "ip": request.remote_addr,
        "city": ip_info,
        "registration_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    data["users"].append(new_user)

    with open(TAFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    log_action("User registered", uid=uid, email=email)
    session["logged_in"] = True
    session["uid"] = uid
    session["email"] = email
    return redirect(url_for('dashboard'))


# --- Личный кабинет ---
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('index'))

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_uid = session.get("uid")
    user = next((u for u in data["users"] if u["uid"] == user_uid), None)

    if not user:
        session.clear()
        return redirect(url_for('index'))

    return render_template("FF2.html", user=user, uid=user_uid)


# --- Обновление прогресса ---
@app.route('/update_progress', methods=['POST'])
def update_progress():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user_uid = session.get("uid")
        coins = request.json.get("coins")
        diamonds = request.json.get("diamonds")

        with open(TAFO_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            user = next((u for u in data["users"] if u["uid"] == user_uid), None)
            if user:
                user["coins"] = coins
                user["diamonds"] = diamonds
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=4)
            f.truncate()

        return jsonify({"success": True})
    except Exception as e:
        log_action(f"Failed to save progress: {e}", uid=session.get("uid"), email=session.get("email"))
        return jsonify({"error": "Failed to save progress"}), 500


# --- Получение награды ---
@app.route('/claim_treasure', methods=['POST'])
def claim_treasure():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        user_uid = session.get("uid")
        treasure_type = request.json.get("treasure_type")

        with open(TAFO_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)

        new_treasure = {
            "uid": user_uid,
            "reward": treasure_type,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": request.remote_addr
        }
        data["treasures"].append(new_treasure)

        with open(TAFO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        log_action(f"Treasure claimed: {treasure_type}", uid=user_uid, email=session.get("email"))
        return jsonify({"success": True})
    except Exception as e:
        log_action(f"Failed to claim treasure: {e}", uid=session.get("uid"), email=session.get("email"))
        return jsonify({"error": "Failed to claim treasure"}), 500


# --- Вход админа ---
@app.route('/admin_login_page', methods=['GET', 'POST'])
def login_admin_page():
    if request.method == 'POST':
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            log_action("Admin logged in")
            return redirect(url_for('admin_dashboard'))
        else:
            log_action("Failed admin login attempt")
            return render_template('login-admin.html', error="Неверный пароль.")
    return render_template('login-admin.html')


# --- Панель админа ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login_admin_page'))

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.readlines()

    users = [{
        "uid": u.get("uid"),
        "email": u.get("email"),
        "password": u.get("password"),
        "ip": u.get("ip"),
        "location": u.get("city"),
        "registration_date": u.get("registration_date")
    } for u in data.get("users", [])]

    treasures = [{
        "uid": t.get("uid"),
        "treasure_type": t.get("reward"),
        "claim_date": t.get("date"),
        "ip": t.get("ip", "Unknown")
    } for t in data.get("treasures", [])]

    return render_template('admin.html', users=users, treasures=treasures, admin_notes=data.get("admin_notes", ""))


# --- API для админа ---
@app.route('/admin/data')
def get_admin_data():
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify({
        "success": True,
        "users": data.get("users", []),
        "treasures": data.get("treasures", []),
        "admin_notes": data.get("admin_notes", "")
    })


# --- Обновление заметок админа ---
@app.route('/admin/update_notes', methods=['POST'])
def update_admin_notes():
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    notes = request.form.get('notes', '')

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["admin_notes"] = notes

    with open(TAFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return jsonify({"success": True})


# --- Выход из админки ---
@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    log_action("Admin logged out")
    return redirect(url_for('index'))


# --- Запуск ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
