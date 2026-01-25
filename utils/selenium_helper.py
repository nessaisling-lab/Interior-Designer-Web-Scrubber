"""Selenium helper utilities for JavaScript-rendered pages."""

import time
from typing import Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Check Selenium version
try:
    import selenium
    SELENIUM_VERSION = tuple(map(int, selenium.__version__.split('.')[:2]))
    SELENIUM_4 = SELENIUM_VERSION >= (4, 0)
except (ImportError, AttributeError):
    SELENIUM_4 = False
    SELENIUM_VERSION = (3, 141)

# Import Service class based on version
if SELENIUM_4:
    try:
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        try:
            from selenium.webdriver.remote.service import Service
        except ImportError:
            Service = None
else:
    Service = None

# Patch urllib3 BEFORE any webdriver_manager import to avoid timeout issues
# Also restore original if webdriver_manager has already patched it
try:
    import urllib3.util.connection as urllib3_connection
    # If webdriver_manager has already patched it, restore original first
    if hasattr(urllib3_connection, '_orig_create_connection'):
        # Restore original
        urllib3_connection.create_connection = urllib3_connection._orig_create_connection
    
    # Save original if not already saved
    if not hasattr(urllib3_connection, '_orig_create_connection'):
        urllib3_connection._orig_create_connection = urllib3_connection.create_connection
    
    # Patch to handle webdriver_manager's incompatible timeout objects
    def patched_create_connection(address, timeout=None, source_address=None, socket_options=None):
        # Fix webdriver_manager timeout object issue
        if timeout is not None and not isinstance(timeout, (int, float)):
            timeout = None
        return urllib3_connection._orig_create_connection(address, timeout, source_address, socket_options)
    
    urllib3_connection.create_connection = patched_create_connection
except Exception:
    pass  # If patching fails, continue anyway

# Try chromedriver-autoinstaller first (more reliable)
try:
    import chromedriver_autoinstaller
    HAS_CHROMEDRIVER_AUTO = True
except ImportError:
    HAS_CHROMEDRIVER_AUTO = False

# Don't import webdriver_manager at module level - import it only when needed
# This prevents it from patching urllib3 before we can fix it
# We'll check for it dynamically when needed

from utils.logger import get_logger

logger = get_logger(__name__)


class SeleniumHelper:
    """Helper class for Selenium-based web scraping."""
    
    def __init__(self, headless: bool = True, wait_time: int = 10):
        """
        Initialize Selenium helper.
        
        Args:
            headless: Run browser in headless mode
            wait_time: Default wait time for elements in seconds
        """
        self.headless = headless
        self.wait_time = wait_time
        self.driver = None
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver."""
        # Fix webdriver_manager timeout patching issue BEFORE creating driver
        try:
            import urllib3.util.connection as urllib3_conn
            # Check if webdriver_manager has patched it with incompatible timeout
            original_func = getattr(urllib3_conn, '_orig_create_connection', None)
            if original_func:
                # Restore original
                urllib3_conn.create_connection = original_func
            else:
                # Save current as original and patch
                urllib3_conn._orig_create_connection = urllib3_conn.create_connection
                
                def safe_create_connection(address, timeout=None, source_address=None, socket_options=None):
                    # Fix webdriver_manager's incompatible timeout object
                    if timeout is not None and not isinstance(timeout, (int, float)):
                        timeout = None
                    return urllib3_conn._orig_create_connection(address, timeout, source_address, socket_options)
                
                urllib3_conn.create_connection = safe_create_connection
        except Exception as patch_error:
            logger.debug(f"Could not patch urllib3: {patch_error}")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Additional options for better compatibility
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Disable images and CSS for faster loading (optional)
        # prefs = {
        #     "profile.managed_default_content_settings.images": 2,
        #     "profile.managed_default_content_settings.stylesheets": 2
        # }
        # chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # Try chromedriver-autoinstaller first (avoids webdriver_manager timeout issues)
            driver_path = None
            use_autoinstaller = False
            
            if HAS_CHROMEDRIVER_AUTO:
                try:
                    import chromedriver_autoinstaller
                    import ssl
                    # Disable SSL verification for chromedriver-autoinstaller (common issue on Windows)
                    ssl._create_default_https_context = ssl._create_unverified_context
                    # This installs/updates chromedriver and adds it to PATH
                    chromedriver_autoinstaller.install()
                    # chromedriver-autoinstaller adds chromedriver to PATH, so we don't need explicit path
                    use_autoinstaller = True
                    logger.info("Using chromedriver-autoinstaller (ChromeDriver added to PATH)")
                except Exception as auto_error:
                    logger.debug(f"chromedriver-autoinstaller failed: {auto_error}")
                    use_autoinstaller = False
                    # Restore SSL context
                    try:
                        import ssl
                        ssl._create_default_https_context = ssl.create_default_context
                    except:
                        pass
            
            # Only use webdriver_manager if chromedriver-autoinstaller is not available
            # Skip webdriver_manager entirely if autoinstaller succeeded
            if not use_autoinstaller and HAS_WEBDRIVER_MANAGER:
                try:
                    import os
                    import platform
                    # Check cache directory first to avoid webdriver_manager timeout issues
                    cache_base = os.path.expanduser('~/.wdm/drivers/chromedriver')
                    if os.path.exists(cache_base):
                        # Look for chromedriver.exe in cache (prefer win64)
                        for root, dirs, files in os.walk(cache_base):
                            if 'chromedriver.exe' in files:
                                found_path = os.path.join(root, 'chromedriver.exe')
                                # Prefer win64 if available
                                if 'win64' in root:
                                    driver_path = found_path
                                    logger.info(f"Found win64 ChromeDriver in cache: {driver_path}")
                                    break
                                elif driver_path is None:
                                    # Fallback to any chromedriver.exe found
                                    driver_path = found_path
                    
                    # If not in cache, use webdriver_manager to download (but catch timeout errors)
                    if not driver_path or not os.path.exists(driver_path):
                        try:
                            manager = ChromeDriverManager()
                            # This may raise timeout error, but we'll catch it
                            raw_path = manager.install()
                            raw_path = os.path.normpath(raw_path)
                            
                            # Find chromedriver.exe in the returned path
                            if os.path.isdir(raw_path):
                                for root, dirs, files in os.walk(raw_path):
                                    if 'chromedriver.exe' in files:
                                        driver_path = os.path.join(root, 'chromedriver.exe')
                                        break
                            elif raw_path.endswith('.exe') and 'chromedriver' in raw_path.lower():
                                driver_path = raw_path
                            else:
                                search_dir = os.path.dirname(raw_path) if os.path.isfile(raw_path) else raw_path
                                for root, dirs, files in os.walk(search_dir):
                                    if 'chromedriver.exe' in files:
                                        driver_path = os.path.join(root, 'chromedriver.exe')
                                        break
                        except Exception as wdm_error:
                            # webdriver_manager timeout/compatibility issue - use cached path if available
                            if 'timeout' in str(wdm_error).lower() or 'connect' in str(wdm_error).lower():
                                logger.debug(f"webdriver_manager timeout issue (known compatibility problem): {wdm_error}")
                                # We'll use the cached path found above
                            else:
                                raise wdm_error
                    
                    # Verify the file exists
                    if driver_path and os.path.exists(driver_path) and os.path.isfile(driver_path):
                        logger.info(f"Using ChromeDriver: {driver_path}")
                    else:
                        logger.warning(f"ChromeDriver executable not found")
                        driver_path = None
                except Exception as e:
                    logger.warning(f"Could not get ChromeDriver: {e}")
                    logger.info("Falling back to system PATH for ChromeDriver")
                    driver_path = None
            
            # Selenium 3.x uses executable_path and chrome_options
            # Try Selenium 3.x API first (most compatible)
            driver = None
            if use_autoinstaller:
                # chromedriver-autoinstaller handles PATH, use direct method
                # Fix urllib3 timeout issue right before creating driver
                # Aggressively patch urllib3 to fix webdriver_manager timeout issue
                try:
                    import urllib3.util.connection as urllib3_conn
                    import urllib3.poolmanager
                    import urllib3.connectionpool
                    
                    # Save original if exists
                    if not hasattr(urllib3_conn, '_orig_create_connection'):
                        urllib3_conn._orig_create_connection = urllib3_conn.create_connection
                    
                    # Patch create_connection to fix timeout object issue
                    def safe_create_connection(address, timeout=None, source_address=None, socket_options=None):
                        if timeout is not None and not isinstance(timeout, (int, float)):
                            timeout = None
                        return urllib3_conn._orig_create_connection(address, timeout, source_address, socket_options)
                    
                    urllib3_conn.create_connection = safe_create_connection
                    
                    # Also patch ConnectionPool's _new_conn method if it exists
                    if hasattr(urllib3.connectionpool.HTTPConnectionPool, '_new_conn'):
                        orig_new_conn = urllib3.connectionpool.HTTPConnectionPool._new_conn
                        def patched_new_conn(self):
                            # Fix timeout in connection creation
                            conn = orig_new_conn(self)
                            return conn
                        urllib3.connectionpool.HTTPConnectionPool._new_conn = patched_new_conn
                        
                except Exception as patch_err:
                    logger.debug(f"Could not patch urllib3 completely: {patch_err}")
                
                try:
                    # chromedriver-autoinstaller adds ChromeDriver to PATH, so we can use direct method
                    # For Selenium 4.x, use options instead of chrome_options
                    if SELENIUM_4:
                        driver = webdriver.Chrome(options=chrome_options)
                        logger.info("Successfully created Chrome driver using Selenium 4.x API with chromedriver-autoinstaller")
                    else:
                        driver = webdriver.Chrome(chrome_options=chrome_options)
                        logger.info("Successfully created Chrome driver using Selenium 3.x API with chromedriver-autoinstaller")
                except Exception as auto_error:
                    error_msg = str(auto_error).lower()
                    if "timeout" in error_msg:
                        # The urllib3 patch didn't work - webdriver_manager has already patched it
                        # Try to reload urllib3 and patch again
                        logger.warning("Timeout error detected. Attempting to reload and re-patch urllib3...")
                        try:
                            import importlib
                            import urllib3.util.connection as urllib3_conn
                            importlib.reload(urllib3_conn)
                            # Re-apply patch
                            if not hasattr(urllib3_conn, '_orig_create_connection'):
                                urllib3_conn._orig_create_connection = urllib3_conn.create_connection
                            def safe_conn(address, timeout=None, source_address=None, socket_options=None):
                                if timeout is not None and not isinstance(timeout, (int, float)):
                                    timeout = None
                                return urllib3_conn._orig_create_connection(address, timeout, source_address, socket_options)
                            urllib3_conn.create_connection = safe_conn
                            
                            # Try again - chromedriver-autoinstaller adds to PATH, so use direct method
                            if SELENIUM_4:
                                driver = webdriver.Chrome(options=chrome_options)
                                logger.info("Successfully created Chrome driver after urllib3 reload (Selenium 4.x)")
                            else:
                                driver = webdriver.Chrome(chrome_options=chrome_options)
                                logger.info("Successfully created Chrome driver after urllib3 reload (Selenium 3.x)")
                        except Exception as reload_error:
                            logger.error(f"Failed to fix timeout issue: {reload_error}")
                            logger.warning("ChromeDriver is installed via chromedriver-autoinstaller, but webdriver_manager compatibility issue persists.")
                            raise auto_error
                    else:
                        raise auto_error
            elif driver_path:
                import os
                # Verify path exists
                if os.path.exists(driver_path) and os.path.isfile(driver_path):
                    # Use Selenium's Service class to avoid webdriver_manager timeout issues
                    try:
                        # Use Service class for webdriver_manager paths
                        from selenium.webdriver.remote.service import Service as RemoteService
                        service = RemoteService(executable_path=driver_path)
                        driver = webdriver.Chrome(service=service, chrome_options=chrome_options)
                        logger.info(f"Successfully created Chrome driver using Service class")
                    except Exception as service_error:
                        logger.debug(f"Service method failed: {service_error}, trying direct method...")
                        # Fallback to direct method
                        try:
                            driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
                            logger.info(f"Successfully created Chrome driver using direct method")
                        except Exception as e1:
                            error_msg = str(e1).lower()
                            if "timeout" in error_msg or "connect" in error_msg:
                                logger.warning(f"Timeout error (webdriver_manager compatibility issue): {e1}")
                                logger.info("Attempting to add ChromeDriver directory to PATH...")
                                # Add driver directory to PATH and try again
                                import os
                                import sys
                                driver_dir = os.path.dirname(driver_path)
                                old_path = os.environ.get('PATH', '')
                                os.environ['PATH'] = driver_dir + os.pathsep + old_path
                                try:
                                    # Try without executable_path, using PATH
                                    driver = webdriver.Chrome(chrome_options=chrome_options)
                                    logger.info("Successfully created Chrome driver using PATH method")
                                except Exception as path_error:
                                    logger.error(f"All methods failed. Last error: {path_error}")
                                    raise Exception("ChromeDriver initialization failed. "
                                                  "This is a known compatibility issue. "
                                                  "Try manually adding ChromeDriver to system PATH or upgrade to Selenium 4.x")
                            else:
                                raise e1
                    except Exception as e1:
                        logger.debug(f"Unexpected error: {e1}")
                        # Try Selenium 4.x API if available
                        if SELENIUM_4:
                            try:
                                service = Service(driver_path)
                                driver = webdriver.Chrome(service=service, options=chrome_options)
                                logger.info("Successfully created Chrome driver using Selenium 4.x API")
                            except Exception as e2:
                                logger.debug(f"Selenium 4.x API also failed: {e2}")
                                raise e1
                        else:
                            raise e1
                else:
                    logger.warning(f"ChromeDriver path does not exist: {driver_path}")
                    driver_path = None
            
            # If driver_path is None or previous attempt failed, try system PATH
            if driver_path is None:
                try:
                    driver = webdriver.Chrome(chrome_options=chrome_options)
                except TypeError:
                    # Try without chrome_options for newer Selenium
                    driver = webdriver.Chrome(options=chrome_options)
            
            driver.implicitly_wait(self.wait_time)
            return driver
        except Exception as e:
            logger.error(f"Failed to create Chrome driver: {e}")
            logger.info("Make sure Chrome browser is installed. ChromeDriver will be downloaded automatically.")
            raise
    
    def get_page_source(self, url: str, wait_for_selector: Optional[str] = None, wait_time: Optional[int] = None) -> Optional[str]:
        """
        Fetch page source after JavaScript execution.
        
        Args:
            url: URL to fetch
            wait_for_selector: Optional CSS selector to wait for before returning page source
            wait_time: Optional custom wait time
            
        Returns:
            Page source HTML as string or None if failed
        """
        if self.driver is None:
            try:
                self.driver = self._create_driver()
            except Exception as e:
                logger.error(f"Could not initialize Selenium driver: {e}")
                return None
        
        try:
            logger.debug(f"Loading page with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for specific element if selector provided
            if wait_for_selector:
                wait = wait_time or self.wait_time
                try:
                    WebDriverWait(self.driver, wait).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                    logger.debug(f"Found element with selector: {wait_for_selector}")
                except TimeoutException:
                    logger.warning(f"Timeout waiting for selector: {wait_for_selector}")
                    # Continue anyway - page might still have content
            
            # Additional wait for JavaScript to finish
            time.sleep(2)  # Give JavaScript time to render
            
            return self.driver.page_source
            
        except WebDriverException as e:
            logger.error(f"Selenium error loading {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Selenium: {e}")
            return None
    
    def get_soup(self, url: str, wait_for_selector: Optional[str] = None, wait_time: Optional[int] = None) -> Optional[BeautifulSoup]:
        """
        Get BeautifulSoup object from JavaScript-rendered page.
        
        Args:
            url: URL to fetch
            wait_for_selector: Optional CSS selector to wait for
            wait_time: Optional custom wait time
            
        Returns:
            BeautifulSoup object or None if failed
        """
        page_source = self.get_page_source(url, wait_for_selector, wait_time)
        if page_source:
            return BeautifulSoup(page_source, 'html.parser')
        return None
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
