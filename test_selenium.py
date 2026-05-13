
from selenium import webdriver
import time

driver = webdriver.Chrome()

driver.get("https://www.producthunt.com/search?q=mental+health+ai")

time.sleep(10)

print(driver.page_source[:1000])

input("ENTER")