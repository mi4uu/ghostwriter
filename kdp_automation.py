from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        time.sleep(random.uniform(0.05, 0.1))

def setup_driver():
    options = webdriver.ChromeOptions()
    # Temporarily comment out profile to test
    # options.add_argument("--user-data-dir=./chrome_profile")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.maximize_window()
    return driver

def login_to_kdp(driver, email, password):
    driver.get("https://kdp.amazon.com/")
    try:
        WebDriverWait(driver, 5).until(EC.title_contains("Kindle Direct Publishing"))
        print("Already logged in.")
        return
    except:
        pass

    try:
        print("Logging in...")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ap_email")))
        driver.find_element(By.ID, "ap_email").send_keys(email)
        try:
            driver.find_element(By.ID, "continue").click()
        except:
            driver.find_element(By.XPATH, "//input[@value='Continue' or @aria-label='Continue']").click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "ap_password")))
        driver.find_element(By.ID, "ap_password").send_keys(password)
        driver.find_element(By.ID, "signInSubmit").click()
        WebDriverWait(driver, 60).until(EC.title_contains("Kindle Direct Publishing"))
        print("Logged in successfully.")
    except Exception as e:
        print(f"Login failed: {e}")
        raise

def safe_click_js(driver, element):
    """Clicks an element using JavaScript to avoid interception errors."""
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)

def choose_categories(driver, categories):
    """
    Robust category selection: Dropdowns -> Dropdowns -> Checkbox (Leaf).
    """
    print("Starting category selection...")
    try:
        # Wait for the modal to appear
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], div[id^='react-aui-modal-content']"))
        )
        time.sleep(1)
    except:
        print("CRITICAL: Category modal not found.")
        return

    for idx, cat_path in enumerate(categories):
        print(f"--- Processing Path: {cat_path} ---")

        # Click "Add another category" if this is not the first one
        if idx > 0:
            try:
                modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
                add_btn = modal.find_element(By.XPATH, ".//button[contains(text(), 'Add another category')] | .//a[contains(text(), 'Add another category')]")
                safe_click_js(driver, add_btn)
                time.sleep(1.5)
            except Exception:
                pass

        parts = [p.strip() for p in cat_path.split('>')]

        for part_index, part_name in enumerate(parts):
            modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")

            # --- STRATEGY 1: CHECKBOX (Leaf Nodes) ---
            checkbox_found = False
            try:
                # Look for a label containing the text
                xpath_label = f".//label[contains(., \"{part_name}\")]"
                labels = modal.find_elements(By.XPATH, xpath_label)

                for label in labels:
                    if label.is_displayed():
                        # Check if it has a checkbox inside
                        if label.find_elements(By.CSS_SELECTOR, "input[type='checkbox'], i.a-icon-checkbox"):
                            print(f"  Found checkbox for '{part_name}'. Clicking...")
                            safe_click_js(driver, label)
                            checkbox_found = True
                            time.sleep(1)
                            break
            except Exception:
                pass

            if checkbox_found:
                continue

            # --- STRATEGY 2: DROPDOWN (Parent Categories) ---
            # If no checkbox found, look for dropdowns
            print(f"  Looking for dropdown for '{part_name}'...")

            dropdowns = modal.find_elements(By.CSS_SELECTOR, "span[role='button'][data-action='a-dropdown-button']")
            visible_dropdowns = [d for d in dropdowns if d.is_displayed()]

            target_dropdown = None

            # Find the one that says "Select one"
            for d in visible_dropdowns:
                if "Select one" in d.text:
                    target_dropdown = d
                    break

            # Fallback to the last visible dropdown
            if not target_dropdown and visible_dropdowns:
                target_dropdown = visible_dropdowns[-1]

            if target_dropdown:
                # Open the dropdown
                safe_click_js(driver, target_dropdown)

                # Wait for the popover (attached to body)
                try:
                    popover = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".a-popover-inner, #a-popover-content"))
                    )

                    # Find option by text
                    xpath_option = f"//a[contains(@class,'a-dropdown-link') and normalize-space(text())=\"{part_name}\"]"
                    option = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath_option))
                    )
                    print(f"  Found dropdown option '{part_name}'. Clicking...")
                    safe_click_js(driver, option)
                    time.sleep(2)
                except Exception as e:
                    print(f"  Failed to select option '{part_name}' in popover: {e}")
                    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            else:
                print(f"  Error: No dropdown or checkbox found for '{part_name}'")

    print("Saving categories...")
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        done_btn = modal.find_element(By.XPATH, ".//button[contains(text(), 'Save categories') or contains(text(), 'Done')]")
        safe_click_js(driver, done_btn)
        time.sleep(2)
    except Exception as e:
        print(f"Error clicking Save: {e}")

def fill_book_details(driver, title, subtitle, author_first, author_last, description, keywords, is_low_content=True):
    print(f"Navigating to {ADD_NEW_URL}")
    driver.get(ADD_NEW_URL)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, f"{ID_TITLE}")))

    driver.find_element(By.ID, f"{ID_TITLE}").send_keys(title)
    type_like_a_human(driver.find_element(By.ID, f"{ID_SUBTITLE}"), subtitle)
    driver.find_element(By.ID, f"{ID_AUTHOR_FIRST_NAME}").send_keys(author_first)
    driver.find_element(By.ID, f"{ID_AUTHOR_Last_NAME}").send_keys(author_last)

    # Copyrights
    try:
        driver.execute_script("document.getElementById('data-print-book-is-public-domain').value = 'false';")
        driver.find_element(By.ID, "non-public-domain").click()
    except: pass

    # Adult Content
    try:
        no_adult = driver.find_element(By.XPATH, "//input[@type='radio' and contains(@name,'adult') and contains(@value,'false')]")
        driver.execute_script("arguments[0].click();", no_adult)
    except: pass

    # Low Content
    if is_low_content:
        try: driver.find_element(By.ID, f"{ID_LOW_CONTENT}").click()
        except: pass

    # Keywords
    for i, keyword in enumerate(keywords[:7]):
        driver.find_element(By.ID, f"{ID_KEYWORDS_PREFIX}{i}").send_keys(keyword)

    # Description
    try:
        driver.find_element(By.ID, "cke_editor1").click()
        driver.execute_script("CKEDITOR.instances['editor1'].setData(arguments[0]);", description)
    except: pass

    # Categories
    try:
        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, ID_CHOOSE_CATEGORIES_BTN)))
        safe_click_js(driver, btn)
        choose_categories(driver, CATEGORIES)
    except Exception as e:
        print(f"Category error: {e}")

    print("Clicking Save and Continue...")
    try:
        save_btn = driver.find_element(By.ID, f"{ID_SAVE_AND_CONTINUE_BTN}")
        safe_click_js(driver, save_btn)
    except: pass

def fill_content_page(driver, interior_path, cover_path):
    print("--- Starting Content Page Automation ---")
    try:
        # 1. Wait for page load (Check for ISBN button)
        # WebDriverWait(driver, 60).until(
        #     EC.presence_of_element_located((By.ID, "free-print-isbn-btn-announce"))
        # )
        time.sleep(6)
        print("Content page loaded.")

        # 2. Assign ISBN
        # try:
        #     print("Assigning Free ISBN...")
        #     isbn_btn = driver.find_element(By.ID, "free-print-isbn-btn-announce")
        #     safe_click_js(driver, isbn_btn)

        #     confirm_isbn = WebDriverWait(driver, 5).until(
        #         EC.element_to_be_clickable((By.ID, "print-isbn-confirm-button-announce"))
        #     )
        #     safe_click_js(driver, confirm_isbn)
        #     time.sleep(3)
        # except Exception:
        #     print("ISBN assignment skipped (may be already assigned).")

        # 3. Print Options (Black & White, No Bleed, Matte)
        try:
            print("Setting Print Options...")
            # No Bleed
            try:
                no_bleed_btn = driver.find_element(By.XPATH, "//button[contains(., 'No Bleed')] | //button[@value='no_bleed']")
                safe_click_js(driver, no_bleed_btn)
            except: pass

            # Matte
            try:
                matte_btn = driver.find_element(By.XPATH, "//button[contains(., 'Matte')] | //button[@value='matte']")
                safe_click_js(driver, matte_btn)
            except: pass
        except Exception: pass

        # 4. Upload Manuscript
        print(f"Uploading manuscript: {interior_path}")
        try:
            # We target the HIDDEN input element by ID
            interior_input = driver.find_element(By.ID, "data-print-book-publisher-interior-file-upload-AjaxInput")
            abs_path = os.path.abspath(interior_path)
            interior_input.send_keys(abs_path)

            print("Waiting for manuscript upload to process...")
            # Wait for the success message element to appear
            WebDriverWait(driver, 180).until(
                EC.presence_of_element_located((By.ID, "data-print-book-publisher-interior-file-upload-success"))
            )
            print("Manuscript uploaded successfully.")
        except Exception as e:
            print(f"Error uploading manuscript: {e}")

        # 5. Upload Cover
        print(f"Uploading cover: {cover_path}")
        try:
            # Click 'Upload a cover you already have' based on the text provided
            print("Selecting 'Upload a cover you already have'...")
            try:
                upload_choice_header = driver.find_element(By.XPATH, "//span[contains(text(), 'Upload a cover you already have')]")
                safe_click_js(driver, upload_choice_header)
            except:
                # Fallback to accordion ID
                upload_choice_btn = driver.find_element(By.XPATH, "//div[@data-a-accordion-row-name='UPLOAD']//button | //div[@data-a-accordion-row-name='UPLOAD']//a")
                safe_click_js(driver, upload_choice_btn)

            time.sleep(2)

            # Upload to HIDDEN input
            cover_input = driver.find_element(By.ID, "data-print-book-publisher-cover-file-upload-AjaxInput")
            abs_cover_path = os.path.abspath(cover_path)
            cover_input.send_keys(abs_cover_path)

            print("Waiting for cover upload to process...")
            WebDriverWait(driver, 180).until(
                EC.presence_of_element_located((By.ID, "data-print-book-publisher-cover-file-upload-success"))
            )
            print("Cover uploaded successfully.")
        except Exception as e:
            print(f"Error uploading cover: {e}")

        time.sleep(5)
        noai = driver.find_element(By.CSS_SELECTOR, "#section-generative-ai > div > div.a-column.a-span10.a-span-last > div > div > div > div > span > div:nth-child(3) > div > div.a-box.a-accordion-active > div > div > a")
        safe_click_js(driver, noai)
        driver.find_element(By.ID,"save-and-continue-announce").click()
    except Exception as e:
        print(f"Content page automation failed: {e}")


def automate_kdp_publishing(email, password, colors):
    os.makedirs("out", exist_ok=True)
    driver = setup_driver()
    try:
        login_to_kdp(driver, email, password)

        for color_hex, color_name in colors:
            subtitle = BOOK_SUBTITLE.replace("COLOR", color_name)

            # 1. Fill Details
            fill_book_details(
                driver,
                title=BOOK_TITLE,
                subtitle=subtitle,
                author_first=AUTHOR_FIRST_NAME,
                author_last=AUTHOR_LAST_NAME,
                description=BOOK_DESCRIPTON,
                keywords=KEYWORDS,
                is_low_content=True
            )

            # 2. Fill Content
            cover_filename = f"out/cat_notebook_cover_{color_name.replace(' ', '-')}.pdf"
            if not os.path.exists(cover_filename):
                 print(f"WARNING: Cover file {cover_filename} missing.")

            # Use the exact interior file path from your project (Note: ensure 'Notes_content_6x9.pdf' is in the folder)
            interior_filename = BOOK_CONTENT # This comes from add_notebook.py

            fill_content_page(driver, interior_filename, cover_filename)

            print(f"--- Process finished for {color_name} ---")
            break # Remove break to process all colors

    except Exception as e:
        print(f"Global Error: {e}")
    finally:
        print("Script finished. Browser is open.")
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    EMAIL = "michallipinski@gmail.com"
    PASSWORD = "kochamGusi3!"
    COLORS = [["#0047AB", "Cobalt Blue"]]
    automate_kdp_publishing(EMAIL, PASSWORD, COLORS)
