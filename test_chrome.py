#!/usr/bin/env python3
"""Quick test to verify ChromeDriver works after approval."""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("Testing ChromeDriver...")
try:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run without GUI for testing
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get("https://www.google.com")
    print(f"✓ ChromeDriver works! Page title: {driver.title}")
    driver.quit()
    print("\n✅ Ready to run KDP automation!")
except Exception as e:
    print(f"✗ ChromeDriver still blocked: {e}")
    print("\nPlease check System Settings > Privacy & Security")
