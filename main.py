import os
import re
import sys
import json
import time
import base64
import shutil
import socket
import requests

# --- НАСТРОЙКИ И ИСТОЧНИКИ РАБОЧИХ VLESS ---
SOURCES = [
    # Специализированные VLESS подписки для обхода ограничений в РФ
    "https://githubusercontent.com",
    "https://githubusercontent.com",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
    # Крупные глобальные агрегаторы (автообновление каждые 15-30 минут)
    "https://githubusercontent.com",
    "https://githubusercontent.com",
    "https://githubusercontent.com"
]

# Имена файлов в репозитории GitHub
CHECKED_FILE = "checked.txt"          # Накопительная база (чтобы не проверять повторно)
SUB_FILE = "subscription.txt"          # Рабочая подписка в открытом виде
BASE64_SUB_FILE = "sub_base64.txt"     # Рабочая подписка в Base64 для приложения Happ

XRAY_BINARY = "./xray"

def download_xray():
    """Автоматическое скачивание актуального ядра Xray под текущую ОС (Linux для GitHub Actions)"""
    if os.path.exists(XRAY_BINARY):
        return
    print("Скачивание Xray core...")
    url = "https://github.com"
    try:
        r = requests.get(url, stream=True, timeout=30)
        with open("xray.zip", "wb") as f:
            shutil.copyfileobj(r.raw, f)
            
        import zipfile
        with zipfile.ZipFile("xray.zip", "r") as zip_ref:
            zip_ref.extract("xray", path=".")
            
        os.chmod(XRAY_BINARY, 0o755)
        os.remove("xray.zip")
        print("Xray core успешно установлен.")
    except Exception as e:
        print(f"Критическая ошибка при скачивании Xray: {e}")

def load_history():
    """Загрузка истории проверенных прокси, чтобы исключить лишнюю нагрузку"""
    if os.path.exists(CHECKED_FILE):
        with open(CHECKED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(link):
    """Сохранение конфигурации в накопительный список"""
    with open(CHECKED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

def fetch_links():
    """Сбор и очистка vless-ссылок из источников"""
    links = []
    # Регулярное выражение строго под протокол vless
    pattern = re.compile(r'vless://[^\s]+')
    
    for url in SOURCES:
        try:
            print(f"Парсинг источника: {url}")
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                content = res.text
                # Если контент источника закодирован в base64, декодируем его
                try:
                    content = base64.b64decode(content.strip()).decode('utf-8')
                except Exception:
                    pass
                
                found = pattern.findall(content)
                links.extend(found)
        except Exception as e:
            print(f"Ошибка при запросе к источнику {url}: {e}")
            
    return list(set(links))

def check_proxy_tcp(link):
    """
    Быстрая и надежная валидация доступности порта сервера (TCP-Пинг).
    Извлекает хост и порт из URI формата vless://UUID@HOST:PORT...
    """
    try:
        # Извлекаем часть после '@'
        after_at = link.split('@')[-1]
        # Отсекаем параметры после знаков '?' или '#'
        host_port_part = re.split(r'[?#]', after_at)[0]
        
        if ':' in host_port_part:
            host, port = host_port_part.rsplit(':', 1)
            port = int(port)
            
            # Попытка установить сетевое соединение (таймаут 2.5 секунды)
            with socket.create_connection((host, port), timeout=2.5):
                return True
    except Exception:
        pass
    return False

def main():
    download_xray()
    
    history = load_history()
    raw_links = fetch_links()
    
    print(f"Всего собрано уникальных VLESS-ссылок: {len(raw_links)}")
    
    working_links = []
    
    for idx, link in enumerate(raw_links):
        # Если ссылка уже проверялась в прошлых циклах (есть в checked.txt) — пропускаем
        if link in history:
            continue
            
        # Проверяем доступность сервера
        is_alive = check_proxy_tcp(link)
        
        # Вносим в историю, чтобы больше никогда не тестировать этот инстанс повторно
        save_to_history(link)
        
        if is_alive:
            working_links.append(link)
            print(f"[{idx}] РАБОЧИЙ: {link[:60]}...")
            
    # Перезаписываем или дополняем итоговые файлы подписок
    if working_links:
        # 1. Открытый текстовый вид
        with open(SUB_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(working_links) + "\n")
            
        # 2. Формат Base64 подписки для клиента Happ
        sub_content = "\n".join(working_links)
        b64_encoded = base64.b64encode(sub_content.encode('utf-8')).decode('utf-8')
        with open(BASE64_SUB_FILE, "w", encoding="utf-8") as f:
            f.write(b64_encoded)
            
        print(f"Успешно добавлено новых рабочих серверов: {len(working_links)}")
    else:
        print("Новых рабочих VLESS серверов в этой итерации не обнаружено.")

if __name__ == "__main__":
    main()
