import os
import re
import sys
import json
import time
import base64
import shutil
import socket
import requests
import urllib.parse

MAX_SERVERS = 25

SOURCES = [
    "https://githubusercontent.com",
    "https://githubusercontent.com",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/clean/vless.txt",
    "https://githubusercontent.com",
    "https://githubusercontent.com",
    "https://githubusercontent.com"
]

CHECKED_FILE = "checked.txt"
SUB_FILE = "subscription.txt"
BASE64_SUB_FILE = "sub_base64.txt"
XRAY_BINARY = "./xray"

def download_xray():
    if os.path.exists(XRAY_BINARY):
        return
    print("Скачивание Xray core")
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
        print("Xray core успешно установлен")
    except Exception as e:
        print(f"Критическая ошибка при скачивании Xray: {e}")

def load_history():
    if os.path.exists(CHECKED_FILE):
        with open(CHECKED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(link):
    with open(CHECKED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{link}\n")

def fetch_links():
    links = []
    pattern = re.compile(r'vless://[^\s]+')
    
    for url in SOURCES:
        try:
            print(f"Парсинг источника: {url}")
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                content = res.text
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
    try:
        after_at = link.split('@')[-1]
        host_port_part = re.split(r'[?#]', after_at)[0]
        
        if ':' in host_port_part:
            host, port = host_port_part.rsplit(':', 1)
            port = int(port)
            with socket.create_connection((host, port), timeout=2.5):
                return True, host
    except Exception:
        pass
    return False, None

def get_country_info(host):
    try:
        time.sleep(1.5)
        res = requests.get(f"http://ip-api.com/json/{host}?fields=countryCode", timeout=5).json()
        return res.get("countryCode", "UN")
    except Exception:
        return "UN"

def get_flag_emoji(country_code):
    if len(country_code) != 2 or country_code == "UN":
        return "🏳️"
    return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

def main():
    download_xray()
    
    history = load_history()
    raw_links = fetch_links()
    
    print(f"Всего собрано уникальных ссылок: {len(raw_links)}")
    
    working_servers = []
    
    for idx, link in enumerate(raw_links):
        if len(working_servers) >= MAX_SERVERS:
            print("Достигнут заданный лимит рабочих серверов")
            break
        
        if link in history:
            continue
            
        is_alive, host = check_proxy_tcp(link)
        save_to_history(link)
        
        if is_alive:
            cc = get_country_info(host)
            working_servers.append({"link": link, "cc": cc})
            print(f"[{idx}] РАБОЧИЙ сервер найден Страна: {cc}")
            
    if working_servers:
        working_servers.sort(key=lambda x: x["cc"])
        
        country_counts = {}
        final_links = []
        
        for server in working_servers:
            cc = server["cc"]
            country_counts[cc] = country_counts.get(cc, 0) + 1
            num = country_counts[cc]
            
            flag = get_flag_emoji(cc)
            raw_name = f"{flag} {cc} | {num} | @FunZaykaShop"
            encoded_name = urllib.parse.quote(raw_name)
            
            base_link = server["link"].split('#')[0]
            new_link = f"{base_link}#{encoded_name}"
            final_links.append(new_link)
            
        headers = [
            "#profile-title: @FunZaykaShop",
            "#profile-update-interval: 1",
            "#announce: По вопросам пишите в поддержку!",
            "#support-url: https://t.me/FunZaykaShop"
        ]
        
        full_text = "\n".join(headers) + "\n" + "\n".join(final_links) + "\n"
        
        with open(SUB_FILE, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        b64_encoded = base64.b64encode(full_text.encode('utf-8')).decode('utf-8')
        with open(BASE64_SUB_FILE, "w", encoding="utf-8") as f:
            f.write(b64_encoded)
            
        print(f"Успешно добавлено новых серверов: {len(working_servers)}")
    else:
        print("Новых рабочих серверов не обнаружено")

if __name__ == "__main__":
    main()
