import requests
from bs4 import BeautifulSoup
import time

url = "https://github.com/search?q=mental+health+ai&type=repositories"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "en-US,en;q=0.9"
}

time.sleep(2)

response = requests.get(url, headers=headers)

print(response.status_code)

if response.status_code == 200:
    with open("github_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)

with open("github_page.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")