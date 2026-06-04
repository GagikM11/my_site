from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import db_manager
import auth_manager
import os

app = Flask(__name__)
app.secret_key = 'gaga_super_secret_key_99' # Секретный ключ для сессий

# Инициализация БД при запуске
db_manager.init_db()
auth_manager.init_auth_db()

@app.route('/')
def index():
    if 'user' in session:
        # Передаем имя пользователя прямо в HTML
        return render_template('index.html', username=session['user'])
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data.get('username') or not data.get('password'):
        return jsonify({"status": "error", "message": "Заполните все поля"}), 400
    if auth_manager.register_user(data['username'], data['password']):
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Ник уже занят"}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if auth_manager.login_user(data['username'], data['password']):
        session['user'] = data['username']
        session.permanent = True # Сессия будет долгой
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Неверный логин или пароль"}), 401

@app.route('/api/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

@app.route('/send', methods=['POST'])
def send():
    if 'user' not in session:
        return jsonify({"status": "error"}), 403
    
    data = request.json
    nickname = session['user'] # Имя берем из сессии, его нельзя подделать
    message = data.get('message')
    time_str = data.get('time')
    
    if message:
        db_manager.add_message(nickname, message, time_str)
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "error"}), 400

@app.route('/get', methods=['GET'])
def get_messages():
    return jsonify(db_manager.fetch_all_messages())

if __name__ == "__main__":
    app.run()
