import os
import json
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = "supersecretkey123"

DATA_FILE = "TaFo.json"

# -----------------------
# Загрузка и сохранение пользователей
# -----------------------
def load_users():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

# -----------------------
# Главная страница
# -----------------------
@app.route("/")
def index():
    return render_template("FF.html")

# -----------------------
# Игровая страница по UID
# -----------------------
@app.route("/game/<uid>")
def game(uid):
    users = load_users()
    if uid not in users:
        flash("Пользователь не найден!", "error")
        return redirect(url_for("index"))
    user = users[uid]
    return render_template("FF2.html", user=user)

# -----------------------
# Логин администратора
# -----------------------
@app.route("/login-admin", methods=["GET", "POST"])
def login_admin_page():
    if request.method == "POST":
        password = request.form.get("password")
        if password == "admin123":  # Простой пароль админа
            return redirect(url_for("admin_panel"))
        else:
            flash("Неверный пароль!", "error")
            return redirect(url_for("login_admin_page"))
    return render_template("login-admin.html")

# -----------------------
# Панель администратора
# -----------------------
@app.route("/admin")
def admin_panel():
    users = load_users()
    return render_template("admin.html", users=users)

# -----------------------
# Обмен монет на алмазы
# -----------------------
@app.route("/exchange/<uid>", methods=["POST"])
def exchange(uid):
    users = load_users()
    if uid not in users:
        return jsonify({"status": "error", "message": "Пользователь не найден!"})
    user = users[uid]
    cost = 500
    reward = 35
    if user["coins"] >= cost:
        user["coins"] -= cost
        user["diamonds"] += reward
        save_users(users)
        return jsonify({"status": "success", "coins": user["coins"], "diamonds": user["diamonds"]})
    else:
        return jsonify({"status": "error", "message": f"Недостаточно монет. Нужно {cost}."})

# -----------------------
# Ежедневный подарок
# -----------------------
@app.route("/daily-gift/<uid>", methods=["POST"])
def daily_gift(uid):
    users = load_users()
    if uid not in users:
        return jsonify({"status": "error", "message": "Пользователь не найден!"})
    user = users[uid]
    today = date.today().isoformat()
    if user.get("last_gift") == today:
        return jsonify({"status": "error", "message": "Подарок уже получен сегодня!"})
    reward = 100
    user["coins"] += reward
    user["last_gift"] = today
    save_users(users)
    return jsonify({"status": "success", "coins": user["coins"]})

# -----------------------
# Вывод алмазов
# -----------------------
@app.route("/withdraw/<uid>", methods=["POST"])
def withdraw(uid):
    users = load_users()
    if uid not in users:
        return jsonify({"status": "error", "message": "Пользователь не найден!"})
    user = users[uid]
    amount = 100
    if user["diamonds"] < amount:
        return jsonify({"status": "error", "message": f"Недостаточно алмазов. Нужно {amount}."})
    user["diamonds"] -= amount
    save_users(users)
    return jsonify({"status": "success", "diamonds": user["diamonds"], "message": f"Выведено {amount} алмазов!"})

# -----------------------
# Запуск сервера
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
