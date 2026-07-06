# QuoKat-Messenger
Quokat - Secure P2P messenger with ECDH+AES-256-GCM, QR codes &amp; 3 versions - Quokat - защищённый P2P мессенджер с ECDH+AES-256-GCM, QR-кодами и 3 версиями

<img width="1024" height="211" alt="image" src="https://github.com/user-attachments/assets/0e86baf1-2c6a-4e4b-8b44-ca766f06045a" />

RU - https://github.com/ThisTakou/QuoKat-Messenger#-quokat

EN - https://github.com/ThisTakou/QuoKat-Messenger#-quokat-1

# 🔐 Quokat
 
Просто P2P мессенджер между двумя людьми. Никаких серверов, никакого логирования. Все зашифровано.
 
## Зачем это нужно?
 
Вы хотите пообщаться с кем-то приватно? Закиньте ему QR-код или скажите IP - и оба подключитесь. Сообщения шифруются ECDH ключами и не может быть прочитаны никем, кроме вас двоих. Провайдер не видит содержимое, хостер не видит, никто.
 
## Как это работает?
 
1. Запустите программу - она даст вам ID и QR-код
2. Друг либо отсканирует QR, либо просто введет IP и ваш код
3. Начнется обмен ECDH ключами
4. После этого - защищенный чат
 
Все. Никаких логинов, никаких аккаунтов, никакой истории.
 
## Три версии
 
### Early (консоль)
Просто открыл и пишешь. 400 строк кода, минимум зависимостей (только cryptography).
 
```bash
run_early.bat
```
 
### GUI
Окно с кнопками, вкладками, нормальный интерфейс. Для тех кто не хочет консоль.
 
```bash
run_gui.bat
```
 
### Pro
Красиво, с анимациями, спиннер при подключении, градиенты. Если хочешь показать на собеседнике.
 
```bash
run_pro.bat
```
 
## Установка
 
### Windows
```bash
# Скачай, распакуй, запусти
run_early.bat
```
 
Python установится? Скачай с https://python.org (обязательно Add to PATH)
 
### Linux/Ubuntu
```bash
git clone https://github.com/USERNAME/quokat.git
cd quokat
pip3 install -r requirements_early.txt
python3 quokat_early.py
```
 
### macOS
```bash
brew install python3
# потом то же что Linux
```
 
## Шифрование
 
- **ECDH** на эллиптической кривой SECP256R1 (256 бит)
- **AES-256-GCM** для каждого сообщения
- Каждое сообщение свой nonce
- Невозможно подделать (GCM auth tag)
 
Это не наша фишка - это стандарты криптографии. Это то же самое что используется в HTTPS, Signal, WhatsApp.
 
## Тестирование
 
Открой два терминала:
 
**Терминал 1:**
```
python3 quokat_early.py
Choice: 2
⏳ Waiting...
```
 
**Терминал 2:**
```
python3 quokat_early.py
Choice: 1
Peer ID: [скопируй из терминала 1]
Enter IP: 127.0.0.1
```
 
Пишешь в первом - видишь во втором.
 
## Требования
 
- Python 3.7+
- cryptography (для шифрования)
- PyQt5 (только для GUI версии)
- qrcode (опционально, для QR кодов)
 
## Это опасно?
 
Нет. Криптография проверена миллионами устройств. Мы не придумывали свои алгоритмы - используем стандартные.
 
Не используй это для передачи государственных секретов. Используй для приватного общения с друзьями.
 
## Ограничения
 
- Только двое в чате (не группа)
- Нет истории сообщений (когда закроешь - нет)
- Нет файлов (только текст)
- Нет аккаунтов (новый ID каждый раз)
 
Это фишка, не баг. Ты не зависишь от облака, серверов, аккаунтов.
 
## Лицензия
 
MIT - делай что хочешь.
 
---
 
# 🔐 Quokat
 
Just a P2P messenger between two people. No servers, no logging. Everything is encrypted.
 
## Why?
 
You want to chat privately with someone? Send them a QR code or tell them your IP - both of you connect. Messages are encrypted with ECDH keys and no one else can read them. Your ISP doesn't see the content, no hosting provider sees it, nobody.
 
## How it works?
 
1. Run the app - it gives you an ID and QR code
2. Friend scans QR or enters your IP + your code
3. ECDH key exchange happens
4. Secure chat
 
That's it. No logins, no accounts, no history.
 
## Three versions
 
### Early (console)
Just open and type. 400 lines of code, minimal deps (only cryptography).
 
```bash
run_early.bat
```
 
### GUI
Window with buttons, tabs, normal interface. For people who don't want terminal.
 
```bash
run_gui.bat
```
 
### Pro
Beautiful, with animations, spinner on connect, gradients. Show it off to your friend.
 
```bash
run_pro.bat
```
 
## Installation
 
### Windows
```bash
# Download, unzip, run
run_early.bat
```
 
Python not installed? Get it from https://python.org (make sure to check "Add to PATH")
 
### Linux/Ubuntu
```bash
git clone https://github.com/USERNAME/quokat.git
cd quokat
pip3 install -r requirements_early.txt
python3 quokat_early.py
```
 
### macOS
```bash
brew install python3
# then same as Linux
```
 
## Encryption
 
- **ECDH** on SECP256R1 elliptic curve (256-bit)
- **AES-256-GCM** for each message
- Each message has its own nonce
- Can't be forged (GCM auth tag)
 
This isn't our magic - it's cryptography standards. Same stuff used in HTTPS, Signal, WhatsApp.
 
## Testing
 
Open two terminals:
 
**Terminal 1:**
```
python3 quokat_early.py
Choice: 2
⏳ Waiting...
```
 
**Terminal 2:**
```
python3 quokat_early.py
Choice: 1
Peer ID: [copy from terminal 1]
Enter IP: 127.0.0.1
```
 
Type in first - see in second.
 
## Requirements
 
- Python 3.7+
- cryptography (for encryption)
- PyQt5 (GUI version only)
- qrcode (optional, for QR codes)
 
## Is this safe?
 
Yeah. Cryptography is battle-tested by millions of devices. We didn't invent our own algorithms - using standard ones.
 
Don't use this for state secrets. Use it for private chats with friends.
 
## Limitations
 
- Only two people in chat (no group)
- No message history (close app - gone)
- No files (text only)
- No accounts (new ID each time)
 
That's a feature, not a bug. You're not dependent on cloud, servers, accounts.
 
## License
 
MIT - do whatever you want.
