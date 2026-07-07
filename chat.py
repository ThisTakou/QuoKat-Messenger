                      
                       
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

              
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hmac

        
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False

                                                                              
CONFIG = {
    'UDP_PORT': 5005,                                             
    'TCP_PORT': 6006,                               
    'BROADCAST_INTERVAL': 2,                                     
    'SEARCH_TIMEOUT': 10,                             
    'ID_FILE': 'my_id.txt',
    'BUFFER_SIZE': 4096,
    'TCP_BUFFER_SIZE': 65536,
    'SCREEN_WAIT_TIME': 10,                                                                 
}

                                                                              
class NetworkInfo:

    @staticmethod
    def get_local_ip() -> str:
        try:
                                              
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                                      
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
        try:
            import urllib.request
            response = urllib.request.urlopen('https://api.ipify.org?format=json', timeout=3)
            data = json.loads(response.read().decode())
            return data.get('ip')
        except:
            return None

    @staticmethod
    def generate_qr_code(my_id: str, port: int = 6006) -> Optional[Tuple]:
        if not QRCODE_AVAILABLE:
            return None

        local_ip = NetworkInfo.get_local_ip()

                                                       
        qr_data = f"p2pchat://{local_ip}:{port}/{my_id}"

        try:
                               
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

                                                           
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
        print("\n" + "=" * 70)
        print("🔗 ИНФОРМАЦИЯ ДЛЯ ПОДКЛЮЧЕНИЯ")
        print("=" * 70)

                            
        local_ip = NetworkInfo.get_local_ip()
        print(f"\n📍 Локальный IP:    {local_ip}:{port}")

                                        
        public_ip = NetworkInfo.get_public_ip()
        if public_ip:
            print(f"🌍 Публичный IP:    {public_ip}:{port}")
        else:
            print(f"🌍 Публичный IP:    [используйте https://whatismyipaddress.com/]")

        print(f"🔑 Ваш ID:          {my_id}")

                           
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

                                                                              
class IDManager:

    @staticmethod
    def get_mac_address() -> str:
        return uuid.getnode().to_bytes(6, byteorder='big').hex()

    @staticmethod
    def generate_id() -> str:
        mac = IDManager.get_mac_address()
        salt = secrets.token_hex(8)
        data = (mac + salt).encode()
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()[:8].upper()

    @staticmethod
    def load_or_create_id(filename: str = 'my_id.txt') -> str:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                my_id = f.read().strip()
                if my_id:
                    return my_id

                          
        my_id = IDManager.generate_id()
        with open(filename, 'w') as f:
            f.write(my_id)
        return my_id

                                                                              
class CryptoManager:

    def __init__(self):
        self.private_key = ec.generate_private_key(
            ec.SECP256R1(), default_backend()
        )
        self.public_key = self.private_key.public_key()
        self.shared_secret = None
        self.cipher_key = None

    def get_public_key_bytes(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )

    def compute_shared_secret(self, peer_public_key_bytes: bytes) -> bytes:
        peer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), peer_public_key_bytes
        )

                                
        shared_secret = self.private_key.exchange(
            ec.ECDH(), peer_public_key
        )

                                                      
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,                       
            salt=b'p2p_chat_salt_v1',
            info=b'encryption_key',
            backend=default_backend()
        )

        self.cipher_key = hkdf.derive(shared_secret)
        return self.cipher_key

    def encrypt_message(self, message: str) -> bytes:
        if self.cipher_key is None:
            raise ValueError("Ключ шифрования не установлен")

                                                       
        nonce = secrets.token_bytes(12)

                 
        cipher = AESGCM(self.cipher_key)
        ciphertext = cipher.encrypt(nonce, message.encode(), None)

                                       
        return nonce + ciphertext

    def decrypt_message(self, encrypted_data: bytes) -> str:
        if self.cipher_key is None:
            raise ValueError("Ключ шифрования не установлен")

                                          
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

                        
        cipher = AESGCM(self.cipher_key)
        plaintext = cipher.decrypt(nonce, ciphertext, None)

        return plaintext.decode()

                                                                              
class PeerDiscovery:

    def __init__(self, my_id: str, my_port: int = CONFIG['UDP_PORT']):
        self.my_id = my_id
        self.my_port = my_port
        self.socket = None
        self.running = False
        self.discovered_peers: Dict[str, str] = {}                  

    def setup_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                             
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                             
        self.socket.bind(('', self.my_port))
        self.socket.settimeout(2)

    def send_search_broadcast(self, target_id: str):
        message = f"SEARCH:{self.my_id}:{target_id}".encode()

                                                         
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
        self.running = True
        while self.running:
            try:
                data, addr = self.socket.recvfrom(CONFIG['BUFFER_SIZE'])
                message = data.decode()

                                                            
                if message.startswith('SEARCH:'):
                    parts = message.split(':')
                    if len(parts) >= 3:
                        peer_id = parts[1]
                        target_id = parts[2]

                                                            
                        if peer_id != self.my_id:
                            self.discovered_peers[peer_id] = addr[0]

            except socket.timeout:
                pass
            except Exception as e:
                print(f"⚠️ Ошибка при прослушивании broadcast: {e}")

    def search_peer(self, peer_id: str, timeout: int = CONFIG['SEARCH_TIMEOUT']) -> Optional[str]:
        self.discovered_peers.clear()
        start_time = time.time()

                                  
        listener_thread = threading.Thread(
            target=self.listen_for_broadcasts,
            daemon=True
        )
        listener_thread.start()

                                                           
        while time.time() - start_time < timeout:
            self.send_search_broadcast(peer_id)

                                      
            if peer_id in self.discovered_peers:
                self.running = False
                return self.discovered_peers[peer_id]

            time.sleep(CONFIG['BROADCAST_INTERVAL'])

        self.running = False
        return None

                                                                              
class P2PConnection:

    def __init__(self, my_id: str, crypto: CryptoManager):
        self.my_id = my_id
        self.crypto = crypto
        self.peer_id: Optional[str] = None
        self.peer_ip: Optional[str] = None
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False

    def connect_to_peer(self, peer_ip: str, peer_port: int = CONFIG['TCP_PORT']) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((peer_ip, peer_port))
            self.peer_ip = peer_ip

                                
            self.socket.send(self.my_id.encode())

                           
            response = self.socket.recv(CONFIG['BUFFER_SIZE']).decode()
            if response == "OK":
                self.connected = True
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False

    def accept_connection(self, timeout: int = CONFIG['SEARCH_TIMEOUT']) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', CONFIG['TCP_PORT']))
            self.socket.listen(1)
            self.socket.settimeout(timeout)

            client_socket, addr = self.socket.accept()

                              
            peer_id = client_socket.recv(CONFIG['BUFFER_SIZE']).decode()
            self.peer_id = peer_id
            self.peer_ip = addr[0]

                                      
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
        try:
                                                    
            my_key_bytes = self.crypto.get_public_key_bytes()
            self.socket.send(len(my_key_bytes).to_bytes(4, 'big'))
            self.socket.send(my_key_bytes)

                                                
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

                                    
            self.crypto.compute_shared_secret(peer_public_key_bytes)

            return True
        except Exception as e:
            print(f"❌ Ошибка при обмене ключами: {e}")
            return False

    def send_message(self, message: str) -> bool:
        try:
            encrypted = self.crypto.encrypt_message(message)

                                        
            size = len(encrypted).to_bytes(4, 'big')
            self.socket.send(size + encrypted)
            return True
        except Exception as e:
            print(f"❌ Ошибка при отправке: {e}")
            return False

    def receive_message(self) -> Optional[str]:
        try:
                             
            size_data = self.socket.recv(4)
            if not size_data:
                return None

            size = int.from_bytes(size_data, 'big')

                             
            encrypted_data = b''
            while len(encrypted_data) < size:
                chunk = self.socket.recv(CONFIG['TCP_BUFFER_SIZE'])
                if not chunk:
                    break
                encrypted_data += chunk

                            
            message = self.crypto.decrypt_message(encrypted_data)
            return message
        except Exception as e:
            return None

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False

                                                                              
class P2PMessenger:

    def __init__(self):
        self.my_id = IDManager.load_or_create_id()
        self.crypto = CryptoManager()
        self.discovery = PeerDiscovery(self.my_id)
        self.connection = P2PConnection(self.my_id, self.crypto)
        self.running = False
        self.first_run = True                            
        self._chat_disconnect_reason = 'exit'                           

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_sidebar(self):
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
        if seconds is None:
            seconds = CONFIG['SCREEN_WAIT_TIME']

                                        
        seconds = max(10, min(3600, seconds))

        for i in range(seconds, 0, -1):
            print(f"\r⏱️  Экран обновится через {i} сек...", end='', flush=True)
            time.sleep(1)

        print("\r" + " " * 50 + "\r", end='')                  
        self.clear_screen()

    def print_header(self):
        self.clear_screen()
        print("=" * 60)
        print("🔐 P2P МЕССЕНДЖЕР С ШИФРОВАНИЕМ (ECDH + AES-256-GCM)")
        print("=" * 60)
        print(f"✅ ВАШ УНИКАЛЬНЫЙ КОД: {self.my_id}")
        print("=" * 60)
        print()

    def print_header_with_qr(self):
        self.clear_screen()
        NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])

    def show_menu(self):
        if self.first_run:
                                                                
            self.print_header_with_qr()
            self.first_run = False
            print("Выберите действие:")
            print("1. Подключиться к собеседнику (введите код)")
            print("2. Ожидать входящего соединения")
            print("3. Показать QR-код еще раз")
            print("4. Выход")
            print()
            choice = input("Ваш выбор (1-4): ").strip()

                                              
            if choice == '4':
                return '3'
            elif choice == '3':
                NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])
                time.sleep(2)
                return self.show_menu()
            return choice
        else:
                                                    
            self.print_header()
            print("Выберите действие:")
            print("1. Подключиться к собеседнику (введите код)")
            print("2. Ожидать входящего соединения")
            print("3. Показать QR-код")
            print("4. Выход")
            print()

            choice = input("Ваш выбор (1-4): ").strip()

                               
            if choice == '3':
                NetworkInfo.print_qr_info(self.my_id, CONFIG['TCP_PORT'])
                time.sleep(2)
                return self.show_menu()

            return choice

    def mode_connect_to_peer(self):
        self.print_header()
        self.print_sidebar()

        print("Выберите способ подключения:")
        print("1. По ID (поиск в локальной сети + вручную IP)")
        print("2. По IP (введи IP напрямую)")
        print()

        method = input("Выбор (1-2): ").strip()

        if method == '1':
            self.connect_by_id()
        elif method == '2':
            self.connect_by_ip()
        else:
            print("❌ Неверный выбор")
            self.wait_before_clear()

    def connect_by_id(self):
        target_id = input("\nВведите код собеседника: ").strip().upper()

        if not target_id:
            print("❌ Код не может быть пустым")
            self.wait_before_clear()
            return

        if target_id == self.my_id:
            print("❌ Нельзя подключиться к самому себе")
            self.wait_before_clear()
            return

        print(f"\n🔍 Поиск пользователя {target_id} в локальной сети...")
        self.discovery.setup_socket()

        peer_ip = self.discovery.search_peer(target_id)

        if peer_ip:
            print(f"✅ Найден! IP: {peer_ip}")
            if self.attempt_connection(target_id, peer_ip):
                self._run_chat_with_reconnect(target_id, peer_ip)
        else:
            print("❌ Пользователь не найден в локальной сети")
            peer_ip = input("Введите IP адрес вручную (или Enter для пропуска): ").strip()

            if peer_ip:
                if self.attempt_connection(target_id, peer_ip):
                    self._run_chat_with_reconnect(target_id, peer_ip)

        self.wait_before_clear()

    def connect_by_ip(self):
        peer_ip = input("\nВведите IP адрес: ").strip()

        if not peer_ip:
            print("❌ IP не может быть пустым")
            self.wait_before_clear()
            return

        target_id = input("Введите код собеседника: ").strip().upper()

        if not target_id:
            print("❌ Код не может быть пустым")
            self.wait_before_clear()
            return

        if self.attempt_connection(target_id, peer_ip):
            self._run_chat_with_reconnect(target_id, peer_ip)
        self.wait_before_clear()

    def attempt_connection(self, target_id: str, peer_ip: str, silent: bool = False) -> bool:
        if not silent:
            print("🔗 Подключаюсь...")

                                                                          
        self.crypto = CryptoManager()
        self.connection = P2PConnection(self.my_id, self.crypto)

        if not self.connection.connect_to_peer(peer_ip):
            if not silent:
                print("❌ Не удалось подключиться")
            return False

        self.connection.peer_id = target_id

        if not silent:
            print("🔑 Обмен ключами шифрования...")
        if not self.connection.exchange_public_keys():
            if not silent:
                print("❌ Ошибка при обмене ключами")
            self.connection.close()
            return False

        if not silent:
            print("✅ Соединение установлено и защищено!")
            time.sleep(1)
        return True

    def _run_chat_with_reconnect(self, target_id: str, peer_ip: str):
        while True:
            reason = self.start_chat()

            if reason == 'exit':
                                                          
                break

                                              
            print("\n🔄 Автоматическое переподключение...")
            reconnected = False

            for attempt in range(1, 4):
                print(f"   Попытка {attempt}/3 (через 3 сек)...", flush=True)
                time.sleep(3)

                if self.attempt_connection(target_id, peer_ip, silent=True):
                    print(f"✅ Переподключено к {target_id}!")
                    time.sleep(1)
                    reconnected = True
                    break
                else:
                    print(f"   ❌ Попытка {attempt} не удалась")

            if not reconnected:
                print(f"\n❌ Не удалось переподключиться к {target_id} после 3 попыток")
                print("   Возврат в главное меню...")
                time.sleep(3)
                break

    def mode_wait_for_connection(self):
        self.print_header()
        self.print_sidebar()

        print(f"⏳ Ожидание входящего соединения на порту {CONFIG['TCP_PORT']}...")
        print("(Собеседник должен знать ваш IP адрес и ваш код: " + self.my_id + ")")
        print()

        if self.connection.accept_connection():
            peer_id = self.connection.peer_id
            peer_ip = self.connection.peer_ip
            print(f"✅ Входящее соединение от {peer_id}")
            print(f"   IP: {peer_ip}")

                                  
            print("🔑 Обмен ключами шифрования...")
            if self.connection.exchange_public_keys():
                print("✅ Соединение установлено и защищено!")
                time.sleep(1)
                                                                             
                self._run_chat_with_reconnect(peer_id, peer_ip)
            else:
                print("❌ Ошибка при обмене ключами")
                self.connection.close()
        else:
            print("❌ Таймаут ожидания")

        self.wait_before_clear()

    def start_chat(self) -> str:
        self._chat_disconnect_reason = 'disconnect'

        self.clear_screen()
        print("=" * 60)
        print(f"💬 ЧАТ С {self.connection.peer_id}")
        print("=" * 60)
        print("(Введите /exit для выхода)")
        print()

                                          
        receiver_thread = threading.Thread(
            target=self._receive_messages,
            daemon=True
        )
        receiver_thread.start()

                                         
        try:
            while self.connection.connected:
                message = input("Вы: ").strip()

                if message == "/exit":
                    print("👋 Вы вышли из чата")
                    self._chat_disconnect_reason = 'exit'
                    self.connection.close()
                    break

                if message:
                    if not self.connection.send_message(message):
                        print("❌ Ошибка при отправке сообщения")
                        break
        except KeyboardInterrupt:
            print("\n👋 Отключено пользователем")
            self._chat_disconnect_reason = 'exit'
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        finally:
            self.connection.close()

        return self._chat_disconnect_reason

    def _receive_messages(self):
        while self.connection.connected:
            message = self.connection.receive_message()

            if message:
                print(f"\n{self.connection.peer_id}: {message}")
                print("Вы: ", end='', flush=True)
            else:
                                      
                if self.connection.connected:
                    self._chat_disconnect_reason = 'disconnect'
                    self.connection.close()
                    print(f"\n⚠️ Соединение потеряно с {self.connection.peer_id}")
                    print("↩️  Нажмите Enter для переподключения...")
                break

            time.sleep(0.1)

    def run(self):
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

                                                                              
def main():
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
