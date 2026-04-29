import requests
from bs4 import BeautifulSoup
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

url = "https://www.producthunt.com/search?q=mental+health+ai"

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")

soup = BeautifulSoup(response.text, "html.parser")

links = soup.find_all("a", href=lambda h: h and "/posts/" in h)

print(f"found : {len(links)} produits")

data = []
seen = set()

for link in links:
    name = link.get_text(strip=True)
    href = "https://www.producthunt.com" + link["href"]
    if name and len(name) > 2 and href not in seen:
        seen.add(href)
        data.append({"name": name, "url": href})

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print(f"{len(data)} produits sauvegardés dans data.json")