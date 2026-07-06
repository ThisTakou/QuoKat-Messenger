#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P2P Мессенджер с конец-в-конец шифрованием (ECDH + AES-256-GCM)
Работает без центрального сервера
Версия: 1.0
"""

import socket
import threading
import hashlib
import secrets
import time
import os
import sys
import json
import uuid
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Криптография
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hmac

# QR-код
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

CONFIG = {
    'UDP_PORT': 5005,           # Порт для обнаружения (broadcast)
    'TCP_PORT': 6006,           # Порт для сообщений
    'BROADCAST_INTERVAL': 2,    # Интервал broadcast поиска (сек)
    'SEARCH_TIMEOUT': 10,       # Таймаут поиска (сек)
    'ID_FILE': 'my_id.txt',
    'BUFFER_SIZE': 4096,
    'TCP_BUFFER_SIZE': 65536,
    'SCREEN_WAIT_TIME': 60,     # Время перед очисткой экрана (10-3600 сек, по умолчанию 60)
}

# ============================================================================
# КЛАСС ДЛЯ РАБОТЫ С IP И QR-КОДОМ
# ============================================================================

class NetworkInfo:
    """Получает информацию о сети и генерирует QR-код"""

    @staticmethod
    def get_local_ip() -> str:
        """Получить локальный IP адрес"""
        try:
            # Создаем сокет для определения IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                # Альтернативный метод
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.bind(("", 0))
                s.listen(1)
                conn, addr = s.accept()
                ip = addr[0]
                conn.close()
                s.close()
                return ip
            except:
                return "127.0.0.1"

    @staticmethod
    def get_public_ip() -> Optional[str]:
        """Получить публичный IP через API (если доступно)"""
        try:
            import urllib.request
            response = urllib.request.urlopen('https://api.ipify.org?format=json', timeout=3)
            data = json.loads(response.read().decode())
            return data.get('ip')
        except:
            return None

    @staticmethod
    def generate_qr_code(my_id: str, port: int = 6006) -> Optional[Tuple]:
        """
        Генерировать QR-код с информацией для подключения.
        Возвращает (ASCII представление, QR данные, IP адрес).
        """
        if not QRCODE_AVAILABLE:
            return None

        local_ip = NetworkInfo.get_local_ip()

        # Формируем данные для QR: p2pchat://IP:PORT/ID
        qr_data = f"p2pchat://{local_ip}:{port}/{my_id}"

        try:
            # Генерируем QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Преобразуем в ASCII (черные = ██, белые = ░░)
            qr_ascii = ""
            for row in qr.modules:
                for cell in row:
                    qr_ascii += "██" if cell else "░░"
                qr_ascii += "\n"

            return qr_ascii, qr_data, local_ip

        except Exception as e:
            print(f"⚠️ Ошибка при генерации QR: {e}")
            return None

    @staticmethod
    def print_qr_info(my_id: str, port: int = 6006):
        """Красиво вывести информацию с QR-кодом"""
        print("\n" + "=" * 70)
        print("🔗 ИНФОРМАЦИЯ ДЛЯ ПОДКЛЮЧЕНИЯ")
        print("=" * 70)

        # Получаем IP адреса
        local_ip = NetworkInfo.get_local_ip()
        print(f"\n📍 Локальный IP:    {local_ip}:{port}")

        # Пытаемся получить публичный IP
        public_ip = NetworkInfo.get_public_ip()
        if public_ip:
            print(f"🌍 Публичный IP:    {public_ip}:{port}")
        else:
            print(f"🌍 Публичный IP:    [используйте https://whatismyipaddress.com/]")

        print(f"🔑 Ваш ID:          {my_id}")

        # Генерируем QR-код
        qr_result = NetworkInfo.generate_qr_code(my_id, port)

        if qr_result:
            qr_ascii, qr_data, _ = qr_result
            print("\n📱 Отсканируйте QR-код телефоном:")
            print("─" * 70)
            print(qr_ascii, end="")
            print("─" * 70)
            print(f"\n📲 Друг может отсканировать этот QR для автоматического подключения")
            print(f"   или ввести вручную:")
            print(f"   • Код: {my_id}")
            print(f"   • IP: {local_ip}")
        else:
            print("\n⚠️ QR-код недоступен (установите: pip install qrcode[pil])")
            print(f"   Поделитесь вручную:")
            print(f"   • Код: {my_id}")
            print(f"   • IP: {local_ip}")

        print("=" * 70 + "\n")

# ============================================================================
# КЛАСС ДЛЯ УПРАВЛЕНИЯ ID
# ============================================================================

class IDManager:
    """Генерирует и управляет уникальным ID пользователя"""

    @staticmethod
    def get_mac_address() -> str:
        """Получить MAC-адрес (кроссплатформенно)"""
        return uuid.getnode().to_bytes(6, byteorder='big').hex()

    @staticmethod
    def generate_id() -> str:
        """Генерировать уникальный 8-символьный ID"""
        mac = IDManager.get_mac_address()
        salt = secrets.token_hex(8)
        data = (mac + salt).encode()
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()[:8].upper()

    @staticmethod
    def load_or_create_id(filename: str = 'my_id.txt') -> str:
        """Загрузить ID из файла или создать новый"""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                my_id = f.read().strip()
                if my_id:
                    return my_id

        # Создать новый ID
        my_id = IDManager.generate_id()
        with open(filename, 'w') as f:
            f.write(my_id)
        return my_id

# ============================================================================
# КЛАСС ДЛЯ ШИФРОВАНИЯ
# ============================================================================

class CryptoManager:
    """Управляет криптографией: ECDH ключевой обмен и AES-256-GCM"""

    def __init__(self):
        """Инициализация с генерацией приватного ключа"""
        self.private_key = ec.generate_private_key(
            ec.SECP256R1(), default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.shared_secret = None
        self.cipher_key = None

    def get_public_key_bytes(self) -> bytes:
        """Получить публичный ключ в формате для отправки"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

    def compute_shared_secret(self, peer_public_key_bytes: bytes) -> bytes:
        """Вычислить общий секрет из публичного ключа собеседника"""
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), peer_public_key_bytes
        )

        # Вычисляем общий секрет
        shared_secret = self.private_key.exchange(
            ec.ECDH(), peer_public_key
        )

        # Генерируем криптографический ключ через HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 бит для AES-256
            salt=b'p2p_chat_salt_v1',
            info=b'encryption_key',
            backend=default_backend()
        )

        self.cipher_key = hkdf.derive(shared_secret)
        return self.cipher_key

    def encrypt_message(self, message: str) -> bytes:
        """Зашифровать сообщение AES-256-GCM"""
        if self.cipher_key is None:
            raise ValueError("Ключ шифрования не установлен")

        # Генерируем уникальный nonce (12 байт для GCM)
        nonce = secrets.token_bytes(12)

        # Шифруем
        cipher = AESGCM(self.cipher_key)
        ciphertext = cipher.encrypt(nonce, message.encode(), None)

        # Возвращаем nonce + ciphertext
        return nonce + ciphertext

    def decrypt_message(self, encrypted_data: bytes) -> str:
        """Расшифровать сообщение AES-256-GCM"""
        if self.cipher_key is None:
            raise ValueError("Ключ шифрования не установлен")

        # Извлекаем nonce (первые 12 байт)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Расшифровываем
        cipher = AESGCM(self.cipher_key)
        plaintext = cipher.decrypt(nonce, ciphertext, None)

        return plaintext.decode()

# ============================================================================
# КЛАСС ДЛЯ ОБНАРУЖЕНИЯ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

class PeerDiscovery:
    """Обнаружение пиров в локальной сети (UDP broadcast)"""

    def __init__(self, my_id: str, my_port: int = CONFIG['UDP_PORT']):
        self.my_id = my_id
        self.my_port = my_port
        self.socket = None
        self.running = False
        self.discovered_peers: Dict[str, str] = {}  # {ID: IP_адрес}

    def setup_socket(self):
        """Настроить UDP сокет для broadcast"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Разрешить broadcast
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Привязываем к порту
        self.socket.bind(('', self.my_port))
        self.socket.settimeout(2)

    def send_search_broadcast(self, target_id: str):
        """Отправить broadcast пакет поиска"""
        message = f"SEARCH:{self.my_id}:{target_id}".encode()

        # Определяем broadcast адреса для разных платформ
        broadcast_ips = [
            '<broadcast>',
            '255.255.255.255',
            '192.168.1.255',
            '192.168.0.255',
        ]

        for broadcast_ip in broadcast_ips:
            try:
                self.socket.sendto(message, (broadcast_ip, self.my_port))
            except:
                pass

    def listen_for_broadcasts(self):
        """Слушать входящие broadcast пакеты"""
        self.running = True
        while self.running:
            try:
                data, addr = self.socket.recvfrom(CONFIG['BUFFER_SIZE'])
                message = data.decode()

                # Парсим сообщение: SEARCH:МОЙ_ID:ЦЕЛЕВОЙ_ID
                if message.startswith('SEARCH:'):
                    parts = message.split(':')
                    if len(parts) >= 3:
                        peer_id = parts[1]
                        target_id = parts[2]

                        # Если поиск для нас или общий поиск
                        if peer_id != self.my_id:
                            self.discovered_peers[peer_id] = addr[0]

            except socket.timeout:
                pass
            except Exception as e:
                print(f"⚠️ Ошибка при прослушивании broadcast: {e}")

    def search_peer(self, peer_id: str, timeout: int = CONFIG['SEARCH_TIMEOUT']) -> Optional[str]:
        """Искать пира в локальной сети"""
        self.discovered_peers.clear()
        start_time = time.time()

        # Запускаем поток слушания
        listener_thread = threading.Thread(
            target=self.listen_for_broadcasts,
            daemon=True
        )
        listener_thread.start()

        # Отправляем поиск каждые BROADCAST_INTERVAL секунд
        while time.time() - start_time < timeout:
            self.send_search_broadcast(peer_id)

            # Проверяем, найден ли пир
            if peer_id in self.discovered_peers:
                self.running = False
                return self.discovered_peers[peer_id]

            time.sleep(CONFIG['BROADCAST_INTERVAL'])

        self.running = False
        return None

# ============================================================================
# КЛАСС ДЛЯ TCP СОЕДИНЕНИЯ
# ============================================================================

class P2PConnection:
    """Управляет TCP соединением между двумя пирами"""

    def __init__(self, my_id: str, crypto: CryptoManager):
        self.my_id = my_id
        self.crypto = crypto
        self.peer_id: Optional[str] = None
        self.peer_ip: Optional[str] = None
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False

    def connect_to_peer(self, peer_ip: str, peer_port: int = CONFIG['TCP_PORT']) -> bool:
        """Подключиться к пиру (режим клиента)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((peer_ip, peer_port))
            self.peer_ip = peer_ip

            # Отправляем свой ID
            self.socket.send(self.my_id.encode())

            # Ждем принятия
            response = self.socket.recv(CONFIG['BUFFER_SIZE']).decode()
            if response == "OK":
                self.connected = True
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def accept_connection(self, timeout: int = CONFIG['SEARCH_TIMEOUT']) -> bool:
        """Ожидать входящего соединения (режим сервера)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', CONFIG['TCP_PORT']))
            self.socket.listen(1)
            self.socket.settimeout(timeout)

            client_socket, addr = self.socket.accept()

            # Получаем ID пира
            peer_id = client_socket.recv(CONFIG['BUFFER_SIZE']).decode()
            self.peer_id = peer_id
            self.peer_ip = addr[0]

            # Отправляем подтверждение
            client_socket.send(b"OK")

            self.socket = client_socket
            self.connected = True
            return True
        except socket.timeout:
            return False
        except Exception as e:
            print(f"❌ Ошибка при приеме соединения: {e}")
            return False

    def exchange_public_keys(self) -> bool:
        """Обменяться публичными ключами ECDH"""
        try:
            # Сначала ОТПРАВЛЯЕМ свой публичный ключ
            my_key_bytes = self.crypto.get_public_key_bytes()
            self.socket.send(len(my_key_bytes).to_bytes(4, 'big'))
            self.socket.send(my_key_bytes)

            # Потом ПОЛУЧАЕМ публичный ключ пира
            peer_key_size_data = self.socket.recv(4)
            if not peer_key_size_data or len(peer_key_size_data) < 4:
                raise ValueError("Не получен размер ключа пира")

            peer_key_size = int.from_bytes(peer_key_size_data, 'big')

            peer_public_key_bytes = b''
            while len(peer_public_key_bytes) < peer_key_size:
                chunk = self.socket.recv(CONFIG['TCP_BUFFER_SIZE'])
                if not chunk:
                    raise ValueError("Соединение разорвалось при получении ключа")
                peer_public_key_bytes += chunk

            # Вычисляем общий секрет
            self.crypto.compute_shared_secret(peer_public_key_bytes)

            return True
        except Exception as e:
            print(f"❌ Ошибка при обмене ключами: {e}")
            return False

    def send_message(self, message: str) -> bool:
        """Отправить зашифрованное сообщение"""
        try:
            encrypted = self.crypto.encrypt_message(message)

            # Отправляем размер + данные
            size = len(encrypted).to_bytes(4, 'big')
            self.socket.send(size + encrypted)
            return True
        except Exception as e:
            print(f"❌ Ошибка при отправке: {e}")
            return False

    def receive_message(self) -> Optional[str]:
        """Получить расшифрованное сообщение"""
        try:
            # Получаем размер
            size_data = self.socket.recv(4)
            if not size_data:
                return None

            size = int.from_bytes(size_data, 'big')

            # Получаем данные
            encrypted_data = b''
            while len(encrypted_data) < size:
                chunk = self.socket.recv(CONFIG['TCP_BUFFER_SIZE'])
                if not chunk:
                    break
                encrypted_data += chunk

            # Расшифровываем
            message = self.crypto.decrypt_message(encrypted_data)
            return message
        except Exception as e:
            return None

    def close(self):
        """Закрыть соединение"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False

# ============================================================================
# ГЛАВНЫЙ КЛАСС ПРИЛОЖЕНИЯ
# ============================================================================

class P2PMessenger:
    """Главное приложение мессенджера"""

    def __init__(self):
        self.my_id = IDManager.load_or_create_id()
        self.crypto = CryptoManager()
        self.discovery = PeerDiscovery(self.my_id)
        self.connection = P2PConnection(self.my_id, self.crypto)
        self.running = False
        self.first_run = True  # Флаг для первого запуска

    def clear_screen(self):
        """Очистить консоль"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_sidebar(self):
        """Вывести боковую информацию"""
        local_ip = NetworkInfo.get_local_ip()
        public_ip = NetworkInfo.get_public_ip() or "Loading..."
        print("\n" + "=" * 60)
        print("📊 INFO SIDEBAR")
        print("=" * 60)
        print(f"🔑 Your ID:      {self.my_id}")
        print(f"📍 Local IP:     {local_ip}:{CONFIG['TCP_PORT']}")
        print(f"🌍 Public IP:    {public_ip}")
        print("=" * 60 + "\n")

    def wait_before_clear(self, seconds: int = None):
        """Ждать перед очисткой экрана с отсчетом"""
        if seconds is None:
            seconds = CONFIG['SCREEN_WAIT_TIME']

        # Ограничиваем от 10 до 3600 сек
        seconds = max(10, min(3600, seconds))

        for i in range(seconds, 0, -1):
            print(f"\r⏱️  Экран обновится через {i} сек...", end='', flush=True)
            time.sleep(1)

        print("\r" + " " * 50 + "\r", end='')  # Очистим строку
        self.clear_screen()

    def print_header(self):
        """Вывести заголовок"""
        self.clear_screen()
        print("=" * 60)
        print("🔐 P2P МЕССЕНДЖЕР С ШИФРОВАНИЕМ (ECDH + AES-256-GCM)")
        print("=" * 60)
        print(f"✅ ВАШ УНИКАЛЬНЫЙ КОД: {self.my_id}")
        print("=" * 60)
        print()

    def print_header_with_qr(self):
        """Вывести заголовок с QR-кодом (при первом запуске)"""
        self.clear_screen()
        NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])

    def show_menu(self):
        """Главное меню"""
        if self.first_run:
            # При первом запуске показываем QR-код с информацией
            self.print_header_with_qr()
            self.first_run = False
            print("Выберите действие:")
            print("1. Подключиться к собеседнику (введите код)")
            print("2. Ожидать входящего соединения")
            print("3. Показать QR-код еще раз")
            print("4. Выход")
            print()
            choice = input("Ваш выбор (1-4): ").strip()

            # Обработка дополнительного пункта
            if choice == '4':
                return '3'
            elif choice == '3':
                NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])
                time.sleep(2)
                return self.show_menu()
            return choice
        else:
            # После первого запуска стандартное меню
            self.print_header()
            print("Выберите действие:")
            print("1. Подключиться к собеседнику (введите код)")
            print("2. Ожидать входящего соединения")
            print("3. Показать QR-код")
            print("4. Выход")
            print()

            choice = input("Ваш выбор (1-4): ").strip()

            # Обработка QR-кода
            if choice == '3':
                NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])
                time.sleep(2)
                return self.show_menu()

            return choice

    def mode_connect_to_peer(self):
        """Режим: подключиться к собеседнику"""
        self.print_header()
        self.print_sidebar()

        target_id = input("Введите код собеседника: ").strip().upper()

        if not target_id:
            print("❌ Код не может быть пустым")
            self.wait_before_clear()
            return

        if target_id == self.my_id:
            print("❌ Нельзя подключиться к самому себе")
            self.wait_before_clear()
            return
            return

        print(f"\n🔍 Поиск пользователя {target_id} в локальной сети...")
        self.discovery.setup_socket()

        peer_ip = self.discovery.search_peer(target_id)

        if peer_ip:
            print(f"✅ Найден! IP: {peer_ip}")
            print("🔗 Подключаюсь...")

            if self.connection.connect_to_peer(peer_ip):
                self.connection.peer_id = target_id

                # Обмениваемся ключами
                print("🔑 Обмен ключами шифрования...")
                if self.connection.exchange_public_keys():
                    print("✅ Соединение установлено и защищено!")
                    time.sleep(1)
                    self.start_chat()
                else:
                    print("❌ Ошибка при обмене ключами")
                    self.connection.close()
            else:
                print("❌ Не удалось подключиться")
        else:
            print("❌ Пользователь не найден в локальной сети")
            print("🌐 Попробуем подключиться через интернет...")

            peer_ip = input("Введите IP адрес собеседника (или нажмите Enter для пропуска): ").strip()

            if peer_ip:
                print("🔗 Подключаюсь...")
                if self.connection.connect_to_peer(peer_ip):
                    self.connection.peer_id = target_id

                    print("🔑 Обмен ключами шифрования...")
                    if self.connection.exchange_public_keys():
                        print("✅ Соединение установлено и защищено!")
                        time.sleep(1)
                        self.start_chat()
                    else:
                        print("❌ Ошибка при обмене ключами")
                        self.connection.close()
                else:
                    print("❌ Не удалось подключиться")

        self.wait_before_clear()

    def mode_wait_for_connection(self):
        """Режим: ожидание входящего соединения"""
        self.print_header()
        self.print_sidebar()

        print(f"⏳ Ожидание входящего соединения на порту {CONFIG['TCP_PORT']}...")
        print("(Собеседник должен знать ваш IP адрес и ваш код: " + self.my_id + ")")
        print()

        if self.connection.accept_connection():
            print(f"✅ Входящее соединение от {self.connection.peer_id}")
            print(f"   IP: {self.connection.peer_ip}")

            # Обмениваемся ключами
            print("🔑 Обмен ключами шифрования...")
            if self.connection.exchange_public_keys():
                print("✅ Соединение установлено и защищено!")
                time.sleep(1)
                self.start_chat()
            else:
                print("❌ Ошибка при обмене ключами")
                self.connection.close()
        else:
            print("❌ Таймаут ожидания")

        self.wait_before_clear()

    def start_chat(self):
        """Начать чат"""
        self.clear_screen()
        print("=" * 60)
        print(f"💬 ЧАТ С {self.connection.peer_id}")
        print("=" * 60)
        print("(Введите /exit для выхода)")
        print()

        # Запускаем поток приема сообщений
        receiver_thread = threading.Thread(
            target=self._receive_messages,
            daemon=True
        )
        receiver_thread.start()

        # Главный цикл отправки сообщений
        try:
            while self.connection.connected:
                message = input("Вы: ").strip()

                if message == "/exit":
                    print("👋 Вы вышли из чата")
                    self.connection.close()
                    break

                if message:
                    if self.connection.send_message(message):
                        # Сообщение отправлено успешно
                        pass
                    else:
                        print("❌ Ошибка при отправке сообщения")
                        break
        except KeyboardInterrupt:
            print("\n👋 Отключено пользователем")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        finally:
            self.connection.close()

        time.sleep(2)

    def _receive_messages(self):
        """Поток для приема сообщений"""
        while self.connection.connected:
            message = self.connection.receive_message()

            if message:
                print(f"\n{self.connection.peer_id}: {message}")
                print("Вы: ", end='', flush=True)
            else:
                # Соединение разорвано
                if self.connection.connected:
                    print(f"\n⚠️ Соединение потеряно с {self.connection.peer_id}")
                    self.connection.close()
                break

            time.sleep(0.1)

    def run(self):
        """Главный цикл"""
        while True:
            choice = self.show_menu()

            if choice == '1':
                self.mode_connect_to_peer()
            elif choice == '2':
                self.mode_wait_for_connection()
            elif choice == '3':
                print("👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор")
                time.sleep(1)

# ============================================================================
# ТОЧКА ВХОДА
# ============================================================================

def main():
    """Главная функция"""
    try:
        messenger = P2PMessenger()
        messenger.run()
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
