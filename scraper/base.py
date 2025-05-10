"""
Base abstract class for all e-commerce scrapers.
"""

import os
import time
import random
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BaseScraper(ABC):
    """Base abstract class for all e-commerce scrapers"""

    def __init__(self, chromedriver_path=None):
        """Initialize the base scraper with common settings"""
        if not chromedriver_path:
            chromedriver_path = os.path.join(os.getcwd(), 'chromedriver-win64', 'chromedriver.exe')

        self.chromedriver_path = chromedriver_path
        self.driver = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
        ]

    def setup_driver(self):
        """Setup and configure the Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation
        chrome_options.add_argument(f"user-agent={random.choice(self.user_agents)}")

        self.driver = webdriver.Chrome(service=Service(self.chromedriver_path), options=chrome_options)
        self.driver.set_script_timeout(30)

        return self.driver

    def scroll_page(self, scroll_pause=1.0):
        """Scroll through the page like a human would"""
        print("Scrolling through page...")
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        scroll_points = range(0, total_height, viewport_height // 2)

        for point in scroll_points:
            self.driver.execute_script(f"window.scrollTo(0, {point});")
            # Random wait between scrolls to mimic human behavior
            time.sleep(random.uniform(0.5, scroll_pause))

        # Let the page settle after scrolling
        time.sleep(2)

    def close_driver(self):
        """Close the selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    @abstractmethod
    def generate_search_url(self, search_term):
        """Generate the search URL for the given term"""
        pass

    @abstractmethod
    def extract_products(self, num_pages=1, search_term=""):
        """Extract products from search results"""
        pass