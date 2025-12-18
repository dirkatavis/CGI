import time

from selenium.webdriver.common.by import By
from utils.logger import log
from utils.ui_helpers import (click_element, find_element , find_elements)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from utils.ui_helpers import click_element
from flows.opcode_flows import select_opcode    
from flows.mileage_flows import complete_mileage_dialog



def handle_existing_complaint(driver, mva: str) -> dict:
    """Select an existing complaint tile and advance."""
    log.debug(f"[COMPLAINT] {mva} - Handling existing complaint.")
    if click_element(driver, (By.XPATH, "//button[normalize-space()='Next']")):
        log.info(f"[COMPLAINT] {mva} - Next clicked after selecting existing complaint")
        return {"status": "ok"}

    else:
        log.debug(f"[WORKITEM][WARN] {mva} - could not advance with existing complaint")
        return {"status": "failed", "reason": "existing_complaint_next"}

def handle_new_complaint(driver, mva: str) -> dict:
    """Create and submit a new PM complaint."""
    log.debug(f"[COMPLAINT] {mva} - Handling new complaint.")
    if not (
    click_element(driver, (By.XPATH, "//button[normalize-space()='Add New Complaint']"))
    or click_element(driver, (By.XPATH, "//button[normalize-space()='Create New Complaint']"))
    ):

        log.warning(f"[WORKITEM][WARN] {mva} - Add/Create New Complaint not found")
        return {"status": "failed", "reason": "new_complaint_entry"}

    log.info(f"[WORKITEM] {mva} - Adding new complaint")
    time.sleep(2)

    # Drivability -> Yes
    log.info(f"[DRIVABLE] {mva} - answering drivability question: Yes")
    if not click_element(driver, (By.XPATH, "//button[normalize-space()='Yes']")):
        log.warning(f"[WORKITEM][WARN] {mva} - Drivable=Yes button not found")
        return {"status": "failed", "reason": "drivable_yes"}
    log.info(f"[COMPLAINT] {mva} - Drivable=Yes")


    # Complaint Type -> PM
    if not click_element(driver, (By.XPATH, "//button[normalize-space()='PM']")):
        log.warning(f"[WORKITEM][WARN] {mva} - Complaint type PM not found")
        return {"status": "failed", "reason": "complaint_pm"}
    log.info(f"[COMPLAINT] {mva} - PM complaint selected")


    # Submit
    if not click_element(driver, (By.XPATH, "//button[normalize-space()='Submit Complaint']")):

        log.warning(f"[WORKITEM][WARN] {mva} - Submit Complaint not found")
        return {"status": "failed", "reason": "submit_complaint"}
    log.info(f"[COMPLAINT] {mva} - Submit Complaint clicked")

    # Next -> proceed to Mileage
    if not click_element(driver, (By.XPATH, "//button[normalize-space()='Next']")):
        log.warning(f"[WORKITEM][WARN] {mva} - could not advance after new complaint")
        return {"status": "failed", "reason": "new_complaint_next"}
    log.info(f"[COMPLAINT] {mva} - Next clicked after new complaint")

    return {"status": "ok"}

def handle_complaint(driver, mva: str, found_existing: bool) -> dict:
    """Route complaint handling to existing or new complaint flows."""
    log.debug(f"[COMPLAINT] {mva} - Routing complaint handling. Found existing: {found_existing}")
    if found_existing:
        return handle_existing_complaint(driver, mva)
    else:
        return handle_new_complaint(driver, mva)

def find_dialog(driver):
    locator = (By.CSS_SELECTOR, "div.bp6-dialog, div[class*='dialog']")
    return find_element(driver, locator)

def detect_existing_complaints(driver, mva: str):
    """Detect complaint tiles containing 'PM' in their text."""
    try:
        time.sleep(3)  # wait for tiles to load
        tiles = driver.find_elements(
            By.XPATH, "//div[contains(@class,'fleet-operations-pwa__complaintItem__')]"
        )
        log.debug(f"[COMPLAINT] {mva} — found {len(tiles)} total complaint tile(s)")

        valid_tiles = [t for t in tiles if "PM" in t.text.strip()]
        log.debug(
            f"[COMPLAINT] {mva} — filtered {len(valid_tiles)} PM-type complaint(s): "
            f"{[t.text for t in valid_tiles]}"
        )

        return valid_tiles
    except Exception as e:
        log.error(f"[COMPLAINT][ERROR] {mva} — complaint detection failed → {e}")
        return []

def find_pm_tiles(driver, mva: str):
    """Locate complaint tiles of type 'PM' or 'PM Hard Hold - PM'."""
    try:
        tiles = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    "//div[contains(@class,'tileContent')][normalize-space(.)='PM - PM' or normalize-space(.)='PM Hard Hold - PM']"
                    "/ancestor::div[contains(@class,'complaintItem')][1]"
                )
            )
        )
        log.info(f"[COMPLAINT] {mva} — found {len(tiles)} PM/Hard Hold PM complaint tile(s)")
        return tiles
    except Exception as e:
        log.info(f"[COMPLAINT] {mva} — no PM complaint tiles found ({e})")
        return []

def associate_existing_complaint(driver, mva: str) -> dict:
    """
    Look for existing PM complaints and associate them.
    Flow: select complaint tile → Next (complaint) → Next (mileage) → Opcode (PM Gas) → Finalize Work Item.
    """
    log.debug(f"[COMPLAINT] {mva} - Associating existing complaint.")
    try:
        tiles = driver.find_elements(
            By.XPATH, "//div[contains(@class,'fleet-operations-pwa__complaintItem__')]"
        )
        time.sleep(3)  # wait for tiles to load
        if not tiles:
            log.info(f"[COMPLAINT][EXISTING] {mva} - no complaint tiles found")
            return {"status": "skipped_no_complaint", "mva": mva}

        # Filter PM complaints only
        pm_tiles = [t for t in tiles if any(label in t.text for label in ["PM", "PM Hard Hold - PM"])]
        if not pm_tiles:
            log.info(f"[COMPLAINT][EXISTING] {mva} - no PM complaints found")
            return {"status": "skipped_no_complaint", "mva": mva}

        if not pm_tiles:
            log.info(f"[COMPLAINT][EXISTING] {mva} - no PM complaints found")
            return {"status": "no_pm", "mva": mva}

        # Click first matching PM complaint
        tile = pm_tiles[0]
        try:
            tile.click()
            log.info(f"[COMPLAINT][ASSOCIATED] {mva} - complaint '{tile.text.strip()}' selected")
        except Exception as e:
            log.warning(f"[COMPLAINT][WARN] {mva} - failed to click complaint tile → {e}")
            return {"status": "failed", "reason": "tile_click", "mva": mva}

        # Step 1: Complaint → Next
        from utils.ui_helpers import click_next_in_dialog
        if not click_next_in_dialog(driver, timeout=8):
            return {"status": "failed", "reason": "complaint_next", "mva": mva}

        # Step 2: Mileage → Next
        res = complete_mileage_dialog(driver, mva)
        if res.get("status") != "ok":
            return {"status": "failed", "reason": "mileage", "mva": mva}

        # Step 3: Opcode → PM Gas
        res = select_opcode(driver, mva, code_text="PM Gas")
        if res.get("status") != "ok":
            return {"status": "failed", "reason": "opcode", "mva": mva}

        return {"status": "associated", "mva": mva}

    except Exception as e:
        log.warning(f"[COMPLAINT][WARN] {mva} - complaint association failed → {e}")
        return {"status": "failed", "reason": "exception", "mva": mva}

def create_new_complaint(driver, mva: str) -> dict:
    """Create a new complaint when no suitable PM complaint exists."""
    log.debug(f"[COMPLAINT] {mva} - Creating new complaint.")
    log.info(f"[COMPLAINT][NEW] {mva} - creating new complaint")

    try:
        # 1. Click Add New Complaint (or Create New Complaint)
        if not (
            click_element(driver, (By.XPATH, "//button[normalize-space()='Add New Complaint']"))
            or click_element(driver, (By.XPATH, "//button[normalize-space()='Create New Complaint']"))
        ):

            log.warning(
                "[COMPLAINT][NEW][WARN] {mva} - could not click Add/Create New Complaint"
            )
            return {"status": "failed", "reason": "add_btn"}
        log.info(f"[COMPLAINT][NEW] {mva} - Add/Create New Complaint clicked")
        time.sleep(2)

        # 2. Handle Drivability (Yes/No). Simplest case -> always Yes
        if not click_element(driver, (By.XPATH, "//button[normalize-space()='Yes']")):
            log.warning(
                f"[COMPLAINT][NEW][WARN] {mva} - could not click Yes in Drivability step"
            )
            return {"status": "failed", "reason": "drivability"}
        log.info(f"[COMPLAINT][NEW] {mva} - Drivability Yes clicked")
        time.sleep(1)

        # 3) Complaint Type = PM (auto-advances, no Next button here)
        if click_element(driver, (By.XPATH, "//button[normalize-space()='PM']")):
            log.info(f"[COMPLAINT] {mva} - Complaint type 'PM' selected")
            time.sleep(2)  # allow auto-advance to Additional Info screen
        else:
            log.warning(f"[COMPLAINT][WARN] {mva} - Complaint type 'PM' not found")
            return {"status": "failed", "reason": "complaint_type", "mva": mva}

        # 4) Additional Info screen -> Submit
        if click_element(driver, (By.XPATH, "//button[normalize-space()='Submit Complaint']")):
            log.info(f"[COMPLAINT] {mva} - Additional Info submitted")
            time.sleep(2)
        else:
            log.warning(f"[COMPLAINT][WARN] {mva} - could not submit Additional Info")
            return {"status": "failed", "reason": "submit_info", "mva": mva}

        return {"status": "created"}


    except Exception as e:
        log.error(f"[COMPLAINT][NEW][ERROR] {mva} - creation failed -> {e}")
        return {"status": "failed", "reason": "exception"}

def click_next_in_dialog(driver, timeout: int = 10) -> bool:
    """
    Click the 'Next' button inside the active dialog.
    Returns True if clicked, False if not found.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        locator = (By.XPATH, "//button[normalize-space()='Next']")
        log.debug(f"[CLICK] attempting to click {locator} (dialog Next)")

        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        btn.click()

        log.info("[DIALOG] Next button clicked")
        return True

    except Exception as e:
        log.warning(f"[DIALOG][WARN] could not click Next button → {e}")
        return False
