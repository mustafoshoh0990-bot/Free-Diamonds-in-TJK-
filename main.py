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
        return data.get("city", "Unknown")
    except (requests.RequestException, json.JSONDecodeError):
        return "Unknown"


# Home page and registration/login
@app.route("/")
def index():
    return render_template("FF.html")


# User login
@app.route("/login", methods=["POST"])
def login():
    uid = request.form.get("uid")
    password = request.form.get("password")

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user = next((u for u in data["users"] if u["uid"] == uid and u["password"] == password), None)
    if user:
        session["user_id"] = uid
        log_action(f"User logged in", uid=uid)
        return redirect(url_for("game"))
    else:
        return render_template("FF.html", error="Неверный UID или пароль")


# User registration
@app.route("/register", methods=["POST"])
def register():
    uid = request.form.get("uid")
    password = request.form.get("password")
    email = request.form.get("email")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return render_template("FF.html", error_register="Неверный формат почты")

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if any(u["uid"] == uid for u in data["users"]):
        return render_template("FF.html", error_register="Этот UID уже зарегистрирован")

    new_user = {
        "uid": uid,
        "email": email,
        "password": password,
        "balance": 0,
        "diamonds": 0,
        "last_collect": None,
        "last_ad_watch": None,
        "last_diamond_redeem": None,
        "last_withdraw": None,
        "registration_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": request.remote_addr,
        "city": get_ip_info(request.remote_addr)
    }

    data["users"].append(new_user)
    with open(TAFO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    log_action(f"New user registered", uid=uid, email=email)
    session["user_id"] = uid
    return redirect(url_for("game"))


# User game panel
@app.route("/game")
def game():
    if "user_id" not in session:
        return redirect(url_for("index"))

    return render_template("FF2.html", uid=session["user_id"])


# Get user data
@app.route("/get_user_data")
def get_user_data():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    uid = session["user_id"]
    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user = next((u for u in data["users"] if u["uid"] == uid), None)
    if user:
        return jsonify(user)
    else:
        return jsonify({"error": "User not found"}), 404


# Save user progress
@app.route("/save_progress", methods=["POST"])
def save_progress():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    uid = session["user_id"]
    try:
        user_data = request.json
        with open(TAFO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        user_index = next((i for i, u in enumerate(data["users"]) if u["uid"] == uid), -1)
        if user_index != -1:
            data["users"][user_index]["balance"] = user_data["balance"]
            data["users"][user_index]["diamonds"] = user_data["diamonds"]
            data["users"][user_index]["last_collect"] = user_data["last_collect"]
            data["users"][user_index]["last_ad_watch"] = user_data["last_ad_watch"]
            data["users"][user_index]["last_diamond_redeem"] = user_data["last_diamond_redeem"]
            data["users"][user_index]["last_withdraw"] = user_data["last_withdraw"]

            with open(TAFO_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return jsonify({"success": True})
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Claim treasure
@app.route("/claim_treasure", methods=["POST"])
def claim_treasure():
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401

    uid = session["user_id"]
    treasure_type = request.json.get("treasure_type")

    with open(TAFO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    user = next((u for u in data["users"] if u["uid"] == uid), None)
    if user:
        new_treasure = {
            "uid": uid,
            "reward": treasure_type,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": request.remote_addr
        }
        data["treasures"].append(new_treasure)
        with open(TAFO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        log_action(f"User claimed treasure: {treasure_type}", uid=uid)
        return jsonify({"success": True})
    else:
        return jsonify({"error": "User not found"}), 404


# User logout
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


# Admin login page
@app.route("/login_admin")
def login_admin():
    return render_template("login-admin.html")


# Admin authentication
@app.route("/authenticate_admin", methods=["POST"])
def authenticate_admin():
    password = request.form.get("password")
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        log_action(f"Admin logged in")
        return redirect(url_for("admin_panel"))
    else:
        return render_template("login-admin.html", error="Неверный пароль администратора")


# Admin panel
@app.route("/admin")
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("login_admin"))
    return render_template("admin.html")


# Admin logout
@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("login_admin"))


# Admin data fetching
@app.route("/admin/get_data")
def get_admin_data():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

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

    log_action("Admin updated notes")
    return jsonify({"success": True})


# Run the app
if __name__ == "__main__":
    app.run(debug=True)
