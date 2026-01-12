def navigate_back_to_home(driver):
    """
    Placeholder for navigation logic to return to the home page in the UI.
    """
    log.info("[NAV] Navigating back to home (stub function called)")
    # TODO: Implement actual navigation logic as needed
    pass
def find_elements(driver, locator, timeout=10):
    """
    Find all elements matching the locator within the timeout.
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.TYPE, "selector")
        timeout: Timeout in seconds
    Returns:
        List of WebElements (may be empty if none found)
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        return driver.find_elements(*locator)
    except TimeoutException:
        log.warning(f"Timeout waiting for elements: {locator}")
        return []
    except Exception as e:
        log.error(f"Error finding elements {locator}: {e}")
        return []
"""
UI Helper utilities for Selenium interactions.

Provides common helper functions for finding elements, clicking, sending text, etc.
"""

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from utils.logger import log


def safe_wait(driver, timeout, condition, desc="element"):
    """
    Safely wait for a condition with timeout.
    
    Args:
        driver: WebDriver instance
        timeout: Timeout in seconds
        condition: Expected condition or callable
        desc: Description for logging
        
    Returns:
        Element if found, None otherwise
    """
    try:
        element = WebDriverWait(driver, timeout).until(condition)
        return element
    except TimeoutException:
        log.warning(f"Timeout waiting for {desc}")
        return None
    except Exception as e:
        log.error(f"Error waiting for {desc}: {e}")
        return None


def find_element(driver, locator, timeout=10):
    """
    Find an element with explicit wait.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.TYPE, "selector")
        timeout: Timeout in seconds
        
    Returns:
        WebElement if found
        
    Raises:
        TimeoutException if element not found
    """
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located(locator)
    )


def click_element(driver, locator, timeout=10, desc=None):
    """
    Click an element with explicit wait.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.TYPE, "selector")
        timeout: Timeout in seconds
        desc: Description for logging
        
    Returns:
        bool: True if clicked successfully, False otherwise
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        element.click()
        if desc:
            log.info(f"Clicked {desc}")
        return True
    except TimeoutException:
        log.warning(f"Timeout waiting to click {desc or 'element'}")
        return False
    except Exception as e:
        log.error(f"Error clicking {desc or 'element'}: {e}")
        return False


def send_text(driver, locator, text, timeout=10):
    """
    Send text to an input field with explicit wait.
    
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.TYPE, "selector")
        text: Text to send
        timeout: Timeout in seconds
        
    Returns:
        bool: True if text sent successfully, False otherwise
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        element.clear()
        element.send_keys(text)
        return True
    except TimeoutException:
        log.warning(f"Timeout waiting to send text")
        return False
    except Exception as e:
        log.error(f"Error sending text: {e}")
        return False


def is_element_present(driver, locator, timeout=5):
    """
    Check if an element is present within the given timeout.
    Args:
        driver: WebDriver instance
        locator: Tuple of (By.TYPE, "selector")
        timeout: Timeout in seconds
    Returns:
        bool: True if element is present, False otherwise
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        return True
    except TimeoutException:
        return False
    except Exception as e:
        log.error(f"Error checking element presence: {e}")
        return False
