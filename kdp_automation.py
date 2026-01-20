from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import os
from add_notebook import *
def type_like_a_human(element, text):
    for character in text:
        element.send_keys(character)
        # Sleep for a random time between 0.05 and 0.2 seconds per key
        time.sleep(random.uniform(0.05, 0.1))
def setup_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # Uncomment for headless mode
    options.add_argument("--user-data-dir=./chrome_profile")  # Persist session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def login_to_kdp(driver, email, password):
    driver.get("https://kdp.amazon.com/")
    # Check if already logged in
    try:
        WebDriverWait(driver, 10).until(EC.title_contains("Kindle Direct Publishing"))
        print("Already logged in.")
        return
    except:
        pass  # Not logged in, proceed to login

    try:
        # Wait for login form
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ap_email")))
        driver.find_element(By.ID, "ap_email").send_keys(email)
        # Try different ways for continue
        try:
            driver.find_element(By.ID, "continue").click()
        except:
            driver.find_element(By.XPATH, "//input[@value='Continue' or @aria-label='Continue']").click()
        print("Waiting for password field... If captcha appears, please solve it manually.")
        WebDriverWait(driver, 120).until(EC.presence_of_element_located((By.ID, "ap_password")))
        driver.find_element(By.ID, "ap_password").send_keys(password)
        driver.find_element(By.ID, "signInSubmit").click()
        # Wait for login to complete
        WebDriverWait(driver, 60).until(EC.title_contains("Kindle Direct Publishing"))
        print(f"Logged in successfully. Current URL: {driver.current_url}, Title: {driver.title}")
    except Exception as e:
        print(f"Login failed: {e}")
        driver.save_screenshot("login_error.png")
        raise

def fill_book_details(driver, title, subtitle, author_first, author_last, description, keywords, is_low_content=True):
    try:
        print(f"Navigating to {ADD_NEW_URL}")
        driver.get(ADD_NEW_URL)
        print(f"Page loaded. URL: {driver.current_url}, Title: {driver.title}")
        print(f"ID_TITLE: [{ID_TITLE}]")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, f"{ID_TITLE}")))
        print("Title field found.")
        # Fill title
        driver.find_element(By.ID, f"{ID_TITLE}").send_keys(title)

        # Fill subtitle
        #driver.find_element(By.ID, f"{ID_SUBTITLE}").send_keys(subtitle)
        type_like_a_human( driver.find_element(By.ID, f"{ID_SUBTITLE}"),subtitle)
        # Fill author
        driver.find_element(By.ID, f"{ID_AUTHOR_FIRST_NAME}").send_keys(author_first)
        driver.find_element(By.ID, f"{ID_AUTHOR_Last_NAME}").send_keys(author_last)


        # 1. Find the hidden element
        hidden_input = driver.find_element(By.ID, ID_COPYRIGHTS)

        # 2. Use JavaScript to set the value attribute directly
        driver.execute_script("arguments[0].value = 'false';", hidden_input)




        # 1. Find the hidden element
        hidden_input = driver.find_element(By.ID, ID_IS_ADULTONLY)

        # 2. Use JavaScript to set the value attribute directly
        driver.execute_script("arguments[0].value = 'false';", hidden_input)
        
        
        # Low content book
        if is_low_content:
            driver.find_element(By.ID, f"{ID_LOW_CONTENT}").click()

        # Keywords
        for i, keyword in enumerate(keywords[:7]):  # Max 7
            driver.find_element(By.ID, f"{ID_KEYWORDS_PREFIX}{i}").send_keys(keyword)

        # Description
        #driver.find_element(By.NAME, DESCRIPTON_INPUT_NAME).send_keys(description)
        driver.find_element(By.ID, "cke_editor1").click()
        driver.execute_script("CKEDITOR.instances['editor1'].setData(arguments[0]);", description)
        #.send_keys(description)
        driver.save_screenshot('screenshot0.png')
        driver.find_element(By.ID,ID_CHOOSE_CATEGORIES_BTN).click()
        driver.save_screenshot('screenshot1.png')

        # Choose categories - this might be complex, for now skip or add later

        # Save and continue
        # driver.find_element(By.ID, f"{ID_SAVE_AND_CONTINUE_BTN}").click()
    except Exception as e:
        print(f"Fill details failed: {e}")
        raise

def upload_cover_and_content(driver, cover_path, content_path):
    # Assuming after save, it goes to content page
    # Note: IDs are placeholders. Inspect KDP page to find actual IDs for upload inputs.
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "cover-upload")))  # Placeholder ID

    # Upload cover
    cover_input = driver.find_element(By.ID, "cover-upload")
    cover_input.send_keys(os.path.abspath(cover_path))

    # Upload manuscript
    manuscript_input = driver.find_element(By.ID, "manuscript-upload")
    manuscript_input.send_keys(os.path.abspath(content_path))

    # Continue
    # driver.find_element(By.ID, "save-and-continue").click()

def automate_kdp_publishing(email, password, colors):
    os.makedirs("out", exist_ok=True)
    driver = setup_driver()
    try:
        login_to_kdp(driver, email, password)

        for color_hex, color_name in colors:
            # Generate cover if not exists
            cover_filename = f"out/cat_notebook_cover_{color_name.replace(' ', '-')}.pdf"
            if not os.path.exists(cover_filename):
                # Call the generate function, but since it's in another file, import or run
                from notebok_cover import generate_kdp_cover
                generate_kdp_cover(
                    title=BOOK_TITLE.upper(),
                    main_color_hex=color_hex,
                    image_filename="lines.png",
                    output_filename=cover_filename
                )

            subtitle = BOOK_SUBTITLE.replace("COLOR", color_name)











            fill_book_details(
                driver,
                title=BOOK_TITLE,
                subtitle=subtitle,
                author_first=AUTHOR_FIRST_NAME,
                author_last=AUTHOR_LAST_NAME,
                description=BOOK_DESCRIPTON,
                keywords=["funny cat lover gifts for women men mom dad",
                           "sarcastic coworker leaving gag gift for office", 
                          "work from home desk accessories essentials wfh",
                            "novelty blank lined notebook journal diary pad", 
                            "crazy cat lady merchandise birthday christmas",
                            "cute animal pet owner appreciation present"],  # Example
                is_low_content=True
            )

            # upload_cover_and_content(driver, cover_filename, BOOK_CONTENT)

            # Note: This is simplified; KDP has more steps like pricing, etc.
            # You may need to add more functions for subsequent pages

    finally:
        print("DONE")
        time.sleep(60)
        driver.quit()

if __name__ == "__main__":
    # Replace with actual credentials
    EMAIL = "michallipinski@gmail.com"
    PASSWORD = "kochamGusi3!"

    COLORS = [
        ["#0047AB", "Cobalt Blue"],
        # ["#7b7b7b", "Gray"],
        # ["#7bc4c4", "AQUA SKY"],
        # ["#a07bc4", "Amethyst"],
        # ["#c47b7b", "Old Rose"],
        # ["#007b7b", "Teal"],
        # ["#a0c47b", "Sage Green"],
        # ["#0099cc", "Bondi Blue"],
        # ["#ffcc00", "Tangerine Yellow"]
    ]

    automate_kdp_publishing(EMAIL, PASSWORD, COLORS)