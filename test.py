from selenium import webdriver
import time

driver = webdriver.Chrome()

driver.get("https://www.producthunt.com/search?q=mental+health+ai")

input("Solve Cloudflare manually then press ENTER")

html = driver.page_source

print(html[:1000])

with open("test.html", "w", encoding="utf-8") as f:
    f.write(html)

driver.quit()