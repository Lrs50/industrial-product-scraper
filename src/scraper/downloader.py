from typing import List, Dict, Any
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path
from urllib.parse import quote
import sys
import os
from pathlib import Path
from pprint import pprint

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import *


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://www.baldor.com/",
}

def build_image_url(image_path: str) -> str:
    base = "https://www.baldor.com"
    params = "bc=white&as=1&w=1920&h=0"
    return f"{base}{image_path}?{params}"

def build_product_file_url(path: str) -> str:
    base = "https://www.baldor.com"
    return f"{base}{path}"

def build_drawing_img_url(product_code: str, drawing_number: str) -> str:
    return f"https://www.baldor.com/api/products/{product_code}/drawings/{drawing_number}"

def build_cad_url(value: str, original_url: str) -> str:
    encoded_url = quote(original_url, safe="")
    return f"https://www.baldor.com/api/products/download/?value={value}&url={encoded_url}"

class Downloader(object):
    def __init__(self,log_to_console: bool = True, log_to_file: bool = False):
        
        self.logger = get_logger("Parser", to_console=log_to_console, to_file=log_to_file)
        attach_urllib3_to_logger(self.logger)
        self.session = create_resilient_session()
        
        
    def run(self,json: Dict[str, Any]):
        
        self.logger.info(f"{'_'*20} Started the Downloader for item {json['product_id']} {'_'*20}")
        
        self.json = json
        
        self.path = f"output/assets/{self.json['product_id']}"
        
        self.fetch_and_save_drawings()
    
    def download_file(self,url: str, destination: str) -> None:
        
        try:
            response = self.session.get(url,headers=DEFAULT_HEADERS,stream=True, timeout=10)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"[UNEXPECTED ERROR] during request: {e}")
            return {"results": {"matches": []}}
        
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
    def fetch_and_save_image(self):
        
        img_src = self.json.get("img_src")
        
        if img_src:
            img_url = build_image_url(img_src)
        else:
            self.logger.warning("No Main Image Source Found!")
        
        self.download_file(img_url,f"{self.path}/img.jpg")
    
    def fetch_and_save_pdf(self):
        
        pdf_src = self.json.get("pdf_src")
        
        if pdf_src:
            pdf_url = build_product_file_url(pdf_src)
        else:
            self.logger.warning("No Product File Source Found!")
        
        self.download_file(pdf_url,f"{self.path}/manual.pdf")
      
    def fetch_and_save_performance(self):
        
        performance_dict = self.json.get("performance")
        
        if not performance_dict:
            self.logger.warning("No information about Performance!")
        
        performance_curves_src = performance_dict.get("performance_curves",[])
        associated_urls = performance_dict.get("associated_urls",[])

        associated_urls.extend(performance_curves_src)
        
        if not associated_urls:
            self.logger.warning("No Associated urls in Performance")
            return
            
        for i,url in enumerate(associated_urls):
            self.download_file(url,f"{self.path}/performance_{i}.pdf")
            
    
    def fetch_and_save_drawings(self):
        
        drawings_dict = self.json.get("drawings")
        
        if not drawings_dict:
            self.logger.warning("No information about Drawings!")
        
        img_list = drawings_dict.get("imgs",[])
        cad_list = drawings_dict.get("cads",[])
        
        if not img_list:
            self.logger.warning("No Images in Drawings!")
        
        if not cad_list:
            self.logger.warning("No Cads in Drawings!")
            
        
        for i,img_dict in enumerate(img_list):
            url = build_drawing_img_url(self.json['product_id'],img_dict["number"])
            self.download_file(url,f"{self.path}/drawing_img_{i}.pdf")
            
        for i,cad_dict in enumerate(cad_list):
            url = build_cad_url(cad_dict["value"],cad_dict["url"])
            
            file_type = cad_dict["value"].split(".")[-1]
            name = f"cad_{cad_dict['filetype']}_{i}.{file_type}"
            
            self.download_file(url,f"{self.path}/{name}")