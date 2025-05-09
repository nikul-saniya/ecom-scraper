import os
import time
import random
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd


def scrape_amazon_products(search_url, num_pages=1):
    """
    Scrape Amazon products from multiple pages of search results
    """
    # Set up Chrome options
    chromedriver_path = os.path.join(os.getcwd(), 'chromedriver-win64', 'chromedriver.exe')

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Hide automation

    # Rotate between different common user agents to avoid detection
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")

    all_products = []

    try:
        # Initialize the Chrome driver
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)

        # Set script timeout
        driver.set_script_timeout(30)

        # Navigate to Amazon homepage first (helps avoid detection)
        driver.get("https://www.amazon.in/")
        time.sleep(random.uniform(2, 3))  # Random wait to mimic human behavior

        current_page = 1
        current_url = search_url

        while current_page <= num_pages:
            print(f"\nScraping page {current_page} of {num_pages}")
            print(f"Navigating to: {current_url}")

            driver.get(current_url)

            # Add a longer wait time to ensure page loads completely
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.s-result-item"))
                )
            except TimeoutException:
                print("Timeout waiting for results page to load.")
                # Try to continue anyway

            # Scroll like a human would
            print("Scrolling through page...")
            total_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            scroll_points = range(0, total_height, viewport_height // 2)

            for point in scroll_points:
                driver.execute_script(f"window.scrollTo(0, {point});")
                # Random wait between scrolls to mimic human behavior
                time.sleep(random.uniform(0.5, 1.2))

            # Let the page settle after scrolling
            time.sleep(2)

            # Try multiple selector strategies to find products
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

            # Filter out sponsored products and other non-product items
            filtered_containers = []
            for container in product_containers:
                try:
                    # Check if this is actually a product (has at least some product text or price)
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

            for i, container in enumerate(product_containers):
                try:
                    # Extract product details
                    product = {}

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
                            if title_text and len(title_text) > 5:  # Ensure it's a meaningful title
                                product["title"] = title_text
                                break
                        except:
                            continue

                    if "title" not in product:
                        # Fallback: extract title from container text (first substantial line)
                        lines = container_text.split('\n')
                        for line in lines:
                            if len(line.strip()) > 10 and "sponsored" not in line.lower():
                                product["title"] = line.strip()
                                break
                        if "title" not in product:
                            product["title"] = "N/A"

                    # Product price - try multiple strategies
                    price_found = False
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
                                price_found = True
                                break
                        except:
                            continue

                    if not price_found:
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
                        # Try to find ratings in text (like "4.5 out of 5 stars")
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

                    # Try to extract brand/manufacturer
                    brand_found = False
                    for line in container_text.split('\n'):
                        # Look for brand text that's typically near the top before price
                        if line.strip() and len(line.strip()) < 30 and line.strip() != product.get("title", ""):
                            if "price" not in line.lower() and "₹" not in line:
                                product["brand"] = line.strip()
                                brand_found = True
                                break

                    if not brand_found:
                        product["brand"] = "N/A"

                    # Try to extract delivery info
                    for line in container_text.split('\n'):
                        if any(keyword in line.lower() for keyword in ["delivery", "free", "arrives", "shipping"]):
                            product["delivery"] = line.strip()
                            break
                        elif "prime" in line.lower():
                            product["delivery"] = "Prime"
                            break
                    if "delivery" not in product:
                        product["delivery"] = "N/A"

                    # Add product if we have at least title OR a valid link
                    if product["title"] != "N/A" or ("/dp/" in product.get("link", "")):
                        # Check if this is actually a product (if we have a title)
                        if product["title"] != "N/A":
                            # Add page number information
                            product["page"] = current_page
                            page_products.append(product)

                except Exception as e:
                    continue

            print(f"Successfully extracted {len(page_products)} products from page {current_page}")
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
                    "a:contains('Next')",
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

        print(f"Successfully extracted a total of {len(all_products)} products from {current_page} pages")
        return all_products

    except Exception as e:
        print(f"An error occurred during scraping: {str(e)}")
        return all_products  # Return any products we managed to collect before the error

    finally:
        # Close the browser
        try:
            driver.quit()
        except:
            pass


def main():
    # Setup command line argument parser
    parser = argparse.ArgumentParser(description='Amazon Product Scraper')
    parser.add_argument('search_term', nargs='*', default=['keyboard'],
                        help='Search term(s) to look for on Amazon')
    parser.add_argument('-p', '--pages', type=int, default=1,
                        help='Number of pages to scrape (default: 1)')
    parser.add_argument('-o', '--output', type=str, default='',
                        help='Output file name (default: based on search term)')

    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)

    search_term = "+".join(args.search_term)
    search_url = f"https://www.amazon.in/s?k={search_term}"

    if args.output:
        filename = args.output
        if not filename.endswith('.csv'):
            filename += '.csv'
        filename = os.path.join('output', filename)
    else:
        clean_term = "_".join(args.search_term)
        filename = f"output/amazon_{clean_term}_{args.pages}_pages.csv"

    print("Amazon Multi-Page Product Scraper - Starting...")
    print(f"Searching for: {' '.join(args.search_term)}")
    print(f"Number of pages to scrape: {args.pages}")
    print(f"Output file: {filename}")

    # Try up to 3 times with different user agents if needed
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt} of {max_attempts}")
        products = scrape_amazon_products(search_url, args.pages)

        if products and len(products) > 0:
            # Convert to DataFrame for better display
            df = pd.DataFrame(products)
            print("\n✓ Scraping Successful!")
            print(f"Total products scraped: {len(products)}")

            # Display sample data
            pd.set_option('display.max_colwidth', 30)  # Limit column width for display
            print("\nSample data (first 5 products):")
            display_cols = ["title", "price", "rating", "page"]
            if len(df) >= 5:
                print(df[display_cols].head())
            else:
                print(df[display_cols])

            # Save to CSV
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\nData saved to {filename}")
            break
        else:
            print(f"Attempt {attempt} failed to scrape any products.")
            if attempt < max_attempts:
                print("Retrying with different settings...")
                time.sleep(3)  # Wait before retrying
    else:
        print("\n❌ All attempts failed. No products were successfully scraped.")


if __name__ == "__main__":
    main()