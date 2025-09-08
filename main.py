from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os, json, datetime, requests, re

app = Flask(__name__)
app.secret_key = "TaFoSecretKey"

ADMIN_PASSWORD = "12345"
TAFO_FILE = "TaFo.json"
LOG_FILE = "TaFo.log"

# Initialize TaFo.json if it doesn't exist
if not os.path.exists(TAFO_FILE):
    data = {"users": [], "treasures": [], "admin_notes": ""}
    with open(TAFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def log_action(action, uid="", email=""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = request.remote_addr
    entry = f"[{now}] IP: {ip} UID: {uid} Email: {email} Action: {action}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def get_ip_info(ip):
    try:
        if ip == "127.0.0.1":
            return "Локальная разработка"
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("city", "Неизвестно")
    except requests.RequestException:
        return "Неизвестно"


@app.route('/')
def index():
    return render_template('FF.html')


@app.route('/register', methods=['POST'])
def register():
    # Registration logic...
    # (Existing code remains the same)
    pass


@app.route('/login', methods=['POST'])
def login():
    # Login logic...
    # (Existing code remains the same)
    pass


@app.route('/game')
def game():
    # Game logic...
    # (Existing code remains the same)
    pass


@app.route('/login_admin', methods=['GET'])
def login_admin_page():
    return render_template('login-admin.html')


@app.route('/process_login_admin', methods=['POST'])
def process_admin_login():
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        log_action("Admin logged in")
        return redirect(url_for('admin_panel'))
    else:
        log_action("Failed admin login attempt")
        return redirect(url_for('login_admin_page', error="Неверный пароль"))


@app.route('/admin')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('login_admin_page'))
    return render_template('admin.html')


@app.route('/admin/get_data', methods=['GET'])
def get_admin_data():
    if not session.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 401

    if not os.path.exists(TAFO_FILE):
        return jsonify({"error": "Data file not found"}), 404

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Format users data for frontend
    users = []
    for user in data.get("users", []):
        users.append({
            "uid": user.get("uid"),
            "email": user.get("email"),
            "password": user.get("password"),
            "ip": user.get("ip"),
            "location": user.get("city"),
            "registration_date": user.get("registration_date")
        })

    # Format treasures data for frontend
    treasures = []
    for treasure in data.get("treasures", []):
        treasures.append({
            "uid": treasure.get("uid"),
            "treasure_type": treasure.get("reward"),
            "claim_date": treasure.get("date"),
            "ip": treasure.get("ip", "Unknown")
        })

    return jsonify({
        "success": True,
        "users": users,
        "treasures": treasures,
        "admin_notes": data.get("admin_notes", "")
    })


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


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)
