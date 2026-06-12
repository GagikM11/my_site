# МЕССЕНДЖЕР ДЛЯ PYTHONISTA
# Версия: 2.3.1
# Дата: 2026-01-12
# 
# 🔧 ИСПРАВЛЕНИЯ ВЕРСИИ 2.3.1:
#   - Увеличен лимит фото до 10MB
#   - Добавлено сжатие фото на клиенте
#   - Показывает прогресс загрузки
#   - Улучшена обработка ошибок

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import socket
import urllib.parse
import os
import re
import hashlib
import base64

# ============= НАСТРОЙКИ =============
VERSION = "2.3.1"
UPLOAD_FOLDER = 'uploads'
REACTIONS_FOLDER = os.path.join(UPLOAD_FOLDER, 'reactions')
HISTORY_FILE = 'chat_history.json'
DEBUG_MODE = True
MAX_MESSAGES = 500
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB (увеличено)

# ============= СОЗДАНИЕ ПАПОК =============
for folder in [UPLOAD_FOLDER, REACTIONS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)
        print(f"📁 Создана папка: {folder}")

# ============= ХРАНИЛИЩЕ =============
messages = []
users = {}
rooms = ['general', 'random', 'gaming']
current_room = 'general'
message_id = 0

def load_history():
    global messages, message_id
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                messages = data.get('messages', [])
                message_id = data.get('message_id', 0)
                print(f"📂 Загружено {len(messages)} сообщений")
        except Exception as e:
            print(f"Ошибка загрузки: {e}")

def save_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({'messages': messages, 'message_id': message_id}, f, ensure_ascii=False)
        print(f"💾 Сохранено {len(messages)} сообщений")
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

load_history()

class MessengerHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        if DEBUG_MODE:
            print(f"[SERVER] {format % args}")
    
    def do_GET(self):
        try:
            if self.path == '/':
                self.send_html()
            elif self.path.startswith('/get_messages'):
                self.get_messages()
            elif self.path.startswith('/users'):
                self.get_users()
            elif self.path.startswith('/uploads/'):
                self.serve_file()
            elif self.path.startswith('/get_rooms'):
                self.get_rooms()
            elif self.path.startswith('/get_reactions'):
                self.get_reactions()
            else:
                self.send_error(404)
        except Exception as e:
            print(f"❌ Ошибка GET: {e}")
            self.send_error(500, str(e))
    
    def do_POST(self):
        try:
            if self.path == '/login':
                self.login_user()
            elif self.path == '/register':
                self.register_user()
            elif self.path == '/send_message':
                self.send_message()
            elif self.path == '/edit_message':
                self.edit_message()
            elif self.path == '/send_photo':
                self.send_photo()
            elif self.path == '/delete_message':
                self.delete_message()
            elif self.path == '/add_reaction':
                self.add_reaction()
            elif self.path == '/logout':
                self.logout_user()
            elif self.path == '/clear_chat':
                self.clear_chat()
            elif self.path == '/change_room':
                self.change_room()
            elif self.path == '/delete_all_messages':
                self.delete_all_messages()
            else:
                self.send_error(404)
        except Exception as e:
            print(f"❌ Ошибка POST: {e}")
            self.send_error(500, str(e))
    
    def send_photo(self):
        """ОТПРАВКА ФОТО - С УВЕЛИЧЕННЫМ ЛИМИТОМ"""
        global message_id
        
        print("📷 ПОЛУЧЕН ЗАПРОС НА ОТПРАВКУ ФОТО")
        
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            print("❌ Нет данных")
            self.send_response(400)
            self.end_headers()
            return
        
        if content_length > MAX_IMAGE_SIZE + 10000:  # +10KB на данные формы
            print(f"❌ Файл слишком большой: {content_length} > {MAX_IMAGE_SIZE}")
            self.send_response(413)  # Payload Too Large
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        print(f"📷 Данные получены, длина: {len(post_data)}")
        
        params = urllib.parse.parse_qs(post_data)
        username = params.get('username', [''])[0]
        image_data = params.get('image', [''])[0]
        
        print(f"📷 Пользователь: {username}")
        print(f"📷 Длина изображения: {len(image_data)} символов")
        
        if username and image_data and image_data.startswith('data:image'):
            try:
                # Извлекаем данные изображения
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                
                file_size_kb = len(image_bytes) / 1024
                print(f"📷 Размер изображения: {file_size_kb:.2f} KB")
                
                if len(image_bytes) > MAX_IMAGE_SIZE:
                    print(f"❌ Изображение слишком большое: {len(image_bytes)} > {MAX_IMAGE_SIZE}")
                    self.send_response(413)
                    self.end_headers()
                    return
                
                # Сохраняем файл
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                # Определяем расширение
                if 'png' in header:
                    ext = 'png'
                elif 'jpeg' in header or 'jpg' in header:
                    ext = 'jpg'
                else:
                    ext = 'jpg'
                
                filename = f"photo_{timestamp}.{ext}"
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                
                with open(file_path, 'wb') as f:
                    f.write(image_bytes)
                
                print(f"📷 Фото сохранено: {filename} ({file_size_kb:.2f} KB)")
                
                # Создаём сообщение
                message_id += 1
                file_url = f'/uploads/{filename}'
                
                msg = {
                    'id': message_id,
                    'username': username,
                    'room': current_room,
                    'image_url': file_url,
                    'timestamp': datetime.now().timestamp() * 1000
                }
                
                messages.append(msg)
                save_history()
                print(f"📷 Сообщение с фото создано: id={message_id}")
                
                self.send_response(200)
                self.end_headers()
                return
                
            except Exception as e:
                print(f"❌ Ошибка сохранения фото: {e}")
                self.send_response(500)
                self.end_headers()
                return
        
        print("❌ Неверные данные для фото")
        self.send_response(400)
        self.end_headers()
    
    def get_reactions(self):
        """Получить реакции для сообщения"""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        msg_id = params.get('msg_id', ['0'])[0]
        
        reactions_file = os.path.join(REACTIONS_FOLDER, f'reactions_{msg_id}.json')
        reactions = {}
        if os.path.exists(reactions_file):
            try:
                with open(reactions_file, 'r') as f:
                    reactions = json.load(f)
            except:
                pass
        
        response = json.dumps(reactions)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode())
    
    def add_reaction(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        msg_id = params.get('message_id', ['0'])[0]
        username = params.get('username', [''])[0]
        emoji = params.get('emoji', [''])[0]
        
        reactions_file = os.path.join(REACTIONS_FOLDER, f'reactions_{msg_id}.json')
        reactions = {}
        if os.path.exists(reactions_file):
            with open(reactions_file, 'r') as f:
                reactions = json.load(f)
        
        if username not in reactions:
            reactions[username] = []
        
        if emoji in reactions[username]:
            reactions[username].remove(emoji)
        else:
            reactions[username].append(emoji)
        
        with open(reactions_file, 'w') as f:
            json.dump(reactions, f)
        
        self.send_response(200)
        self.end_headers()
    
    def delete_all_messages(self):
        global messages, message_id
        print(f"🗑 УДАЛИТЬ ВСЕ: было {len(messages)} сообщений")
        messages = []
        message_id = 0
        save_history()
        print(f"   ✅ УДАЛЕНО! Осталось {len(messages)}")
        self.send_response(200)
        self.end_headers()
    
    def get_rooms(self):
        response = json.dumps({'rooms': rooms, 'current': current_room})
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode())
    
    def change_room(self):
        global current_room, message_id
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            room = params.get('room', ['general'])[0]
            username = params.get('username', [''])[0]
            
            if room in rooms:
                current_room = room
                message_id += 1
                messages.append({
                    'id': message_id,
                    'username': 'Система',
                    'text': f'📍 {username} перешёл в комнату #{room}',
                    'room': room,
                    'timestamp': datetime.now().timestamp() * 1000
                })
                save_history()
        self.send_response(200)
        self.end_headers()
    
    def register_user(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        username = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        
        for ip, user in users.items():
            if user['username'] == username:
                self.send_response(409)
                self.end_headers()
                return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        client_ip = self.client_address[0]
        users[client_ip] = {'username': username, 'password': password_hash, 'room': 'general'}
        
        global message_id
        message_id += 1
        messages.append({
            'id': message_id,
            'username': 'Система',
            'text': f'✨ Новый пользователь {username} зарегистрировался!',
            'room': 'general',
            'timestamp': datetime.now().timestamp() * 1000
        })
        save_history()
        self.send_response(200)
        self.end_headers()
    
    def serve_file(self):
        file_path = self.path[1:]
        full_path = os.path.join(os.getcwd(), file_path)
        if os.path.exists(full_path):
            self.send_response(200)
            if file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                self.send_header('Content-Type', 'image/jpeg')
            elif file_path.endswith('.png'):
                self.send_header('Content-Type', 'image/png')
            elif file_path.endswith('.gif'):
                self.send_header('Content-Type', 'image/gif')
            else:
                self.send_header('Content-Type', 'application/octet-stream')
            self.end_headers()
            with open(full_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            print(f"❌ Файл не найден: {full_path}")
            self.send_error(404)
    
    def edit_message(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        msg_id = int(params.get('message_id', ['0'])[0])
        username = params.get('username', [''])[0]
        new_text = params.get('new_text', [''])[0]
        
        for msg in messages:
            if msg['id'] == msg_id and msg['username'] == username:
                msg['text'] = new_text[:500]
                msg['edited'] = True
                save_history()
                print(f"✏️ Сообщение {msg_id} отредактировано")
                break
        self.send_response(200)
        self.end_headers()
    
    def delete_message(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        message_id_del = int(params.get('message_id', ['0'])[0])
        username = params.get('username', [''])[0]
        
        print(f"🗑 УДАЛЕНИЕ: id={message_id_del}, username={username}")
        
        for i, msg in enumerate(messages):
            if msg['id'] == message_id_del:
                print(f"   НАЙДЕНО: {msg}")
                if 'image_url' in msg:
                    path = msg['image_url'][1:]
                    full_path = os.path.join(os.getcwd(), path)
                    if os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            print(f"   Удалён файл: {path}")
                        except:
                            pass
                messages.pop(i)
                save_history()
                print(f"   ✅ УДАЛЕНО! Осталось {len(messages)}")
                self.send_response(200)
                self.end_headers()
                return
        
        print(f"   ❌ НЕ НАЙДЕНО сообщение с id={message_id_del}")
        self.send_response(404)
        self.end_headers()
    
    def clear_chat(self):
        global messages, message_id
        messages = []
        message_id = 0
        save_history()
        self.send_response(200)
        self.end_headers()
    
    def send_html(self):
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Мессенджер v2.3.1</title>
    <style>
        * {
            -webkit-tap-highlight-color: transparent !important;
            -webkit-touch-callout: none !important;
            user-select: none !important;
        }
        body {
            font-family: -apple-system, sans-serif;
            background: #f8f9fa;
            height: 100vh;
            display: flex;
            flex-direction: column;
            margin: 0;
        }
        .header {
            background: #007aff;
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: bold;
            font-size: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .debug-toggle {
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 10px;
            cursor: pointer;
        }
        .login-panel, .register-panel {
            background: white;
            margin: 20px;
            padding: 20px;
            border-radius: 12px;
        }
        .login-panel input, .register-panel input {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        .login-panel button, .register-panel button {
            width: 100%;
            padding: 12px;
            background: #007aff;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            font-size: 16px;
            cursor: pointer;
        }
        .switch-btn {
            background: #34c759 !important;
            margin-top: 10px;
        }
        .chat-container {
            display: none;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .top-bar {
            background: white;
            padding: 10px 15px;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }
        .rooms-select {
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        .online-info {
            font-size: 12px;
            color: #666;
        }
        .delete-all-btn {
            background: #ff3b30;
            border: none;
            color: white;
            padding: 5px 10px;
            border-radius: 10px;
            font-size: 12px;
            cursor: pointer;
        }
        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            display: flex;
            flex-direction: column;
        }
        .message {
            max-width: 80%;
            padding: 8px 12px;
            border-radius: 18px;
            margin-bottom: 8px;
            transition: transform 0.1s ease;
        }
        .message.pressed {
            transform: scale(0.97);
            opacity: 0.7;
        }
        .my {
            background: #007aff;
            color: white;
            align-self: flex-end;
            margin-left: auto;
        }
        .other {
            background: #e9ecef;
            color: #333;
            align-self: flex-start;
        }
        .system {
            background: #fff3cd;
            color: #856404;
            align-self: center;
            font-size: 12px;
            padding: 5px 12px;
            border-radius: 15px;
            max-width: 90%;
            margin: 8px auto;
        }
        .reactions {
            display: flex;
            gap: 5px;
            margin-top: 5px;
            flex-wrap: wrap;
        }
        .reaction {
            background: rgba(0,0,0,0.1);
            padding: 2px 6px;
            border-radius: 12px;
            font-size: 12px;
            cursor: pointer;
        }
        .my .reaction {
            background: rgba(255,255,255,0.2);
        }
        .input-area {
            display: flex;
            padding: 10px 15px;
            background: white;
            border-top: 1px solid #ddd;
            gap: 8px;
        }
        .input-area input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 14px;
        }
        .input-area button {
            padding: 10px 20px;
            background: #007aff;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
        }
        .file-btn {
            background: #34c759;
        }
        .debug-panel {
            display: none;
            background: #1a1a2e;
            color: #0f0;
            font-family: monospace;
            font-size: 11px;
            max-height: 200px;
            overflow-y: auto;
            border-top: 2px solid #007aff;
        }
        .debug-panel.show {
            display: block;
        }
        .debug-header {
            background: #007aff;
            color: white;
            padding: 5px 10px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .debug-clear {
            background: #ff3b30;
            border: none;
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            cursor: pointer;
            font-size: 10px;
        }
        .debug-log {
            padding: 5px 10px;
            border-bottom: 1px solid #333;
            font-size: 10px;
        }
        .debug-log.error {
            color: #ff6b6b;
        }
        .debug-log.success {
            color: #6bcb77;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        .modal img {
            max-width: 90%;
            max-height: 90%;
        }
        .edit-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 3000;
            justify-content: center;
            align-items: center;
        }
        .edit-modal-content {
            background: white;
            padding: 20px;
            border-radius: 12px;
            width: 280px;
        }
        .edit-modal-content textarea {
            width: 100%;
            padding: 8px;
            margin: 10px 0;
        }
        .context-menu {
            position: fixed;
            background: rgba(30,30,40,0.95);
            border-radius: 12px;
            z-index: 4000;
            min-width: 160px;
            overflow: hidden;
        }
        .context-menu-item {
            padding: 12px 16px;
            color: white;
            cursor: pointer;
            font-size: 15px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .context-menu-item:active {
            background: rgba(255,255,255,0.2);
        }
        .toast {
            position: fixed;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            z-index: 5000;
        }
        .reaction-picker {
            position: fixed;
            background: white;
            border-radius: 12px;
            padding: 10px;
            display: flex;
            gap: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 4500;
        }
        .reaction-picker span {
            font-size: 24px;
            cursor: pointer;
            padding: 5px;
        }
        .image-preview {
            max-width: 200px;
            max-height: 150px;
            border-radius: 10px;
            margin: 5px 0;
        }
        .compress-note {
            font-size: 10px;
            color: #666;
            text-align: center;
            padding: 5px;
        }
    </style>
</head>
<body>
    <div class="header">
        📱 Мессенджер v2.3.1
        <button class="debug-toggle" onclick="toggleDebug()">🐛 Отладка</button>
    </div>
    
    <div id="loginPanel" class="login-panel">
        <h3>🔐 Вход</h3>
        <input type="text" id="loginUsername" placeholder="Имя">
        <input type="password" id="loginPassword" placeholder="Пароль">
        <button onclick="login()">Войти</button>
        <button class="switch-btn" onclick="showRegister()">📝 Регистрация</button>
    </div>
    
    <div id="registerPanel" class="register-panel" style="display:none">
        <h3>📝 Регистрация</h3>
        <input type="text" id="regUsername" placeholder="Имя">
        <input type="password" id="regPassword" placeholder="Пароль">
        <button onclick="register()">Зарегистрироваться</button>
        <button class="switch-btn" onclick="showLogin()">🔐 Вход</button>
    </div>
    
    <div id="chatContainer" class="chat-container">
        <div class="top-bar">
            <select id="roomSelect" class="rooms-select" onchange="changeRoom()">
                <option value="general">💬 Общий</option>
                <option value="random">🎲 Случайный</option>
                <option value="gaming">🎮 Игры</option>
            </select>
            <div>
                <span id="onlineCount" class="online-info">👥 Онлайн: 0</span>
                <button class="delete-all-btn" onclick="deleteAllMessages()">🗑 Всё</button>
            </div>
        </div>
        <div id="messagesList" class="messages-area"></div>
        <div class="compress-note">📸 Фото до 10MB, автоматическое сжатие</div>
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="Сообщение..." autocomplete="off">
            <input type="file" id="photoInput" accept="image/*" style="display:none" onchange="sendPhoto(this)">
            <button class="file-btn" onclick="document.getElementById('photoInput').click()">📷</button>
            <button onclick="sendMessage()">📤</button>
        </div>
    </div>
    
    <div id="debugPanel" class="debug-panel">
        <div class="debug-header">
            <span>🐛 Панель отладки</span>
            <button class="debug-clear" onclick="clearDebugLogs()">Очистить</button>
        </div>
        <div id="debugLogs"></div>
    </div>
    
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span style="position:absolute;top:20px;right:20px;color:white;font-size:30px;">&times;</span>
        <img id="modalImage">
    </div>
    
    <div id="editModal" class="edit-modal">
        <div class="edit-modal-content">
            <h4>✏️ Редактировать</h4>
            <textarea id="editText" rows="3"></textarea>
            <button onclick="saveEdit()" style="background:#007aff;color:white;padding:8px 16px;margin-right:5px;">Сохранить</button>
            <button onclick="closeEditModal()">Отмена</button>
        </div>
    </div>

    <script>
        let currentUser = '';
        let currentRoom = 'general';
        let lastId = 0;
        let currentEditId = null;
        let updateInterval = null;
        let debugEnabled = false;
        
        function debugLog(message, type = 'info') {
            if (!debugEnabled) return;
            const debugDiv = document.getElementById('debugLogs');
            const logEntry = document.createElement('div');
            logEntry.className = 'debug-log ' + type;
            const time = new Date().toLocaleTimeString();
            logEntry.innerHTML = `[${time}] ${message}`;
            debugDiv.appendChild(logEntry);
            logEntry.scrollIntoView();
            while (debugDiv.children.length > 100) {
                debugDiv.removeChild(debugDiv.firstChild);
            }
        }
        
        function toggleDebug() {
            const panel = document.getElementById('debugPanel');
            debugEnabled = !debugEnabled;
            if (debugEnabled) {
                panel.classList.add('show');
                debugLog('🐛 Панель отладки включена');
            } else {
                panel.classList.remove('show');
            }
        }
        
        function clearDebugLogs() {
            document.getElementById('debugLogs').innerHTML = '';
            debugLog('📋 Логи очищены');
        }
        
        function showToast(msg) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.textContent = msg;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 2000);
            if (debugEnabled) debugLog(msg);
        }
        
        async function deleteAllMessages() {
            if (!confirm('Удалить ВСЕ сообщения?')) return;
            try {
                const res = await fetch('/delete_all_messages', {method: 'POST'});
                if (res.ok) {
                    showToast('✅ Все сообщения удалены!');
                    await fullReload();
                }
            } catch(e) {
                showToast('❌ Ошибка: ' + e.message);
            }
        }
        
        function showRegister() {
            document.getElementById('loginPanel').style.display = 'none';
            document.getElementById('registerPanel').style.display = 'block';
        }
        
        function showLogin() {
            document.getElementById('registerPanel').style.display = 'none';
            document.getElementById('loginPanel').style.display = 'block';
        }
        
        async function register() {
            const username = document.getElementById('regUsername').value.trim();
            const password = document.getElementById('regPassword').value.trim();
            if (!username || !password) {
                alert('Заполните все поля');
                return;
            }
            try {
                const res = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'username=' + encodeURIComponent(username) + '&password=' + encodeURIComponent(password)
                });
                if (res.ok) {
                    showToast('✅ Регистрация успешна!');
                    showLogin();
                } else if (res.status === 409) {
                    alert('❌ Пользователь уже существует');
                } else {
                    alert('❌ Ошибка регистрации');
                }
            } catch(e) {
                alert('Ошибка: ' + e.message);
            }
        }
        
        async function login() {
            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value.trim();
            if (!username || !password) {
                alert('Введите имя и пароль');
                return;
            }
            try {
                const res = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'username=' + encodeURIComponent(username) + '&password=' + encodeURIComponent(password)
                });
                if (res.ok) {
                    currentUser = username;
                    document.getElementById('loginPanel').style.display = 'none';
                    document.getElementById('chatContainer').style.display = 'flex';
                    await loadRooms();
                    if (updateInterval) clearInterval(updateInterval);
                    await fullReload();
                    updateInterval = setInterval(() => {
                        loadMessages();
                        loadUsers();
                    }, 1000);
                    showToast('👋 Добро пожаловать!');
                } else {
                    alert('❌ Неверное имя или пароль');
                }
            } catch(e) {
                alert('Ошибка: ' + e.message);
            }
        }
        
        async function loadRooms() {
            try {
                const res = await fetch('/get_rooms');
                const data = await res.json();
                currentRoom = data.current;
                document.getElementById('roomSelect').value = currentRoom;
            } catch(e) {}
        }
        
        async function changeRoom() {
            const newRoom = document.getElementById('roomSelect').value;
            try {
                await fetch('/change_room', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'room=' + encodeURIComponent(newRoom) + '&username=' + encodeURIComponent(currentUser)
                });
                currentRoom = newRoom;
                await fullReload();
                showToast('📌 Комната #' + newRoom);
            } catch(e) {}
        }
        
        async function fullReload() {
            lastId = 0;
            document.getElementById('messagesList').innerHTML = '';
            await loadMessages();
        }
        
        async function addReaction(msgId, emoji) {
            try {
                await fetch('/add_reaction', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'message_id=' + msgId + '&username=' + encodeURIComponent(currentUser) + '&emoji=' + encodeURIComponent(emoji)
                });
                await loadMessages();
            } catch(e) {}
        }
        
        function showReactionPicker(event, msgId) {
            event.stopPropagation();
            const existing = document.querySelector('.reaction-picker');
            if (existing) existing.remove();
            const picker = document.createElement('div');
            picker.className = 'reaction-picker';
            const emojis = ['👍', '❤️', '😂', '😮', '😢', '😡'];
            emojis.forEach(emoji => {
                const span = document.createElement('span');
                span.textContent = emoji;
                span.onclick = () => {
                    addReaction(msgId, emoji);
                    picker.remove();
                };
                picker.appendChild(span);
            });
            let x = event.clientX || event.touches?.[0]?.clientX || 0;
            let y = event.clientY || event.touches?.[0]?.clientY || 0;
            picker.style.left = x + 'px';
            picker.style.top = y + 'px';
            document.body.appendChild(picker);
            setTimeout(() => {
                document.addEventListener('click', function closePicker(e) {
                    if (!picker.contains(e.target)) {
                        picker.remove();
                        document.removeEventListener('click', closePicker);
                    }
                });
            }, 100);
        }
        
        function formatTime(ts) {
            return new Date(ts).toLocaleTimeString('ru-RU', {hour:'2-digit',minute:'2-digit'});
        }
        
        function openImage(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').style.display = 'flex';
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        function openEditModal(id, text) {
            currentEditId = id;
            document.getElementById('editText').value = text;
            document.getElementById('editModal').style.display = 'flex';
        }
        
        function closeEditModal() {
            document.getElementById('editModal').style.display = 'none';
            currentEditId = null;
        }
        
        async function saveEdit() {
            const newText = document.getElementById('editText').value.trim();
            if (!newText || !currentEditId) return;
            try {
                const res = await fetch('/edit_message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'message_id=' + currentEditId + '&username=' + encodeURIComponent(currentUser) + '&new_text=' + encodeURIComponent(newText)
                });
                if (res.ok) {
                    showToast('✅ Отредактировано');
                    closeEditModal();
                    await fullReload();
                }
            } catch(e) {}
        }
        
        async function deleteMessage(id) {
            if (!confirm('Удалить сообщение?')) return;
            try {
                const res = await fetch('/delete_message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'message_id=' + id + '&username=' + encodeURIComponent(currentUser)
                });
                if (res.ok) {
                    showToast(`✅ Сообщение удалено!`);
                    await fullReload();
                } else {
                    showToast(`❌ Ошибка удаления`);
                }
            } catch(e) {
                showToast(`❌ Ошибка: ${e.message}`);
            }
        }
        
        // Функция сжатия изображения
        function compressImage(file, maxSizeMB, callback) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = new Image();
                img.onload = function() {
                    let width = img.width;
                    let height = img.height;
                    let quality = 0.9;
                    
                    // Если изображение слишком большое, уменьшаем размер
                    const maxDimension = 1200;
                    if (width > maxDimension || height > maxDimension) {
                        if (width > height) {
                            height = Math.round(height * maxDimension / width);
                            width = maxDimension;
                        } else {
                            width = Math.round(width * maxDimension / height);
                            height = maxDimension;
                        }
                    }
                    
                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);
                    
                    // Пробуем сжать до нужного размера
                    let result = canvas.toDataURL('image/jpeg', quality);
                    while (result.length > maxSizeMB * 1024 * 1024 && quality > 0.3) {
                        quality -= 0.1;
                        result = canvas.toDataURL('image/jpeg', quality);
                    }
                    
                    debugLog(`📷 Сжато: ${(file.size/1024).toFixed(1)}KB -> ${(result.length/1024).toFixed(1)}KB (качество ${Math.round(quality*100)}%)`);
                    callback(result);
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
        
        async function sendPhoto(input) {
            if (!input.files || !input.files[0]) {
                debugLog('❌ Файл не выбран', 'error');
                return;
            }
            
            const file = input.files[0];
            const fileSizeMB = file.size / (1024 * 1024);
            debugLog(`📷 Выбран файл: ${file.name}, размер: ${fileSizeMB.toFixed(2)}MB`);
            
            if (fileSizeMB > 10) {
                debugLog('❌ Файл слишком большой (>10MB)', 'error');
                showToast('❌ Файл слишком большой (>10MB)');
                input.value = '';
                return;
            }
            
            if (!file.type.startsWith('image/')) {
                debugLog('❌ Выбран не image файл', 'error');
                showToast('❌ Пожалуйста, выберите изображение');
                input.value = '';
                return;
            }
            
            showToast('📷 Сжатие фото...');
            debugLog('📷 Начинаем сжатие...');
            
            compressImage(file, 5, async function(compressedDataUrl) {
                debugLog('📷 Сжатие завершено, отправка на сервер...');
                showToast('📷 Отправка фото...');
                
                try {
                    const res = await fetch('/send_photo', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                        body: 'username=' + encodeURIComponent(currentUser) + '&image=' + encodeURIComponent(compressedDataUrl)
                    });
                    
                    debugLog(`📷 Ответ сервера: ${res.status}`);
                    if (res.ok) {
                        showToast('✅ Фото отправлено!');
                        await fullReload();
                    } else if (res.status === 413) {
                        showToast('❌ Фото слишком большое даже после сжатия');
                        debugLog('❌ Фото слишком большое', 'error');
                    } else {
                        showToast('❌ Ошибка отправки фото');
                        debugLog('❌ Ошибка отправки фото', 'error');
                    }
                } catch(e) {
                    debugLog(`❌ Ошибка: ${e.message}`, 'error');
                    showToast('❌ Ошибка: ' + e.message);
                }
            });
            input.value = '';
        }
        
        function showMenu(event, id, text, isMy) {
            event.preventDefault();
            event.stopPropagation();
            
            debugLog(`📋 Меню для сообщения ${id}, своё: ${isMy}`);
            
            const existing = document.querySelector('.context-menu');
            if (existing) existing.remove();
            
            const menu = document.createElement('div');
            menu.className = 'context-menu';
            
            if (isMy) {
                const editItem = document.createElement('div');
                editItem.className = 'context-menu-item';
                editItem.innerHTML = '✏️ Редактировать';
                editItem.onclick = () => {
                    menu.remove();
                    openEditModal(id, text);
                };
                menu.appendChild(editItem);
                
                const deleteItem = document.createElement('div');
                deleteItem.className = 'context-menu-item';
                deleteItem.innerHTML = '🗑 Удалить';
                deleteItem.onclick = () => {
                    menu.remove();
                    deleteMessage(id);
                };
                menu.appendChild(deleteItem);
            }
            
            const reactItem = document.createElement('div');
            reactItem.className = 'context-menu-item';
            reactItem.innerHTML = '😊 Реакция';
            reactItem.onclick = (e) => {
                menu.remove();
                showReactionPicker(e, id);
            };
            menu.appendChild(reactItem);
            
            document.body.appendChild(menu);
            
            let x = event.clientX || event.touches?.[0]?.clientX || 0;
            let y = event.clientY || event.touches?.[0]?.clientY || 0;
            
            setTimeout(() => {
                const menuRect = menu.getBoundingClientRect();
                const windowWidth = window.innerWidth;
                let left = (windowWidth - menuRect.width) / 2;
                if (left < 10) left = 10;
                menu.style.left = left + 'px';
                menu.style.top = y - menuRect.height / 2 + 'px';
            }, 10);
            
            setTimeout(() => {
                document.addEventListener('click', function close(e) {
                    if (!menu.contains(e.target)) {
                        menu.remove();
                        document.removeEventListener('click', close);
                    }
                });
            }, 100);
        }
        
        async function loadReactions(msgId, container) {
            try {
                const res = await fetch('/get_reactions?msg_id=' + msgId);
                const reactions = await res.json();
                container.innerHTML = '';
                for (const [user, emojis] of Object.entries(reactions)) {
                    for (const emoji of emojis) {
                        const span = document.createElement('span');
                        span.className = 'reaction';
                        span.textContent = emoji;
                        span.onclick = (e) => {
                            e.stopPropagation();
                            addReaction(msgId, emoji);
                        };
                        container.appendChild(span);
                    }
                }
            } catch(e) {}
        }
        
        function addMessage(msg) {
            const div = document.createElement('div');
            const time = formatTime(msg.timestamp);
            if (msg.username === 'Система') {
                div.className = 'message system';
                div.innerHTML = `${msg.text}<div style="font-size:10px;margin-top:3px">${time}</div>`;
            } else {
                const isMy = msg.username === currentUser;
                div.className = 'message ' + (isMy ? 'my' : 'other');
                let content = '';
                if (msg.image_url) {
                    content += `<img src="${msg.image_url}" class="image-preview" onclick="openImage('${msg.image_url}')">`;
                }
                if (msg.text) {
                    content += `<div>${escapeHtml(msg.text)}${msg.edited ? ' <span style="font-size:10px">(ред.)</span>' : ''}</div>`;
                }
                const reactionsDiv = document.createElement('div');
                reactionsDiv.className = 'reactions';
                div.innerHTML = `<strong>${isMy ? 'Вы' : escapeHtml(msg.username)}</strong><br>${content}<div style="font-size:10px;margin-top:3px">${time}</div>`;
                div.appendChild(reactionsDiv);
                
                let pressTimer;
                div.addEventListener('touchstart', (e) => {
                    div.classList.add('pressed');
                    pressTimer = setTimeout(() => {
                        div.classList.remove('pressed');
                        showMenu(e, msg.id, msg.text, isMy);
                        pressTimer = null;
                    }, 500);
                });
                div.addEventListener('touchend', () => {
                    if (pressTimer) {
                        clearTimeout(pressTimer);
                        pressTimer = null;
                    }
                    div.classList.remove('pressed');
                });
                div.addEventListener('touchmove', () => {
                    if (pressTimer) {
                        clearTimeout(pressTimer);
                        pressTimer = null;
                    }
                    div.classList.remove('pressed');
                });
                
                loadReactions(msg.id, reactionsDiv);
            }
            document.getElementById('messagesList').appendChild(div);
            div.scrollIntoView({ behavior: 'smooth' });
        }
        
        function escapeHtml(t) {
            if (!t) return '';
            return t.replace(/[&<>]/g, function(m) {
                if (m === '&') return '&amp;';
                if (m === '<') return '&lt;';
                if (m === '>') return '&gt;';
                return m;
            });
        }
        
        async function loadMessages() {
            try {
                const res = await fetch('/get_messages?last_id=' + lastId + '&room=' + currentRoom + '&t=' + Date.now());
                const data = await res.json();
                if (data.messages && data.messages.length) {
                    for (const msg of data.messages) {
                        if (msg.id > lastId) {
                            addMessage(msg);
                            lastId = msg.id;
                        }
                    }
                }
            } catch(e) {
                debugLog(`Ошибка загрузки: ${e.message}`, 'error');
            }
        }
        
        async function loadUsers() {
            try {
                const res = await fetch('/users');
                const data = await res.json();
                document.getElementById('onlineCount').innerHTML = '👥 Онлайн: ' + (data.count || 0);
            } catch(e) {}
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const text = input.value.trim();
            if (!text) return;
            try {
                const res = await fetch('/send_message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: 'username=' + encodeURIComponent(currentUser) + '&text=' + encodeURIComponent(text) + '&room=' + encodeURIComponent(currentRoom)
                });
                if (res.ok) {
                    input.value = '';
                    await fullReload();
                }
            } catch(e) {}
        }
        
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        console.log('Мессенджер v2.3.1 запущен');
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_messages(self):
        last_id = 0
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if 'last_id' in params:
            try:
                last_id = int(params['last_id'][0])
            except:
                pass
        
        room = params.get('room', ['general'])[0]
        new_messages = [m for m in messages if m['id'] > last_id and m.get('room', 'general') == room]
        response = json.dumps({'messages': new_messages}, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def get_users(self):
        response = json.dumps({'count': len(users)})
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(response.encode())
    
    def login_user(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            username = params.get('username', [''])[0]
            password = params.get('password', [''])[0]
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        else:
            self.send_response(401)
            self.end_headers()
            return
        
        for ip, user in users.items():
            if user['username'] == username and user['password'] == password_hash:
                client_ip = self.client_address[0]
                users[client_ip] = user
                self.send_response(200)
                self.end_headers()
                return
        self.send_response(401)
        self.end_headers()
    
    def send_message(self):
        global message_id
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
        
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        username = params.get('username', [''])[0]
        text = params.get('text', [''])[0]
        room = params.get('room', ['general'])[0]
        
        if username and text:
            message_id += 1
            messages.append({
                'id': message_id,
                'username': username,
                'text': text[:500],
                'room': room,
                'timestamp': datetime.now().timestamp() * 1000
            })
            save_history()
            while len(messages) > MAX_MESSAGES:
                messages.pop(0)
        self.send_response(200)
        self.end_headers()
    
    def logout_user(self):
        self.send_response(200)
        self.end_headers()

def find_free_port():
    for port in range(8000, 9000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

def run_server():
    port = find_free_port()
    if port is None:
        print('❌ Не удалось найти свободный порт!')
        return
    
    server = HTTPServer(('0.0.0.0', port), MessengerHandler)
    local_ip = get_local_ip()
    
    print('=' * 60)
    print(f'📱 МЕССЕНДЖЕР v{VERSION}')
    print('=' * 60)
    print(f'✅ Сервер запущен!')
    print(f'📱 Открой Safari: http://localhost:{port}')
    print(f'💡 Для друзей: http://{local_ip}:{port}')
    print('=' * 60)
    print('📸 ФУНКЦИИ:')
    print('   📷 Отправка фото - кнопка "📷" (до 10MB, сжатие автоматическое)')
    print('   🗑 Удаление - долгое нажатие на своё сообщение')
    print('   ✏️ Редактирование - долгое нажатие → Редактировать')
    print('   😊 Реакции - долгое нажатие → Реакция')
    print('   🐛 Отладка - кнопка в шапке')
    print('=' * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Сервер остановлен')
        save_history()
        server.shutdown()

if __name__ == '__main__':
    run_server()