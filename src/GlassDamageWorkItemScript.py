import sys
import os
# Ensure project root is in sys.path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
"""
Script to loop through MVAs, check for glass damage work item, log status, and create if missing.
Uses two-tier logging (per-MVA and error/confirmation logs).
"""
import time
from utils.logger import log
from core.driver_manager import get_driver, quit_driver
from config.config_loader import get_config
from flows.LoginFlow import LoginFlow
from flows.work_item_flow import get_work_items
from flows.complaints_flows import detect_existing_complaints, handle_new_complaint
from pages.work_item import WorkItem
from selenium.common.exceptions import NoSuchElementException
import csv
from pages.mva_input_page import MVAInputPage
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

MVA_CSV = "data/GlassDamageWorkItemScript.csv"


from flows.work_item_handler import WorkItemConfig

def read_csv_rows(csv_path):
    """Read rows from CSV, skipping empty and comment rows."""
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row and row.get('MVA') and not row['MVA'].strip().startswith('#')]

def create_work_item_config(row):
    """Create WorkItemConfig from a CSV row."""
    mva = row['MVA'].strip()
    return WorkItemConfig(
        mva=mva,
        damage_type=row.get('DamageType'),
        location=row.get('Location')
    )

def log_work_item_config(config):
    """Log details of a WorkItemConfig."""
    log.info(f"[CSV] Loading work item: {config.mva} (DamageType: {config.damage_type}, Location: {config.location})")

def get_work_item_configs(csv_path):
    """Read, filter, create, and log WorkItemConfig objects from CSV."""
    rows = read_csv_rows(csv_path)
    configs = []
    for row in rows:
        config = create_work_item_config(row)
        configs.append(config)
        log_work_item_config(config)
    return configs


# ----------------------------------------------------------------------------
# AUTHOR:       Dirk Steele <dirk.avis@mail.com>
# DATE:         2026-01-12
# DESCRIPTION:  Read glass work items from CSV and return WorkItemConfig objects.
#               Skips comments and empty rows, logs each loaded config.
# VERSION:      1.0.0
# NOTES:        Expects columns: MVA, DamageType, Location.
# ----------------------------------------------------------------------------

def main():
    username = get_config("username")
    password = get_config("password")
    login_id = get_config("login_id")
    driver = get_driver()
    mva_input_page = MVAInputPage(driver)
    login_flow = LoginFlow(driver)
    login_result = login_flow.login_handler(username, password, login_id)
    if login_result.get("status") != "ok":
        log.error(f"[LOGIN] Failed to initialize session → {login_result}")
        return

    mva_list = get_work_item_configs(MVA_CSV)
    for work_item_config in mva_list:
        # after finding the first work item type sought we can break out of the loop
        mva = work_item_config.mva
        mva_header = f"\n{'*'*32}\nMVA {mva}\n{'*'*32}"
        log.info(mva_header)
        log.info(f"[MVA] Reviewing {mva} (Type: {work_item_config.damage_type}, Location: {work_item_config.location})")
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                # --- Robust MVA input logic (from GlassDataParser.py) ---
                input_field = mva_input_page.find_input()
                if not (input_field and input_field.is_enabled() and input_field.is_displayed()):
                    try:
                        input_field = WebDriverWait(driver, 5, poll_frequency=0.25).until(
                            lambda d: (
                                (f := mva_input_page.find_input()) and f.is_enabled() and f.is_displayed() and f
                            )
                        )
                    except TimeoutException:
                        input_field = None
                if not input_field:
                    log.error(f"[MVA][FATAL] Could not find MVA input field for {mva}. Attempt {attempt}/{max_attempts}.")
                    if attempt == max_attempts:
                        log.error(f"[MVA][FATAL] Skipping {mva} after {max_attempts} attempts.")
                        break
                    else:
                        time.sleep(2)
                        continue
                import selenium.webdriver.common.keys as Keys
                # Aggressively clear the field
                # We don't need an aggressive clear here.  Just clear the field once and verify.  If still not cleared, log an error.
                # Refactoring to simplify the logic. into one clear attempt followed by verification.
                # we may need to have a slight delay after clear to allow UI to update(3000ms)
                # Background knowledge: The application will clear the field with an <ENTER>. This is a shortcut we can use.


                for _ in range(3):
                    input_field.send_keys(Keys.Keys.CONTROL + 'a')
                    input_field.send_keys(Keys.Keys.DELETE)
                    input_field.clear()
                    time.sleep(0.2)
                # Wait up to 1s (4 x 250ms) for the field to be empty
                for _ in range(4):
                    if input_field.get_attribute("value") == "":
                        break
                    time.sleep(0.25)
                else:
                    log.warning(f"[MVA_INPUT] Field not empty after clearing attempts!")
                # Wait up to 3 seconds for the field to be empty
                for _ in range(15):
                    if input_field.get_attribute("value") == "":
                        break
                    time.sleep(0.2)
                if input_field.get_attribute("value") != "":
                    log.warning(f"[MVA_INPUT] Field not fully cleared before entering new MVA!")
                else:
                    log.info(f"[MVA_INPUT] Field cleared before entering new MVA.")
                input_field.send_keys(mva)
                # Don't send Enter - the application auto-searches after 8 digits
                log.info(f"[MVA_INPUT] Entered MVA: {mva}")

                # --- End robust MVA input logic ---

                # Wait for vehicle properties container to appear (indicates valid MVA)
                try:
                    log.info(f"[MVA_VALIDATION] Waiting for vehicle properties to load for {mva}...")
                    vehicle_properties = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.fleet-operations-pwa__vehicle-properties-container__1ad7kyc"))
                    )
                    log.info(f"[MVA_VALIDATION] Vehicle properties loaded successfully for {mva}")
                except TimeoutException:
                    log.warning(f"[MVA_VALIDATION] Vehicle properties not found for {mva} - MVA may be invalid or non-existent")
                    break  # Skip to next MVA

                # Additional wait for work items to update after vehicle properties load
                time.sleep(2)
                work_items = get_work_items(driver, mva)
                # Only proceed if there are no glass work items
                glass_found = False
                for wi in work_items:
                    # Debug: Log the actual text and its properties
                    log.info(f"[DEBUG] Work item text: '{wi.text}'")
                    log.info(f"[DEBUG] Text length: {len(wi.text)}")
                    log.info(f"[DEBUG] Text repr: {repr(wi.text)}")
                    log.info(f"[DEBUG] Lowercased: '{wi.text.lower()}'")
                    log.info(f"[DEBUG] Contains 'glass': {'glass' in wi.text.lower()}")
                    if "glass" in wi.text.lower():
                        glass_found = True
                        log.info(f"[GLASS] Glass damage work item already exists for {mva}")
                        break
                if glass_found:
                    break  # No need to create a new work item, exit retry loop

                # If there are work items but none are glass, or if there are no work items at all, create new glass work item
                log.info(f"[GLASS] No active glass damage work item found for {mva}, creating new work item...")
                from flows.work_item_flow import create_work_item_with_strategy
                result = create_work_item_with_strategy(driver, work_item_config, strategy_type="GLASS")
                if result.get("status") == "created":
                    log.info(f"[GLASS] Glass damage work item created for {mva}")
                else:
                    log.error(f"[GLASS][ERROR] Failed to create glass work item for {mva}: {result}")
                break  # Success or failure, exit retry loop
            except Exception as e:
                log.error(f"[ERROR] Exception for {mva} (attempt {attempt}/{max_attempts}): {e}")
                if attempt == max_attempts:
                    log.error(f"[MVA][FATAL] Skipping {mva} after {max_attempts} attempts due to repeated errors.")
                else:
                    time.sleep(2)
        time.sleep(2)

    # Ensure the browser is closed after all automation is finished
    try:
        quit_driver()
        log.info("[SESSION] Browser closed.")
    except Exception as e:
        log.warning(f"[SESSION] Failed to close browser: {e}")

# ----------------------------------------------------------------------------
# AUTHOR:       Dirk Steele <dirk.avis@mail.com>
# DATE:         2026-01-12
# DESCRIPTION:  Main script logic. Logs in, iterates MVAs, checks for glass work items,
#               and creates new ones if needed. Handles robust MVA input and error handling.
# VERSION:      1.0.0
# NOTES:        Uses robust field clearing and retry logic for reliability.
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
