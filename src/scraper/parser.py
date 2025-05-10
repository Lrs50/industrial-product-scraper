from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import re
import json

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

def normalize_spaces(text: str) -> str:
    return ' '.join(text.split())

class Parser(object):
    
    def __init__(self, url: str,log_to_console: bool = True, log_to_file: bool = False):
        
        self.logger = get_logger("Parser", to_console=log_to_console, to_file=log_to_file)
        self.url = url
        self.data = {}
        
        self.parsers = {
            "specs": self.parse_specs,
            "nameplate": self.parse_nameplate,
            "performance": self.parse_performance,
            "parts": self.parse_parts,
            "accessories": self.parse_accessories,
            "drawings": self.parse_drawings
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
                self.data["info"][key.lower()] = value
        
        self.data["product_id"] = title
        self.data["description"] = description
        
        # id 451 means no picture
        img_tag = catalog_div.find("img", class_="product-image")
        img_src = img_tag.get("data-src")
        
        self.data["img_src"] = img_src
        
        pdf_tag = catalog_div.find("a", id="infoPacket")
        
        if pdf_tag is None:
            self.logger.warning("No Product Information Packet Found")
        else:
            pdf_src = pdf_tag.get("href")
            self.data["pdf_src"] = pdf_src
            
        self.logger.info("Successfully retrieved catalog info") 
    
    def parse_specs(self,soup):
        """Extracts key-value specs from the 'Specs' tab."""
        
        specs = {}
    
        specs_div = soup.find("div", class_="pane", attrs={"data-tab": "specs"})
        
        if not specs_div:
            self.logger.warning("Specs div not found")
        
        specs = self.parse_label_value_grid(specs_div)
        
        self.logger.info("Successfully retrieved Specs info")    
        
        return specs   
    
    def parse_nameplate(self,soup):
        
        nameplate = {}
        extras = []
        
        nameplate_div = soup.find("div", class_="pane", attrs={"data-tab": "nameplate"})
        
        rows = nameplate_div.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["th", "td"])
            key = None
            
            if len(cells) ==1:
                cell_text = cells[0].get_text(strip=True)
                extras.append(cell_text)
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
      
    def parse_label_value_grid(self,table):
        data = {}
        columns = table.find_all("div", class_="col")
    
        for col in columns:
            for item in col.find_all("div",recursive=False):
                label = item.find("span",class_="label")
                value = item.find("span",class_="value")
                
                if label and value:
                    key = label.get_text(strip=True)
                    val = value.get_text(separator=", ",strip=True)
                    data[key.lower()] = val
    
        return data
        
    def parse_performance(self,soup):
        
        performance = {}
        
        performance_div = soup.find("div", class_="pane", attrs={"data-tab": "performance"})
        
        try:
            description = [
                h2.get_text(strip=True)
                for h2 in performance_div.find_all("h2")
                if not h2.find_parent("div", class_="tabHeading")][0]
            
            performance["description"] = description
        except:
            self.logger.warning("No description found in Performance")

        try:
            observation = performance_div.find("em").get_text(strip=True)
            performance["observation"] = observation
        except:
            self.logger.warning("No observation found in Performance")
        
        h3_tags = [h3.get_text(strip=True).lower() for h3 in performance_div.find_all("h3")]
        
        if "general characteristics" in h3_tags:

            table = performance_div.find("div", class_="product-overview")                        
            performance["general_characteristics"] = self.parse_label_value_grid(table) 
            
        if "load characteristics" in h3_tags:
            data = {}
            table = performance_div.find("table", class_="data-table")

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

            performance["load_characteristics"] = data
            
        if "performance curves" in h3_tags:
            performance_curves_element = performance_div.find("div",class_="section drawings")

            links = [a["href"] for a in performance_curves_element.find_all("a", href=True)]
            
            data["performance_curves"] = links
            
        if not h3_tags:
            self.logger.info("No sessions found in Performance, fallback extraction will be used")
            links = [a["href"] for a in performance_div.find_all("a", href=True)]
            
            performance["associated_urls"] = links
            
        self.logger.info("Successfully retrieved performance info")
        
        return performance
    
    def parse_parts(self,soup):
        
        parts = []
        
        parts_div = soup.find("div", class_="pane", attrs={"data-tab": "parts"})
        
        rows = parts_div.find("tbody").find_all("tr")
        
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
    
    def parse_accessories(self,soup):
        
        accessories = []
        
        accessories_div = soup.find("div", class_="pane", attrs={"data-tab": "accessories"})
        
        rows = accessories_div.find("tbody").find_all("tr")
        
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

    def parse_drawings(self,soup):
        
        drawings = []
        
        drawings_div  = soup.find("div", class_="pane", attrs={"data-tab": "drawings"})
        
        if not drawings_div:
            self.logger.warning("Drawings div not found")
            return drawings
        
        cad_div = drawings_div.find("div", class_="cadfiles")
        
        if cad_div is None:
            self.logger.warning("Could not find Cad Div in Drawings")
            return drawings
        
        ng_init = cad_div.get("ng-init", "")
        matches = re.findall(r"\[\s*{.*?}\s*\]", ng_init, flags=re.DOTALL)
        
        if not matches:
            self.logger.warning("Could not find Matches in Drawings")
            return drawings

        for i,match in enumerate(matches):
            matches[i] = match.replace("\n", "").replace("\r", "")
            try:
                matches[i] = json.loads(matches[i])
            except json.JSONDecodeError as e:
                self.logger.error("Error parsing JSON in Drawings:", e)
                return []
        
        
        cad_json = matches[0]
        
        cad_data = [
            {
                "name": item.get("name",None),
                "filetype": item.get("filetype",None),
                "value": item.get("value",None),
                "url": item.get("url",None),
                "cad":item.get("cad",None),
                "version":item.get("version",None),
            }
            for item in cad_json
            if item.get("url",None)
        ]

        img_json = matches[1]
        img_data = [
            {
                "description":item.get("description",None),
                "kind":item.get("kind",None),
                "material":item.get("material",None),
                "number":item.get("number",None),
                "revision":item.get("revision",None),
                "revisionLetter":item.get("revisionLetter",None),
                "type":item.get("type",None),
                "url":item.get("url",None),
            }
            for item in img_json
            if item.get("number",None)
        ]
        
        
        self.logger.info("Successfully retrieved drawings info") 
        
        """
        both img and cad info are gonna be usefull for the downloader in the future
        their info is needed for future api calls
        """
        return {"imgs":img_data,"cads":cad_data}

def main():
    
    links = [
        #"https://www.baldor.com/catalog/027603",
        #"https://www.baldor.com/catalog/1021W",
        "https://www.baldor.com/catalog/CD1803R",
        #"https://www.baldor.com/catalog/BSM100C-1150AA",
        #"https://www.baldor.com/catalog/CD3433",
        #"https://www.baldor.com/catalog/024018",
        #"https://www.baldor.com/catalog/027550"
        
    ]
    
    for url in links[:]:
        parser = Parser(url)
        data = parser.run()
        #pprint(data)

if __name__ == "__main__":
    main()

