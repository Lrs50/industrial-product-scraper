from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import json

# import sys
# import os
# from pathlib import Path
# from pprint import pprint

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import *

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

def normalize_spaces(text: str) -> str:
    return ' '.join(text.split())

class Parser(object):
    
    def __init__(self,log_to_console: bool = True, log_to_file: bool = False):
        """
        Initializes the parser with the target URL and logging preferences.

        Args:
            log_to_console (bool): Whether to log to the console.
            log_to_file (bool): Whether to log to a file.
        """
        
        self.logger = get_logger("Parser", to_console=log_to_console, to_file=log_to_file)
        attach_urllib3_to_logger(self.logger)
        
        self.data : dict = {}
        
        self.parsers = {
            "specs":        self.parse_specs,
            "nameplate":    self.parse_nameplate,
            "performance":  self.parse_performance,
            "parts":        self.parse_parts,
            "accessories":  self.parse_accessories,
            "drawings":     self.parse_drawings
        }
        
    def find_sessions(self,soup: BeautifulSoup) -> List[str]:
        """
        Finds the names of all session tabs in the c-tab section of the page.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the page.

        Returns:
            List[str]: List of lowercase session names.
        """
        
        info_box = soup.find("div", class_="c-tab")
        if info_box is None:
            self.logger.warning("No c-tab section found in HTML.")
            return []
        
        session_elements = info_box.find_all("li")
        names = [element.text.lower() for element in session_elements]  
        self.logger.info(f"Found sessions {names}")
        
        return names
      
    def run(self, url: str) -> Dict[str,Any]:
        """
        Executes the full parsing routine for the product page.

        Fetches the HTML content from the product URL, initializes a BeautifulSoup object,
        and runs parsing functions for each supported section (e.g., specs, drawings, parts).
        The extracted data is collected and returned as a structured dictionary.

        Args:
            url (str): The URL of the product page to parse.

        Returns:
            Dict[str, Any]: Parsed data for each available section, keyed by session name.
        """
        
        self.url    = url
        self.logger.info(f"{'_'*20} Started the Parser for item {self.url.split("/")[-1]} {'_'*20}")
        
        session = create_resilient_session()
        
        try:
            response = session.get(self.url, headers=DEFAULT_HEADERS, timeout=10)
        except Exception as e:
            self.logger.error(f"Unexpected error during request: {e}")
            return {}
        
        response.raise_for_status()
        html = response.text
        
        soup = BeautifulSoup(html, "html.parser")
        self.parse_catalog(soup)

        session_names = self.find_sessions(soup)

        for session_name in session_names:
            if session_name in self.parsers:
                self.data[session_name] = self.parsers[session_name](soup)
                
            else:
                self.logger.warning(f"No Parser implementation for {session_name.capitalize()}")
                
        return self.data    


    def parse_catalog(self,soup: BeautifulSoup) -> None:
        
        """
        Extracts general product information from the catalog header section of the page.

        Parses the product title, description, key-value pairs from the detail table,
        image source, and product information packet PDF link. Stores the extracted data
        into `self.data` under keys: 'product_id', 'description', 'info', 'img_src', and optionally 'pdf_src'.

        Args:
            soup (BeautifulSoup): BeautifulSoup object of the page.

        Returns:
            None
        """
        
        catalog_div = soup.find("div",id="catalog-detail")
        
        if catalog_div is None:
            self.logger.warning("No catalog-detail div found")
            return
        
        # Title Extraction
        title_tag = soup.find("div", class_="page-title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Description Extraction
        desc_tag = catalog_div.find("div", class_="product-description")
        description = desc_tag.get_text(strip=True) if desc_tag else None
        
        self.data["product_id"] = title
        self.data["description"] = normalize_spaces(description)
        self.data["info"] = {}
        
        # Detail Extraction
        detail_table_tag = catalog_div.find("table",class_="detail-table")
        if detail_table_tag:
            info_tags = detail_table_tag.find_all("tr")
                
            for info_tag in info_tags:
                key_cell = info_tag.find("th")
                value_cell = info_tag.find("td")

                if key_cell and value_cell:
                    key = key_cell.get_text(strip=True)
                    value = value_cell.get_text(separator=" ", strip=True)
                    self.data["info"][key.lower()] = value
        else:
            self.logger.warning("No detail-table table found")
            
        # Picture link extraction
        # id 451 means no picture
        img_tag = catalog_div.find("img", class_="product-image")
        img_src = img_tag.get("data-src") if img_tag else None
        self.data["img_src"] = img_src
        
        # Pdf link extraction
        pdf_tag = catalog_div.find("a", id="infoPacket")
        
        if pdf_tag:
            pdf_src = pdf_tag.get("href")
            self.data["pdf_src"] = pdf_src
            
        else:
            self.logger.warning("No Product Information Packet Found")
            
        self.logger.info("Successfully retrieved Catalog Info") 
    
    def parse_specs(self,soup: BeautifulSoup) -> Dict[str,str]:
        """
        Extracts key-value specs from the 'Specs' tab.

        Args:
            soup (BeautifulSoup): Parsed HTML page.

        Returns:
            Dict[str,str]: Dictionary containing spec labels and their corresponding values.
        """
        
        specs = {}
    
        specs_div = soup.find("div", class_="pane", attrs={"data-tab": "specs"})
        
        if specs_div is None:
            self.logger.warning("Specs div not found")
            return {}
        
        specs = self.parse_label_value_grid(specs_div)
        self.logger.info("Successfully retrieved Specs info")    
        
        return specs   
    
    def parse_nameplate(self,soup: BeautifulSoup) -> Dict[str,str]:
        """
        Extracts nameplate data from the 'Nameplate' tab, handling both key-value pairs and extra text entries.

        Args:
            soup (BeautifulSoup): Parsed HTML page.

        Returns:
            Dict[str,str]: Dictionary containing nameplate information, with unstructured lines grouped under 'EXTRAS'.
        """  
        nameplate = {}
        extras = []
        
        nameplate_div = soup.find("div", class_="pane", attrs={"data-tab": "nameplate"})
        
        if nameplate_div is None:
            self.logger.warning("Nameplate div not found")
            return {}
        
        rows = nameplate_div.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["th", "td"])
            key = None
            
            if len(cells) ==1:
                # Handle standalone text rows (e.g., section titles or notes)
                extras.append(cells[0].get_text(strip=True))
                continue
                
            for cell in cells:
                text = cell.get_text(strip=True)
                
                if cell.name == "th":
                    key=text
                elif cell.name =="td":
                    if key:
                        value = text
                        nameplate[key.lower()] = value
                        key=None
                    elif text:
                        extras.append(text)
        if extras:
            nameplate["EXTRAS"] = extras
            
        self.logger.info("Successfully retrieved nameplate info") 
        return nameplate
      
    def parse_label_value_grid(self,table: BeautifulSoup) -> Dict[str,str]:
        """
        Extracts key-value pairs from a label-value grid layout.

        Each label and its corresponding value are wrapped in <span> tags with classes 'label' and 'value'.
        These are grouped inside <div class="col"> containers.

        Args:
            table: BeautifulSoup tag representing the grid container.

        Returns:
            Dict[str, str]: Dictionary with lowercase label keys and their corresponding values.
        """
        
        if table is None:
            self.logger.warning("Expected a table element but got None")
            return {}
        
        data = {}
        columns = table.find_all("div", class_="col")
    
        for col in columns:
            # Each direct <div> child in the column may contain a label-value pair
            for item in col.find_all("div",recursive=False):
                label = item.find("span",class_="label")
                value = item.find("span",class_="value")
                
                if label and value:
                    key = label.get_text(strip=True)
                    val = value.get_text(separator=", ",strip=True)
                    data[key.lower()] = val
    
        return data
        
    def parse_performance(self,soup: BeautifulSoup) -> Dict[str,str]:
        """
        Extracts performance-related information from the 'Performance' tab of the product page.

        Parses optional description, observation, general characteristics (as label-value pairs),
        load characteristics (as table data), and performance curves (as file links).
        Falls back to generic links if no structured sections are found.

        Args:
            soup (BeautifulSoup): Parsed HTML of the page.

        Returns:
            Dict[str, Any]: Dictionary containing performance-related information.
        """
        
        performance = {}
        performance_div = soup.find("div", class_="pane", attrs={"data-tab": "performance"})
        
        if performance_div is None:
            self.logger.warning("Performance div not found")
            return {}
        
        # Sometimes present
        try:
            description = [
                h2.get_text(strip=True)
                for h2 in performance_div.find_all("h2")
                if not h2.find_parent("div", class_="tabHeading")][0]
            
            performance["description"] = description
        except:
            self.logger.warning("No description found in Performance")

        # Sometimes present
        try:
            observation = performance_div.find("em").get_text(strip=True)
            performance["observation"] = observation
        except:
            self.logger.warning("No observation found in Performance")
        
        
        # Collect sub-section titles
        h3_tags = [h3.get_text(strip=True).lower() for h3 in performance_div.find_all("h3")]
        
        parsers = {
            "general characteristics":self.parse_general_characteristics,
            "load characteristics":self.parse_load_characteristics,
            "performance curves":self.parse_performance_curves}
        
        for session in h3_tags:
            if session in parsers:
                key = session.lower().replace(" ", "_")
                performance[key] = parsers[session](performance_div)
            else:
                self.logger.warning(f"Session {session} not implemented in Performance Parser!")
         
        if not h3_tags:
            self.logger.info("No sessions found in Performance, fallback extraction will be used")
            links = [a["href"] for a in performance_div.find_all("a", href=True)]
            
            performance["associated_urls"] = links
            
        self.logger.info("Successfully retrieved performance info")
        
        return performance
    
    def parse_general_characteristics(self, soup: BeautifulSoup) -> Dict[str,str]:
        
        table = soup.find("div", class_="product-overview")                        
        return self.parse_label_value_grid(table) 
    
    def parse_load_characteristics(self, soup: BeautifulSoup) -> Dict[str,str]:
        
        table = soup.find("table", class_="data-table")
        data = {}
        
        headers = [
            th.get_text(strip=True)
            for th in table.find("thead").find_all("th")[:]
            ]

        header_tag = headers[0]
        headers = headers[1:]

        data["metric"] = header_tag

        for row in table.find("tbody").find_all("tr"):
            label_cell = row.find("th")
            label = label_cell.get_text(strip=True)
            values = [
                td.get_text(strip=True)
                for td in row.find_all("td")
            ]
            data[label] = dict(zip(headers, values))
        
        return data
     
    def parse_performance_curves(self, soup: BeautifulSoup) -> Dict[str,str]:
        
            performance_curves_element = soup.find("div",class_="section drawings")

            links = [a["href"] for a in performance_curves_element.find_all("a", href=True)]
            
            return links
       
    def parse_parts(self, soup: BeautifulSoup) -> List[Dict[str,str]]:
        """
        Extracts part information from the 'Parts' tab.

        Parses each table row into a dictionary with keys:
        'part_number', 'description', and 'quantity'.

        Args:
            soup (BeautifulSoup): Parsed HTML of the page.

        Returns:
            List[Dict[str,str]]: List of part records.
        """
        
        parts = []
        
        parts_div = soup.find("div", class_="pane", attrs={"data-tab": "parts"})
        
        if not parts_div:
            self.logger.warning("Parts div not found")
            return parts
        
        table_body = parts_div.find("tbody")
            
        if not table_body:
            self.logger.warning("No <tbody> found in parts table")
            return parts

        rows = table_body.find_all("tr")
        
        for row in rows:
            cols  = row.find_all("td")
            if len(cols)!=3:
                self.logger.warning("Malformed row in parse_parts")
                continue
            
            part = normalize_spaces(cols[0].get_text(strip=True))
            desc = normalize_spaces(cols[1].get_text(strip=True))
            qty  = normalize_spaces(cols[2].get_text(strip=True))
        
            parts.append({
            "part_number": part,
            "description": desc,
            "quantity": qty,
            })
        
        self.logger.info("Successfully retrieved parts info") 
        
        return parts
    
    def parse_accessories(self, soup: BeautifulSoup) -> List[Dict[str,str]]:
        
        """
        Extracts accessory information from the 'Accessories' tab.

        Parses each table row into a dictionary with keys:
        'part_number', 'description', and 'list price'.

        Args:
            soup (BeautifulSoup): Parsed HTML of the page.

        Returns:
            List[Dict[str,str]]: List of accessories.
        """
        
        
        accessories = []
        
        accessories_div = soup.find("div", class_="pane", attrs={"data-tab": "accessories"})
        
        if not accessories_div:
            self.logger.warning("Accessories div not found")
            return accessories
        
        table_body = accessories_div.find("tbody")
        if not table_body:
            self.logger.warning("No <tbody> found in accessories table")
            return accessories
        
        rows = table_body.find_all("tr")
        for row in rows:
            cols  = row.find_all("td")
            if len(cols)!=3:
                self.logger.warning("Malformed row in parse_accessories")
                continue
            
            part = normalize_spaces(cols[0].get_text(strip=True))
            desc = normalize_spaces(cols[1].get_text(strip=True))
            qty  = normalize_spaces(cols[2].get_text(strip=True))
        
            accessories.append({
            "part_number": part,
            "description": desc,
            "list price": qty,
            })
        
        self.logger.info("Successfully retrieved accessories info")
        return accessories

    def parse_drawings(self, soup: BeautifulSoup) -> Dict[str,str]:
            """
            Extracts CAD and image metadata from the 'Drawings' tab of the product page.

            Parses the ng-init JSON payload embedded in the Drawings tab to extract file details
            for both CAD downloads and drawing images.

            Returns:
                Dict[str,str]: Contains 'cads' and 'imgs' lists with structured metadata.
            """
            
            drawings_div  = soup.find("div", class_="pane", attrs={"data-tab": "drawings"})
            
            if drawings_div is None:
                self.logger.warning("Drawings div not found")
                return {}
            
            cad_div = drawings_div.find("div", class_="cadfiles")
            
            if cad_div is None:
                self.logger.warning("Could not find Cad Div in Drawings")
                return {}
            
            ng_init = cad_div.get("ng-init", "")
            json_blocks = re.findall(r"\[\s*{.*?}\s*\]", ng_init, flags=re.DOTALL)
            
            if not json_blocks:
                self.logger.warning("No JSON blocks found in ng-init")
                return {}

            cad_data, img_data = [], []

            for raw_json in json_blocks:
                try:
                    clean_json = raw_json.replace("\n", "").replace("\r", "")
                    items = json.loads(clean_json)
                    
                    for item in items:
                        if item.get("url"):
                            cad_data.append({
                            "name": item.get("name"),
                            "filetype": item.get("filetype"),
                            "value": item.get("value"),
                            "url": item.get("url"),
                            "cad": item.get("cad"),
                            "version": item.get("version"),
                        })
                        if item.get("number"):
                            img_data.append({
                                "description": item.get("description"),
                                "kind": item.get("kind"),
                                "material": item.get("material"),
                                "number": item.get("number"),
                                "revision": item.get("revision"),
                                "revisionLetter": item.get("revisionLetter"),
                                "type": item.get("type"),
                                "url": item.get("url"),
                            }) 
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to decode JSON in ng-init: {e}")
                    return []
                
            self.logger.info("Successfully retrieved drawings info") 
            
            """
            both img and cad info are gonna be usefull for the downloader in the future
            their info is needed for future api calls
            """
            return {"imgs":img_data,"cads":cad_data}

import logging

def main():
    
    links = [
        "https://www.baldor.com/catalog/027603",
        "https://www.baldor.com/catalog/1021W",
        "https://www.baldor.com/catalog/CD1803R",
        "https://www.baldor.com/catalog/BSM100C-1150AA",
        "https://www.baldor.com/catalog/CD3433",
        "https://www.baldor.com/catalog/024018",
        "https://www.baldor.com/catalog/027550"
        
    ]
    
    for url in links[:]:
        parser = Parser(url)
        data = parser.run()
        #print(data)


if __name__ == "__main__":
    main()

