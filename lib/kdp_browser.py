"""
KDP Browser Automation helpers.

Selenium-based interactions with Amazon KDP publishing pages.
Migrated and improved from kdp_automation.py.
"""

import os
import time
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# --- KDP Page Element IDs ---

KDP_NEW_PAPERBACK_URL = "https://kdp.amazon.com/en_US/title-setup/paperback/new/details?type=PRIMARY"

# Page 1: Book Details
ID_TITLE = "data-print-book-title"
ID_SUBTITLE = "data-print-book-subtitle"
ID_AUTHOR_FIRST = "data-print-book-primary-author-first-name"
ID_AUTHOR_LAST = "data-print-book-primary-author-last-name"
ID_LOW_CONTENT = "data-view-is-lcb"
ID_KEYWORDS_PREFIX = "data-print-book-keywords-"
ID_COPYRIGHTS = "data-print-book-is-public-domain"
ID_ADULT_HIDDEN = "data-print-book-is-adult-content-hidden"
ID_CATEGORIES_BTN = "categories-modal-button"
ID_SAVE_CONTINUE = "save-and-continue-announce"

# Page 2: Content
ID_INTERIOR_UPLOAD = "data-print-book-publisher-interior-file-upload-AjaxInput"
ID_INTERIOR_SUCCESS = "data-print-book-publisher-interior-file-upload-success"
ID_COVER_UPLOAD = "data-print-book-publisher-cover-file-upload-AjaxInput"
ID_COVER_SUCCESS = "data-print-book-publisher-cover-file-upload-success"


# --- Driver Setup ---

def setup_driver(profile_dir="./chrome_profile"):
    """
    Create a Chrome WebDriver with a persistent profile.

    The saved profile means you log in to KDP once manually,
    and subsequent runs reuse that session.
    """
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.maximize_window()
    return driver


def ensure_logged_in(driver):
    """
    Navigate to KDP and verify we're logged in via saved session.
    If not logged in, wait for user to log in manually.
    """
    driver.get("https://kdp.amazon.com/")

    try:
        WebDriverWait(driver, 10).until(
            EC.title_contains("Kindle Direct Publishing")
        )
        print("Logged in via saved session.")
        return
    except Exception:
        pass

    print("Not logged in. Please log in manually in the browser window...")
    print("Waiting up to 5 minutes for login...")

    try:
        WebDriverWait(driver, 300).until(
            EC.title_contains("Kindle Direct Publishing")
        )
        print("Login detected. Continuing...")
    except Exception:
        raise RuntimeError("Login timed out after 5 minutes. Please try again.")


# --- Helpers ---

def type_like_human(element, text):
    """Type text character by character with random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.03, 0.08))


def safe_click(driver, element):
    """Click an element using JavaScript to avoid interception errors."""
    driver.execute_script(
        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
        element,
    )
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)


def wait_and_find(driver, by, value, timeout=30):
    """Wait for an element and return it."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def wait_and_click(driver, by, value, timeout=15):
    """Wait for an element to be clickable and click it."""
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    safe_click(driver, el)
    return el


# --- Page 1: Book Details ---

def fill_book_details(driver, metadata):
    """
    Fill in the KDP Book Details page (page 1 of 3).

    Args:
        driver: Selenium WebDriver
        metadata: Dict from metadata.json
    """
    print("  [Page 1] Filling book details...")
    driver.get(KDP_NEW_PAPERBACK_URL)

    # Wait for page load
    wait_and_find(driver, By.ID, ID_TITLE, timeout=30)
    time.sleep(1)

    # Title
    driver.find_element(By.ID, ID_TITLE).send_keys(metadata["title"])

    # Subtitle
    type_like_human(
        driver.find_element(By.ID, ID_SUBTITLE),
        metadata["subtitle"],
    )

    # Author
    driver.find_element(By.ID, ID_AUTHOR_FIRST).send_keys(metadata["author_first"])
    driver.find_element(By.ID, ID_AUTHOR_LAST).send_keys(metadata["author_last"])

    # Copyright: not public domain
    try:
        driver.execute_script(
            f"document.getElementById('{ID_COPYRIGHTS}').value = 'false';"
        )
        npd = driver.find_element(By.ID, "non-public-domain")
        if not npd.is_selected():
            driver.execute_script("arguments[0].click();", npd)
    except Exception:
        pass

    # Adult content: No
    _set_not_adult(driver)

    # Low content
    if metadata.get("is_low_content", True):
        try:
            driver.find_element(By.ID, ID_LOW_CONTENT).click()
        except Exception:
            pass

    # Keywords (up to 7)
    for i, keyword in enumerate(metadata.get("keywords", [])[:7]):
        try:
            driver.find_element(By.ID, f"{ID_KEYWORDS_PREFIX}{i}").send_keys(keyword)
        except Exception:
            pass

    # Description (HTML via CKEditor)
    try:
        driver.find_element(By.ID, "cke_editor1").click()
        driver.execute_script(
            "CKEDITOR.instances['editor1'].setData(arguments[0]);",
            metadata["description"],
        )
    except Exception as e:
        print(f"    Warning: Could not set description: {e}")

    # Categories
    try:
        time.sleep(1)
        wait_and_click(driver, By.ID, ID_CATEGORIES_BTN, timeout=10)
        _choose_categories(driver, metadata.get("categories", []))
    except Exception as e:
        print(f"    Warning: Category selection failed: {e}")

    # Save and Continue
    print("  [Page 1] Saving...")
    time.sleep(1)
    wait_and_click(driver, By.ID, ID_SAVE_CONTINUE, timeout=10)
    time.sleep(3)
    print("  [Page 1] Done.")


def _set_not_adult(driver):
    """Set adult content to 'No' using multiple strategies."""
    # Strategy 1: Click visible radio button
    try:
        radio = driver.find_element(
            By.XPATH,
            "//input[@type='radio' and contains(@name,'adult') and "
            "(contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'false') "
            "or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'no'))]"
        )
        driver.execute_script("arguments[0].click();", radio)
        return
    except Exception:
        pass

    # Strategy 2: KDP Primary Audience radio
    try:
        radio = driver.find_element(
            By.XPATH,
            "//input[@type='radio' and "
            "@name=\"data[print_book][is_adult_content]-radio\" and "
            "(@value='false' or translate(@value,'FALSE','false')='false')]"
        )
        driver.execute_script("arguments[0].click();", radio)
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('change'));", radio
        )
        return
    except Exception:
        pass

    # Strategy 3: Hidden field fallback
    try:
        hidden = driver.find_element(By.ID, ID_ADULT_HIDDEN)
        driver.execute_script(
            "arguments[0].value = 'false'; "
            "arguments[0].dispatchEvent(new Event('change'));",
            hidden,
        )
    except Exception:
        pass


def _choose_categories(driver, categories):
    """Select categories in the KDP categories modal."""
    print("    Selecting categories...")

    # Wait for modal
    try:
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div[role='dialog'], div[id^='react-aui-modal-content']")
            )
        )
        time.sleep(1)
    except Exception:
        print("    Warning: Category modal not found")
        return

    for idx, cat_path in enumerate(categories):
        # Click "Add another category" for 2nd+ categories
        if idx > 0:
            try:
                modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
                add_btn = modal.find_element(
                    By.XPATH,
                    ".//button[contains(text(), 'Add another category')] | "
                    ".//a[contains(text(), 'Add another category')]"
                )
                safe_click(driver, add_btn)
                time.sleep(1.5)
            except Exception:
                pass

        parts = [p.strip() for p in cat_path.split('>')]

        for part_name in parts:
            modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")

            # Try checkbox first (leaf nodes)
            if _try_click_checkbox(driver, modal, part_name):
                continue

            # Try dropdown (parent categories)
            _try_select_dropdown(driver, modal, part_name)

    # Save categories
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
        done_btn = modal.find_element(
            By.XPATH,
            ".//button[contains(text(), 'Save categories') or contains(text(), 'Done')]"
        )
        safe_click(driver, done_btn)
        time.sleep(2)
    except Exception as e:
        print(f"    Warning: Could not save categories: {e}")


def _try_click_checkbox(driver, modal, part_name):
    """Try to find and click a checkbox for a category part."""
    try:
        labels = modal.find_elements(
            By.XPATH, f".//label[contains(., \"{part_name}\")]"
        )
        for label in labels:
            if label.is_displayed():
                if label.find_elements(
                    By.CSS_SELECTOR, "input[type='checkbox'], i.a-icon-checkbox"
                ):
                    safe_click(driver, label)
                    time.sleep(1)
                    return True
    except Exception:
        pass
    return False


def _try_select_dropdown(driver, modal, part_name):
    """Try to select a category part from a dropdown."""
    dropdowns = modal.find_elements(
        By.CSS_SELECTOR, "span[role='button'][data-action='a-dropdown-button']"
    )
    visible_dropdowns = [d for d in dropdowns if d.is_displayed()]

    target = None
    for d in visible_dropdowns:
        if "Select one" in d.text:
            target = d
            break
    if not target and visible_dropdowns:
        target = visible_dropdowns[-1]

    if target:
        safe_click(driver, target)
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, ".a-popover-inner, #a-popover-content")
                )
            )
            option_xpath = (
                f"//a[contains(@class,'a-dropdown-link') and "
                f"normalize-space(text())=\"{part_name}\"]"
            )
            option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, option_xpath))
            )
            safe_click(driver, option)
            time.sleep(2)
        except Exception as e:
            print(f"    Warning: Could not select '{part_name}' from dropdown: {e}")
            webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()


# --- Page 2: Content ---

def fill_content_page(driver, metadata, book_dir):
    """
    Fill in the KDP Content page (page 2 of 3).

    Uploads interior and cover PDFs, sets print options, marks not-AI.
    """
    print("  [Page 2] Filling content page...")
    time.sleep(6)  # Wait for page to fully load

    # Print options: try to set No Bleed and Matte
    _set_print_options(driver)

    # Upload interior
    interior_path = os.path.join(book_dir, metadata["interior_file"])
    _upload_file(driver, ID_INTERIOR_UPLOAD, ID_INTERIOR_SUCCESS, interior_path, "interior")

    # Upload cover
    _select_upload_cover_option(driver)
    cover_path = os.path.join(book_dir, metadata["cover_file"])
    _upload_file(driver, ID_COVER_UPLOAD, ID_COVER_SUCCESS, cover_path, "cover")

    # Mark not AI-generated
    _mark_not_ai(driver)

    # Save and continue
    print("  [Page 2] Saving...")
    time.sleep(2)
    try:
        driver.find_element(By.ID, ID_SAVE_CONTINUE).click()
    except Exception:
        wait_and_click(driver, By.ID, ID_SAVE_CONTINUE, timeout=10)

    # Wait for preview to generate and handle it
    _handle_preview(driver)

    print("  [Page 2] Done.")


def _set_print_options(driver):
    """Set print options: No Bleed, Matte finish."""
    try:
        no_bleed = driver.find_element(
            By.XPATH, "//button[contains(., 'No Bleed')] | //button[@value='no_bleed']"
        )
        safe_click(driver, no_bleed)
    except Exception:
        pass

    try:
        matte = driver.find_element(
            By.XPATH, "//button[contains(., 'Matte')] | //button[@value='matte']"
        )
        safe_click(driver, matte)
    except Exception:
        pass


def _upload_file(driver, input_id, success_id, file_path, file_type):
    """Upload a file via hidden file input and wait for success."""
    abs_path = os.path.abspath(file_path)
    print(f"    Uploading {file_type}: {abs_path}")

    try:
        file_input = driver.find_element(By.ID, input_id)
        file_input.send_keys(abs_path)

        # Wait for upload success (up to 3 minutes)
        WebDriverWait(driver, 180).until(
            EC.presence_of_element_located((By.ID, success_id))
        )
        print(f"    {file_type.capitalize()} uploaded successfully.")
    except Exception as e:
        print(f"    ERROR uploading {file_type}: {e}")


def _select_upload_cover_option(driver):
    """Click 'Upload a cover you already have' to reveal the cover upload input."""
    try:
        header = driver.find_element(
            By.XPATH, "//span[contains(text(), 'Upload a cover you already have')]"
        )
        safe_click(driver, header)
    except Exception:
        try:
            btn = driver.find_element(
                By.XPATH,
                "//div[@data-a-accordion-row-name='UPLOAD']//button | "
                "//div[@data-a-accordion-row-name='UPLOAD']//a"
            )
            safe_click(driver, btn)
        except Exception:
            pass
    time.sleep(2)


def _mark_not_ai(driver):
    """Mark the book as not AI-generated."""
    try:
        # The AI section has a specific CSS path - try multiple selectors
        selectors = [
            "#section-generative-ai a",
            "#section-generative-ai div.a-accordion-active a",
            "a[contains(text(), 'None')]",
        ]
        for selector in selectors:
            try:
                if selector.startswith("a["):
                    el = driver.find_element(By.XPATH, f"//{selector}")
                else:
                    el = driver.find_element(By.CSS_SELECTOR, selector)
                safe_click(driver, el)
                print("    Marked as not AI-generated.")
                return
            except Exception:
                continue

        # Fallback: the complex CSS selector from the original code
        noai = driver.find_element(
            By.CSS_SELECTOR,
            "#section-generative-ai > div > div.a-column.a-span10.a-span-last "
            "> div > div > div > div > span > div:nth-child(3) > div > "
            "div.a-box.a-accordion-active > div > div > a"
        )
        safe_click(driver, noai)
        print("    Marked as not AI-generated.")
    except Exception as e:
        print(f"    Warning: Could not mark not-AI: {e}")


def _handle_preview(driver):
    """Wait for preview generation and approve it."""
    print("    Waiting for preview generation...")
    try:
        # Wait for the page to transition - look for previewer or approve elements
        # KDP generates a preview after save - this can take 30-90 seconds
        time.sleep(10)

        # Try to find and click the Launch Previewer button
        try:
            previewer_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(text(), 'Launch Previewer')] | "
                    "//a[contains(text(), 'Launch Previewer')]"
                ))
            )
            safe_click(driver, previewer_btn)
            print("    Previewer launched, waiting...")
            time.sleep(15)  # Give previewer time to load

            # Close previewer if it opened in a modal
            try:
                close_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), 'Close')] | "
                    "//button[@aria-label='Close']"
                )
                safe_click(driver, close_btn)
                time.sleep(2)
            except Exception:
                pass
        except Exception:
            print("    No previewer button found, continuing...")

        # Try to click Approve
        try:
            approve_btn = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(text(), 'Approve')] | "
                    "//input[contains(@value, 'Approve')]"
                ))
            )
            safe_click(driver, approve_btn)
            print("    Preview approved.")
            time.sleep(2)
        except Exception:
            print("    No approve button found, continuing...")

        # Save and continue to pricing
        try:
            wait_and_click(driver, By.ID, ID_SAVE_CONTINUE, timeout=10)
            time.sleep(3)
        except Exception:
            pass

    except Exception as e:
        print(f"    Warning: Preview handling issue: {e}")


# --- Page 3: Pricing ---

def fill_pricing_page(driver, metadata):
    """
    Fill in the KDP Pricing page (page 3 of 3) and publish.

    Args:
        driver: Selenium WebDriver
        metadata: Dict from metadata.json
    """
    print("  [Page 3] Setting pricing...")
    time.sleep(5)  # Wait for page load

    price = metadata.get("price_usd", 7.99)

    # Try to find and fill the US marketplace price input
    try:
        # Look for the primary marketplace price input
        price_selectors = [
            "//input[contains(@id, 'print-book-pricing-us') or contains(@name, 'pricing-us')]",
            "//input[contains(@id, 'pricing') and contains(@id, 'US')]",
            "//div[contains(@class, 'marketplace')]//input[@type='text' or @type='number']",
        ]

        price_input = None
        for selector in price_selectors:
            try:
                price_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                break
            except Exception:
                continue

        if price_input:
            price_input.clear()
            price_input.send_keys(str(price))
            print(f"    Price set to ${price}")
            time.sleep(1)
        else:
            print("    Warning: Could not find price input field")

    except Exception as e:
        print(f"    Warning: Pricing failed: {e}")

    # Select all territories (if applicable)
    try:
        all_territories = driver.find_element(
            By.XPATH,
            "//input[@type='radio' and contains(@value, 'all')] | "
            "//label[contains(text(), 'All territories')]"
        )
        safe_click(driver, all_territories)
        time.sleep(1)
    except Exception:
        pass  # May already be selected

    # Publish
    print("  [Page 3] Publishing...")
    time.sleep(2)

    try:
        publish_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(text(), 'Publish Your Paperback Book')] | "
                "//input[contains(@value, 'Publish')] | "
                "//button[contains(@id, 'publish')]"
            ))
        )
        safe_click(driver, publish_btn)
        print("  [Page 3] Publish clicked!")
        time.sleep(5)

        # Handle any confirmation dialogs
        try:
            confirm = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(text(), 'Confirm') or contains(text(), 'Yes') or contains(text(), 'OK')]"
                ))
            )
            safe_click(driver, confirm)
            time.sleep(3)
        except Exception:
            pass  # No confirmation dialog

    except Exception as e:
        print(f"    ERROR: Could not publish: {e}")
        return False

    print("  [Page 3] Done - Book published!")
    return True
