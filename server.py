import socket
import threading

# Настройки сервера
HOST = '0.0.0.0'  # Слушать все интерфейсы
PORT = 55555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message):
    for client in clients:
        client.send(message)

def handle(client):
    while True:
        try:
            message = client.recv(1024)
            broadcast(message)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f'{nickname} покинул GagaChat!'.encode('utf-8'))
            nicknames.pop(index)
            break

def receive():
    print("GagaChat Сервер запущен...")
    while True:
        client, address = server.accept()
        print(f"Подключен адрес {str(address)}")

        client.send('NICK'.encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')
        nicknames.append(nickname)
        clients.append(client)

        print(f"Никнейм пользователя: {nickname}")
        broadcast(f"{nickname} присоединился к GagaChat!".encode('utf-8'))
        client.send('Вы подключены к GagaChat!'.encode('utf-8'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

receive()
