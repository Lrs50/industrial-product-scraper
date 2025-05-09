from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup

import sys
import os
from pathlib import Path
from pprint import pprint

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_logger

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

class Parser(object):
    
    def __init__(self, url: str,log_to_console: bool = True, log_to_file: bool = False):
        
        self.logger = get_logger("Parser", to_console=log_to_console, to_file=log_to_file)
        self.url = url
        self.data = {}
        
        self.parsers = {
            "specs": self.parse_specs
        }
        
    def find_sessions(self,soup: Any) -> List[str]:
          
        info_box = soup.find("div", class_="c-tab")
        session_elements = info_box.find_all("li")
        
        names = [element.text.lower() for element in session_elements]  
        
        self.logger.info(f"Found sessions {names}")
        
        return names
        
    def run(self) -> Dict[str,Any]:
        
        self.logger.info(f"Started the Parser for item {self.url.split("/")[-1]}")
        
        response = requests.get(self.url,headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, "html.parser")
        
        self.parse_catalog(soup)
    
        session_names = self.find_sessions(soup)

        for session_name in session_names:
            if session_name in self.parsers:
                self.data[session_name] = self.parsers[session_name](soup)
                
            else:
                self.logger.warning(f"No parser implementation for {session_name.capitalize()}")
                
        return self.data    

    def parse_catalog(self,soup):
        
        """Extracts values from page catalog header"""
        
        catalog_div = soup.find("div",id="catalog-detail")
        
        title_tag = soup.find("div", class_="page-title")
        title = title_tag.get_text(strip=True) if title_tag else None

        desc_tag = catalog_div.find("div", class_="product-description")
        description = desc_tag.get_text(strip=True) if desc_tag else None
        
        detail_table_tag = catalog_div.find("table",class_="detail-table")
        info_tags = detail_table_tag.find_all("tr")
        
        self.data["info"] = {}
        
        for info_tag in info_tags:
            key_cell = info_tag.find("th")
            value_cell = info_tag.find("td")

            if key_cell and value_cell:
                key = key_cell.get_text(strip=True)
                value = value_cell.get_text(separator=" ", strip=True)
                self.data["info"][key] = value
        
        self.data["product_id"] = title
        self.data["description"] = description
    
    def parse_specs(self,soup):
        """Extracts key-value specs from the 'Specs' tab."""
        
        specs = {}
    
        specs_div = soup.find("div", class_="pane", attrs={"data-tab": "specs"})
        
        if not specs_div:
            self.logger.warning("Specs div not found")
        
        columns = specs_div.find_all("div", class_="col")
        
        for col in columns:
            for item in col.find_all("div",recursive=False):
                label = item.find("span",class_="label")
                value = item.find("span",class_="value")
                
                if label and value:
                    key = label.get_text(strip=True)
                    val = value.get_text(separator=", ",strip=True)
                    specs[key] = val
        
        self.logger.info("Sucessfully retrieved Specs info")    
        return specs   
    

def main():
    
    links = [
        #"https://www.baldor.com/catalog/027603",
        "https://www.baldor.com/catalog/1021W",
        #"https://www.baldor.com/catalog/CD1803R",
        #"https://www.baldor.com/catalog/BSM100C-1150AA"
    ]
    
    for url in links[:]:
        parser = Parser(url)
        data = parser.run()
        pprint(data)

if __name__ == "__main__":
    main()

