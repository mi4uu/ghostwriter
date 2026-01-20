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

        # Ensure copyright/public-domain choice: click the visible checkbox if present
        try:
            npd = driver.find_element(By.ID, "non-public-domain")
            try:
                if not npd.is_selected():
                    driver.execute_script("arguments[0].click();", npd)
            except Exception:
                # Some elements are not native checkboxes; try clicking via JS anyway
                driver.execute_script("arguments[0].click();", npd)
        except Exception as e:
            print(f"Could not ensure non-public-domain checked: {e}")

        # Ensure adult-content is set to 'No' (false). Try radios first, then fallback to hidden input.
        try:
            clicked_adult = False
            # radios with value containing 'no' or 'false' (case-insensitive)
            adult_radio_xpath = "//input[@type='radio' and (contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no') or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'false'))]"
            radios = driver.find_elements(By.XPATH, adult_radio_xpath)
            for r in radios:
                try:
                    if not r.is_selected():
                        driver.execute_script("arguments[0].click();", r)
                    clicked_adult = True
                    break
                except Exception:
                    continue

            if not clicked_adult:
                # Try to locate radio inputs whose name/id mentions 'adult' and click the last/No option nearby
                alt_xpath = "//input[@type='radio' and (contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'adult') or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'adult'))]"
                alt = driver.find_elements(By.XPATH, alt_xpath)
                for r in alt:
                    try:
                        val = (r.get_attribute('value') or '').lower()
                        if 'no' in val or 'false' in val or val == '0':
                            if not r.is_selected():
                                driver.execute_script("arguments[0].click();", r)
                            clicked_adult = True
                            break
                    except Exception:
                        continue

            if not clicked_adult:
                # Fallback: set hidden input used elsewhere
                try:
                    hidden_input = driver.find_element(By.ID, ID_IS_ADULTONLY)
                    driver.execute_script("arguments[0].value = 'false';", hidden_input)
                    print('Set hidden adult-only field to false as fallback')
                except Exception as e:
                    print(f'Failed fallback setting adult hidden: {e}')
            # Explicit attempt for the KDP Primary Audience radio
            try:
                primary_audience_xpath = "//input[@type='radio' and @name=\"data[print_book][is_adult_content]-radio\" and (@value='false' or translate(@value,'FALSE','false')='false')]"
                pa = driver.find_element(By.XPATH, primary_audience_xpath)
                try:
                    if not pa.is_selected():
                        driver.execute_script("arguments[0].click();", pa)
                    # dispatch change event
                    driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", pa)
                except Exception:
                    driver.execute_script("arguments[0].click();", pa)
            except Exception:
                pass
        except Exception as e:
            print(f"Adult radio handling failed: {e}")




        # # 1. Find the hidden element
        # hidden_input = driver.find_element(By.ID, ID_IS_ADULTONLY)

        # # 2. Use JavaScript to set the value attribute directly
        # driver.execute_script("arguments[0].value = 'false';", hidden_input)
        
        
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

        # Ensure adult-only selection is answered and events fired before opening categories
        try:
            # If a visible 'No' radio exists, click it
            no_radio = None
            try:
                no_radio = driver.find_element(By.XPATH, "//input[@type='radio' and (contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no') or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'false'))]")
                driver.execute_script("arguments[0].click();", no_radio)
            except Exception:
                # try radios whose name/id mentions 'adult' and value is 'no' or similar
                try:
                    alt = driver.find_element(By.XPATH, "//input[@type='radio' and (contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'adult') or contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'adult')) and (contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no') or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'false') or @value='0')]")
                    driver.execute_script("arguments[0].click();", alt)
                except Exception:
                    pass

            # Also set hidden field and dispatch change to ensure page state updates
            try:
                hidden_adult = driver.find_element(By.ID, ID_IS_ADULTONLY)
                driver.execute_script("arguments[0].value = 'false'; arguments[0].dispatchEvent(new Event('change'));", hidden_adult)
            except Exception:
                pass

            # Small pause to allow UI to update and enable category button
            time.sleep(1.0)
        except Exception as e:
            print(f"Warning: adult-only selection attempt failed: {e}")

        # Wait until the Choose Categories button is clickable, then click
        try:
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, ID_CHOOSE_CATEGORIES_BTN)))
            driver.find_element(By.ID, ID_CHOOSE_CATEGORIES_BTN).click()
            driver.save_screenshot('screenshot1.png')
        except Exception as e:
            print(f"Could not open categories modal (button not clickable): {e}")

        # Choose categories (attempt automated selection)
        try:
            choose_categories(driver, CATEGORIES)
        except Exception as e:
            print(f"Category selection skipped/failed: {e}")

        # Save and continue
        try:
            driver.find_element(By.ID, f"{ID_SAVE_AND_CONTINUE_BTN}").click()
        except Exception as e:
            print(f"Could not click save-and-continue button: {e}")
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


def choose_categories(driver, categories):
    """
    Attempt to select categories in the KDP categories modal.
    This uses resilient selectors: search input (if present), tree traversal, and fallback clicks.
    """
    try:
        # Wait for modal to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='dialog'], .categories-modal, #categories-modal"))
        )
    except Exception:
        # modal might already be present
        pass

    def try_click_by_xpaths(xpaths, wait=5):
        for xp in xpaths:
            try:
                el = WebDriverWait(driver, wait).until(EC.element_to_be_clickable((By.XPATH, xp)))
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                el.click()
                return True
            except Exception:
                continue
        return False

    # Try clicking any initial "Select one" controls to open category slots (case-insensitive)
    select_one_xpaths = [
        "//button[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='select one']",
        "//div[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='select one']",
        "//span[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='select one']",
        "//span[contains(@class,'a-dropdown-prompt') and normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='select one']",
    ]
    try_click_by_xpaths(select_one_xpaths, wait=2)

    for idx, cat in enumerate(categories):
        leaf = cat.split('>')[-1].strip()
        clicked = False

        # If there are hierarchical native <select>s, iterate parts and set each level sequentially
        parts = [p.strip() for p in cat.split('>')]
        try:
            all_parts_selected = True
            for part in parts:
                part_selected = False
                selects = driver.find_elements(By.XPATH, "//div[@role='dialog']//select | //select[contains(@class,'a-native-dropdown')] | //select")
                for sel in selects:
                    try:
                        options = sel.find_elements(By.TAG_NAME, 'option')
                        for opt in options:
                            text = (opt.text or '').strip()
                            val = (opt.get_attribute('value') or '')
                            if text and (text.lower() == part.lower() or part.lower() in text.lower()) or (val and ('\"key\":\"' + part + '\"') in val):
                                # set value and dispatch change
                                driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));", sel, val)
                                time.sleep(0.6)
                                # try clicking the dropdown prompt/button to ensure UI updates
                                try:
                                    btn = sel.find_element(By.XPATH, "./following-sibling::span//span[@data-action='a-dropdown-button' or contains(@class,'a-dropdown-prompt') or contains(., 'Select one')]")
                                    driver.execute_script("arguments[0].click();", btn)
                                except Exception:
                                    # try a more global sibling search
                                    try:
                                        btn2 = sel.find_element(By.XPATH, "..//span[@class='a-button a-button-dropdown']")
                                        driver.execute_script("arguments[0].click();", btn2)
                                    except Exception:
                                        pass
                                part_selected = True
                                break
                        if part_selected:
                            break
                    except Exception:
                        continue
                if not part_selected:
                    all_parts_selected = False
                    break
            if all_parts_selected:
                clicked = True
        except Exception:
            pass
        # 1) Try modal search inputs (several possible attributes)
        search_xpaths = [
            "//div[@role='dialog']//input[@type='search']",
            "//div[@role='dialog']//input[@type='text' and (contains(@placeholder,'Search') or contains(@aria-label,'Search'))]",
            "//input[@type='search']",
            "//input[contains(@placeholder,'Search') or contains(@aria-label,'Search') or contains(@class,'search') or contains(@id,'search')]",
        ]

        clicked = False
        for sx in search_xpaths:
            try:
                search = driver.find_element(By.XPATH, sx)
                search.clear()
                search.send_keys(leaf)
                time.sleep(1)
                # after typing, try to click first matching label/button in modal or page
                opt_xpaths = [
                    f"//div[@role='dialog']//button[normalize-space(.)='{leaf}']",
                    f"//div[@role='dialog']//label[normalize-space(.)='{leaf}']",
                    f"//button[normalize-space(.)='{leaf}']",
                    f"//label[normalize-space(.)='{leaf}']",
                    f"//div[contains(normalize-space(.), '{leaf}')]",
                ]
                if try_click_by_xpaths(opt_xpaths, wait=3):
                    clicked = True
                    break
            except Exception:
                continue

        if clicked:
            time.sleep(0.4)
            # After selecting this category, if more categories remain, click 'Add another category'
            if idx < len(categories) - 1:
                add_more_xpaths = [
                    "//button[contains(normalize-space(.), 'Add another category') ]",
                    "//button[contains(normalize-space(.), 'Add another') ]",
                    "//a[contains(normalize-space(.), 'Add another category') ]",
                ]
                if try_click_by_xpaths(add_more_xpaths, wait=3):
                    time.sleep(0.6)
            continue

        # 2) Fallback: try clicking by parts scoped to the categories modal (prefer) then global
        modal_prefix = "//div[contains(@class,'a-modal-scroller') and contains(@class,'a-declarative')]"
        parts = [p.strip() for p in cat.split('>')]
        for part in parts:
            # create tolerant variants (remove commas, normalize ampersand spacing)
            variants = [part, part.replace(',', ''), part.replace(' & ', '&'), part.replace('&', 'and'), part.replace('&', ' & ')]
            clicked_part = False
            for variant in variants:
                variant = variant.strip()
                if not variant:
                    continue
                part_xpaths_modal = [
                    f"{modal_prefix}//button[contains(normalize-space(.), '{variant}')]",
                    f"{modal_prefix}//label[contains(normalize-space(.), '{variant}')]",
                    f"{modal_prefix}//div[contains(normalize-space(.), '{variant}')]",
                    f"{modal_prefix}//span[contains(normalize-space(.), '{variant}')]",
                ]
                if try_click_by_xpaths(part_xpaths_modal, wait=2):
                    clicked_part = True
                    break

                # fallback to global scope
                part_xpaths_global = [
                    f"//button[contains(normalize-space(.), '{variant}')]",
                    f"//label[contains(normalize-space(.), '{variant}')]",
                    f"//div[contains(normalize-space(.), '{variant}')]",
                    f"//span[contains(normalize-space(.), '{variant}')]",
                ]
                if try_click_by_xpaths(part_xpaths_global, wait=2):
                    clicked_part = True
                    break

            if not clicked_part:
                print(f"Could not click category tree part '{part}' (no matching clickable element).")
                # Save debug artifacts to out/ for inspection
                try:
                    os.makedirs('out', exist_ok=True)
                    driver.save_screenshot('out/categories_error.png')
                    with open('out/categories_error.html', 'w', encoding='utf-8') as f:
                        f.write(driver.page_source)
                    print('Saved out/categories_error.png and out/categories_error.html')
                except Exception as dump_e:
                    print(f'Failed to save debug artifacts: {dump_e}')
            else:
                time.sleep(0.4)


    # Try to confirm/close modal
    try:
        done_btn = driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(., 'Done') or contains(., 'Apply') or contains(., 'Save')]")
        done_btn.click()
    except Exception:
        # Best-effort close: try clicking any modal primary button
        try:
            primary = driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@class,'primary') or contains(@aria-label,'Done')]")
            primary.click()
        except Exception:
            print("Could not find Done/Apply button to close categories modal; leaving it open.")

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