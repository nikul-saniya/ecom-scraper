"""
Amazon specific scraper implementation.
"""

import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scraper.base import BaseScraper


class AmazonScraper(BaseScraper):
    """Amazon specific scraper implementation"""

    def __init__(self, chromedriver_path=None):
        super().__init__(chromedriver_path)
        self.site_name = "Amazon"

    def generate_search_url(self, search_term):
        """Generate Amazon search URL"""
        formatted_term = "+".join(search_term.split())
        return f"https://www.amazon.in/s?k={formatted_term}"

    def extract_products(self, num_pages=1, search_term=""):
        """Extract products from Amazon search results"""
        all_products = []
        search_url = self.generate_search_url(search_term)

        try:
            driver = self.setup_driver()

            # Navigate to Amazon homepage first (helps avoid detection)
            driver.get("https://www.amazon.in/")
            time.sleep(random.uniform(2, 3))

            current_page = 1
            current_url = search_url

            while current_page <= num_pages:
                print(f"\nScraping {self.site_name} page {current_page} of {num_pages}")
                print(f"Navigating to: {current_url}")

                driver.get(current_url)

                # Wait for page to load
                try:
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item"))
                    )
                except TimeoutException:
                    print("Timeout waiting for results page to load.")

                # Scroll through the page
                self.scroll_page()

                # Find product containers
                selectors = [
                    "div.s-result-item[data-component-type='s-search-result']",
                    "div.sg-col-4-of-24.sg-col-4-of-12",
                    "div.sg-col-inner",
                    "div.s-result-item"
                ]

                product_containers = []
                for selector in selectors:
                    product_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(product_containers) > 0:
                        print(f"Found {len(product_containers)} products using selector: {selector}")
                        break

                if len(product_containers) == 0:
                    print("Could not find any product containers with known selectors")
                    break

                # Filter out non-product items
                filtered_containers = []
                for container in product_containers:
                    try:
                        # Check if this is actually a product
                        if (container.text and
                                ("₹" in container.text or
                                 "Prime" in container.text or
                                 any(keyword in container.text.lower() for keyword in
                                     ["keyboard", "delivery", "stars", "reviews"]))):
                            filtered_containers.append(container)
                    except:
                        continue

                print(f"After filtering, found {len(filtered_containers)} valid product containers")
                product_containers = filtered_containers

                page_products = []

                for container in product_containers:
                    try:
                        # Extract product details
                        product = {"site": self.site_name}

                        # Get container text for fallback extraction
                        container_text = container.text

                        # Try various selectors for title
                        title_selectors = [
                            "h2 a span",
                            ".a-size-medium.a-color-base.a-text-normal",
                            ".a-size-base-plus.a-color-base.a-text-normal",
                            ".a-link-normal .a-text-normal",
                            "h2"
                        ]

                        # Product title
                        for selector in title_selectors:
                            try:
                                title_element = container.find_element(By.CSS_SELECTOR, selector)
                                title_text = title_element.text.strip()
                                if title_text and len(title_text) > 5:
                                    product["title"] = title_text
                                    break
                            except:
                                continue

                        if "title" not in product:
                            # Fallback: extract title from container text
                            lines = container_text.split('\n')
                            for line in lines:
                                if len(line.strip()) > 10 and "sponsored" not in line.lower():
                                    product["title"] = line.strip()
                                    break
                            if "title" not in product:
                                product["title"] = "N/A"

                        # Product price
                        price_selectors = [
                            "span.a-price span.a-offscreen",
                            "span.a-price",
                            ".a-price .a-offscreen",
                            ".a-price-whole"
                        ]

                        for selector in price_selectors:
                            try:
                                price_element = container.find_element(By.CSS_SELECTOR, selector)
                                price_text = price_element.text.strip()
                                if not price_text and selector.endswith("a-offscreen"):
                                    price_text = price_element.get_attribute("textContent").strip()

                                if price_text:
                                    product["price"] = price_text
                                    break
                            except:
                                continue

                        if "price" not in product:
                            # Fallback: look for ₹ symbol in text
                            lines = container_text.split('\n')
                            for line in lines:
                                if '₹' in line:
                                    product["price"] = line.strip()
                                    break
                            if "price" not in product:
                                product["price"] = "N/A"

                        # Product rating
                        rating_selectors = [
                            "span.a-icon-alt",
                            "i.a-icon-star-small",
                            ".a-star-medium-4"
                        ]

                        for selector in rating_selectors:
                            try:
                                rating_element = container.find_element(By.CSS_SELECTOR, selector)
                                rating_text = rating_element.get_attribute("textContent").strip()
                                if not rating_text:
                                    rating_text = rating_element.text.strip()

                                if rating_text:
                                    product["rating"] = rating_text
                                    break
                            except:
                                continue

                        if "rating" not in product:
                            # Try to find ratings in text
                            for line in container_text.split('\n'):
                                if "out of 5 stars" in line or "stars" in line.lower():
                                    product["rating"] = line.strip()
                                    break
                            if "rating" not in product:
                                product["rating"] = "N/A"

                        # Number of reviews
                        review_selectors = [
                            "span.a-size-base.s-underline-text",
                            ".a-link-normal .a-size-base",
                            "[aria-label*='reviews']"
                        ]

                        for selector in review_selectors:
                            try:
                                review_element = container.find_element(By.CSS_SELECTOR, selector)
                                review_text = review_element.text.strip()
                                if review_text and any(c.isdigit() for c in review_text):
                                    product["reviews"] = review_text
                                    break
                            except:
                                continue

                        if "reviews" not in product:
                            product["reviews"] = "N/A"

                        # Product link
                        link_selectors = [
                            "h2 a",
                            ".a-link-normal",
                            "a[href*='/dp/']"
                        ]

                        for selector in link_selectors:
                            try:
                                link_elements = container.find_elements(By.CSS_SELECTOR, selector)
                                for link_element in link_elements:
                                    href = link_element.get_attribute("href")
                                    if href and ("/dp/" in href or "/gp/product/" in href):
                                        product["link"] = href
                                        break
                                if "link" in product:
                                    break
                            except:
                                continue

                        if "link" not in product:
                            product["link"] = "N/A"

                        # Product image
                        img_selectors = [
                            "img.s-image",
                            ".s-image",
                            "img[src*='images/I']"
                        ]

                        for selector in img_selectors:
                            try:
                                img_elements = container.find_elements(By.CSS_SELECTOR, selector)
                                for img_element in img_elements:
                                    src = img_element.get_attribute("src")
                                    if src and not src.endswith(".gif"):
                                        product["image_url"] = src
                                        break
                                if "image_url" in product:
                                    break
                            except:
                                continue

                        if "image_url" not in product:
                            product["image_url"] = "N/A"

                        # Add page number information
                        product["page"] = current_page

                        # Add product if we have at least title OR a valid link
                        if product["title"] != "N/A" or ("/dp/" in product.get("link", "")):
                            page_products.append(product)

                    except Exception as e:
                        continue

                print(f"Successfully extracted {len(page_products)} products from {self.site_name} page {current_page}")
                all_products.extend(page_products)

                # Check if we've reached the requested number of pages
                if current_page >= num_pages:
                    break

                # Find and click the next page button
                next_page_found = False
                try:
                    # Try multiple selectors for the next page button
                    next_page_selectors = [
                        ".s-pagination-item.s-pagination-next",
                        "a.s-pagination-next",
                        "li.a-last a",
                        "a[aria-label='Go to next page']"
                    ]

                    for selector in next_page_selectors:
                        try:
                            next_button = driver.find_element(By.CSS_SELECTOR, selector)
                            if "a-disabled" not in next_button.get_attribute("class"):
                                current_url = next_button.get_attribute("href")
                                next_page_found = True
                                break
                        except:
                            continue

                    if not next_page_found:
                        # Try to construct the next page URL manually
                        if "page=" in current_url:
                            # Replace existing page parameter
                            current_url = current_url.replace(f"page={current_page}", f"page={current_page + 1}")
                        else:
                            # Add page parameter
                            if "?" in current_url:
                                current_url += f"&page={current_page + 1}"
                            else:
                                current_url += f"?page={current_page + 1}"
                        next_page_found = True

                    if not next_page_found:
                        print(f"Could not find next page button. Stopping at page {current_page}.")
                        break

                    # Random wait between page navigations to mimic human behavior
                    time.sleep(random.uniform(3, 5))
                    current_page += 1

                except Exception as e:
                    print(f"Error navigating to next page: {str(e)}")
                    break

            print(f"Successfully extracted a total of {len(all_products)} products from {self.site_name}")
            return all_products

        except Exception as e:
            print(f"An error occurred during {self.site_name} scraping: {str(e)}")
            return all_products

        finally:
            self.close_driver()