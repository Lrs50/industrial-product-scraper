"""
Baldor Website Navigation Guide
===============================

Main Entry Points:
------------------
- Home: https://www.baldor.com/
- Catalog: https://www.baldor.com/catalog
- Product Offering (visual/brand overview): accessible from homepage

Catalog Structure:
------------------
- Catalog is divided by product categories.
  Example:
    - AC Motors: https://www.baldor.com/catalog#category=2
    - DC Motors: https://www.baldor.com/catalog#category=4

Note: The "#category=..." is a fragment identifier and handled client-side via JavaScript.

Product Listing:
----------------
- The catalog page uses **infinite scroll** to load product listings dynamically.
- Products are loaded progressively as the user scrolls down.
- Each product card links to a dedicated product detail page.

Product Pages:
--------------
- Each product page contains full technical information and specifications.
- These pages are static and can be fetched directly.

Examples:
- https://www.baldor.com/catalog/M2338T
- https://www.baldor.com/catalog/GPL3310

Baldor API:
-----------
- Behind the scenes, the infinite scroll loads data via an internal REST API.
- The endpoint is:

  https://www.baldor.com/api/products

- Parameters:
    - include: "results"
    - language: "en-US"
    - pageIndex: controls pagination (starts at 0)
    - pageSize: number of items per page (typically 10 or more)
    - category: the numeric category ID (e.g., 2 for AC Motors)

- Example API request:

  https://www.baldor.com/api/products?include=results&language=en-US&pageIndex=32&pageSize=10&category=2

- The response is a JSON object with product metadata under:
    data["results"]["matches"]

- This API can be used to efficiently retrieve all product codes for a given category,
  bypassing the need to render or scroll the web interface.

Alternative Pages:
------------------
- The "Product Offering" and "Resources & Support" sections are more visual or redundant.
- They are not ideal starting points for crawling.
"""


from playwright.sync_api import sync_playwright
import requests
from typing import List, Tuple,Dict, Any,Optional

# import sys
# import os
# from pathlib import Path
# from pprint import pprint

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import *

class Crawler(object):
    
    """
    The Crawler is responsible for automatically navigating through the website’s catalog pages,
    collecting the URLs of individual product pages.
    """
    
    def __init__(self, log_to_console: bool = True, log_to_file: bool = False):
        """
        Initializes the Crawler instance.

        Sets up the logger for the crawler and prepares internal state.
        The crawler is responsible for navigating the Baldor online catalog,
        extracting category links using Playwright, and collecting product
        page URLs via their paginated public API.

        Args:
            log_to_console (bool): Whether to enable console logging output.
            log_to_file (bool): Whether to enable file-based logging output.
        """
        self.logger = get_logger("Crawler", to_console=log_to_console, to_file=log_to_file)
        
    def setup_browser(self) -> None:
        """
        Launches a headless Firefox browser using Playwright and creates a new page.
        """
        
        self.logger.debug("Launching browser...")
        playwright = sync_playwright().start()
        self.playwright = playwright
        self.browser = playwright.firefox.launch(headless=True)
        self.page = self.browser.new_page()
    
    def teardown_browser(self) -> None:
        """
        Closes the browser and stops the Playwright context.
        """
        
        self.logger.debug("Closing browser.")
        self.browser.close()
        self.playwright.stop()
        
    def run(self) -> Tuple[List[str], List[dict]]:
        """
        Executes the full crawling workflow and returns both product page URLs and raw product metadata.

        Returns:
            Tuple[List[str], List[dict]]: 
                - A list of product page URLs (e.g., "https://www.baldor.com/catalog/...")
                - A list of raw product metadata dictionaries retrieved from the API
        """
        
        self.logger.info("Starting the Crawler...")
        self.url = "https://www.baldor.com/catalog"
        self.products: List[str] = []
        self.product_matches: List[str] = []
        
        try:
            self.setup_browser()
            self.categories = self.find_categories()
            self.scrape_products()
                
        except Exception as e:
            self.logger.exception(f"Crawler failed: {e}")
            return []
        finally:
            self.teardown_browser()

        self.logger.info(f"Finished crawling. Total products collected: {len(self.products)}")
        return self.products,self.product_matches
    
    def scrape_products(self) -> None:
        """
        Scrapes product URLs and raw product data from all registered categories.

        Iterates through the list of categories, fetches all associated products using the Baldor API,
        and builds a list of product page URLs. Also stores the raw product metadata returned by the API.

        This function populates:
            - self.products: A list of product page URLs (one per product code)
            - self.product_matches: The full product metadata from the API for all categories

        Logs progress and handles API or parsing errors gracefully.
        """
        
        for name,url in self.categories:
            try:
                self.logger.info(f"Fetching items from category {name}")
                category_id = url.split("#category=")[-1]
                codes,product_matches = self.fetch_category_products_and_codes(category_id)

                product_urls = [f"https://www.baldor.com/catalog/{code}" for code in codes]                
                self.products.extend(product_urls)
                self.product_matches.extend(product_matches)
                        
            except Exception as e:
                self.logger.exception(f"Failed to fetch products for category '{name}': {e}")
                continue
            
    def extract_category_names(self) -> List[str]:
        """
        Extracts and returns the cleaned names of all subcategories on the catalog page.

        Navigates to the main catalog URL, waits for the subcategory elements to load,
        and parses their text content into a clean list of names.

        Returns:
            List[str]: A list of cleaned subcategory names.
        """
        
        self.page.goto(self.url,timeout=30000, wait_until="domcontentloaded")
        self.page.wait_for_selector("li.subcategory",timeout=10000)
        subcategories = self.page.query_selector_all("li.subcategory")  
        
        return [self.clean_subcategory_name(sc) for sc in subcategories]
    
    def clean_subcategory_name(self, element: Any) -> str:
        """
        Cleans the text content of a subcategory HTML element.

        Replaces line breaks with spaces and trims leading/trailing whitespace
        to produce a standardized subcategory name.

        Args:
            element (Any): The Playwright element representing a subcategory.

        Returns:
            str: The cleaned subcategory name as a single-line string.
        """
        
        return " ".join(element.inner_text().split("\n")).strip()
    
    def resolve_category_url(self,name: str) -> Optional[Tuple[str,str]]:
        """
        Finds and returns the URL associated with a given category name.

        Simulates a user click on the category element and captures the resulting
        navigation URL. If the category is not found or the process fails,
        logs the issue and returns None.

        Args:
            name (str): The cleaned name of the category to locate.

        Returns:
            Tuple[str, str]: A tuple (category name, category URL) if found, or None otherwise.
        """
        
        page = self.browser.new_page()
        try:   
            page.goto(self.url)
            page.wait_for_selector("li.subcategory")
            subcategories = page.query_selector_all("li.subcategory")
            
            for subcat in subcategories:
                if name == self.clean_subcategory_name(subcat):
                    
                    link_element = subcat.query_selector("a")
                    if link_element:
                        with page.expect_navigation():
                            link_element.click()
                            return name,page.url
                    else:
                       self.logger.warning(f"No <a> found in category '{name}'") 
            
        except Exception as e:
            self.logger.error(f"Failed to resolve category '{name}': {e}")
        finally:
            page.close()
            
        return None
    
    def find_categories(self) -> List[Tuple[str,str]]:
        """
        Finds all product categories by extracting their names and resolving their URLs.

        This method:
            - Extracts subcategory names from the catalog page
            - Resolves each name to its corresponding URL via simulated clicks
            - Logs the progress and any errors encountered

        Returns:
            List[Tuple[str, str]]: A list of (category name, category URL) tuples.
            Returns an empty list if extraction fails.
        """
        
        self.logger.info("Scraping the categories...")
        
        try:
            
            category_names = self.extract_category_names()
            categories: List[Tuple[str,str]] = []
            
            for name in category_names:
                category = self.resolve_category_url(name)
                if category:
                    self.logger.info(f"Found category: {category[0]} → {category[1]}")
                    categories.append(category) 
                     
            return categories
        
        except Exception as e:
            self.logger.exception(f"Error while finding categories: {e}")
            return []
        
    def get_products(self,category_id: int, page_index: int = 0, page_size: int = 10) -> Dict[str,Any]:
        """
        Fetches product data from the Baldor API for a given category and page.

        Sends a GET request with specified parameters and headers. Handles transient
        failures using a resilient session and logs any errors that occur.

        Args:
            category_id (int): The numeric ID of the product category to query.
            page_index (int): The index of the results page to fetch (default is 0).
            page_size (int): The number of products to fetch per page (default is 10).

        Returns:
            Dict[str, Any]: The JSON response from the API as a dictionary.
            On failure, returns a fallback structure: {"results": {"matches": []}}.
        """
        
        url = "https://www.baldor.com/api/products"
        params = {
            "include": "results",
            "language": "en-US",
            "pageIndex": page_index,
            "pageSize": page_size,
            "category": category_id
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Referer": "https://www.baldor.com/catalog",
        }

        try:
            attach_urllib3_to_logger(self.logger)
            
            session = create_resilient_session()
            response = session.get(url, params=params, headers=headers,timeout=10)
            response.raise_for_status()  # will raise if status != 200
            
            return response.json()
        
        except requests.RequestException as e:
            self.logger.error(f"[API ERROR] Category={category_id}, Page={page_index}: {e}")
            return {"results": {"matches": []}}
        except Exception as e:
            self.logger.error(f"[UNEXPECTED ERROR] during request: {e}")
            return {"results": {"matches": []}}

    def fetch_category_products_and_codes(self, category_id: int, page_size: int = 1000) -> Tuple[List[str], List[Any]]:
        """
        Fetches all products and their codes for a given category by paginating through the Baldor API.
        Args:
            category_id (int): The numeric ID of the category to fetch products from.
            page_size (int): Number of products to request per page (default is 1000).

        Returns:
            Tuple[List[str], List[Any]]: A tuple containing:
                - A list of product codes retrieved from the category.
                - A list of the full product entries returned by the API.
        """
                
        all_codes = []
        all_products = []
        page_index = 0

        while True:
            self.logger.debug(f"Requesting page {page_index} for category {category_id}...")
            data = self.get_products(category_id, page_index, page_size)
            
            try:
                products = data["results"]["matches"]
            except Exception as e:
                self.logger.exception(f"Error while parsing category data on page {page_index}: {e}")
                products = []

            if not products:
                break  # no more pages
            
            try:
                codes = [product["code"] for product in products]
            except TypeError as e:
                self.logger.error(f"Invalid format in product data on page {page_index}: {e}")
                codes = []
                
            all_codes.extend(codes)
            all_products.extend(products)
            self.logger.info(f"Fetched page {page_index} with {len(products)} products")

            page_index += 1

        self.logger.info(f"Finished collecting products for category {category_id}. Total: {len(all_codes)}")
        return all_codes,all_products
 
def main():
    
    crawler = Crawler()
    urls,metadata = crawler.run()

    # pprint(urls[10])
    # pprint(metadata[10])

if __name__ == "__main__":
    main()