from typing import List, Dict, Any
from pathlib import Path
from urllib.parse import quote
import re

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

def unwrap(l:List[Any]) -> Any :
    
    return l[0] if len(l) == 1 else l

class Downloader(object):
    def __init__(self,log_to_console: bool = True, log_to_file: bool = False):
        """
        Initializes the Downloader instance with logging and a resilient HTTP session.

        Args:
            log_to_console (bool): If True, logs will be printed to the console.
            log_to_file (bool): If True, logs will be saved to a log file.
        """
        
        self.logger = get_logger("Downloader", to_console=log_to_console, to_file=log_to_file)
        attach_urllib3_to_logger(self.logger)
        self.session = create_resilient_session()
        
        
    def run(self, json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the download of all relevant assets for a given product.

        Args:
            json (Dict[str, Any]): Dictionary with all parsed product metadata.

        Returns:
            Dict[str, Any]: A dictionary with asset types as keys and their relative file paths as values.
        """
        self.logger.info(f"{'_'*20} Started the Downloader for item {json['product_id']} {'_'*20}")
        
        self.json = json
        
        self.path = f"output/assets/{self.sanitize_filename(self.json['product_id'])}"
        self.relative_path = f"assets/{self.sanitize_filename(self.json['product_id'])}"
        
        assets = {}
        
        assets["image"] = unwrap(self.download_main_image())
        assets["manual"] = unwrap(self.download_product_manual())
        assets["performance"] = unwrap(self.download_performance())
        assets.update(self.download_drawings())
        
        return assets
    
    def sanitize_filename(self,filename: str) -> str:
        """
        Replaces characters invalid in file names (especially on Windows)
        with underscores. Logs if the filename was changed.
        """
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        if sanitized != filename:
            self.logger.warning(f"Sanitized filename: '{filename}' → '{sanitized}'")
        return sanitized
    
    def download_file(self,url: str, destination: str) -> None:
        """
        Downloads a file from the given URL and saves it to the specified destination path.

        Args:
            url (str): The full URL of the file to download.
            destination (str): The file path where the downloaded file will be saved.

        Returns:
            None
        """ 
        
        try:
            
            if destination.endswith(".pdf"):
                timeout = 60
            else:
                timeout = 10
            
            response = self.session.get(url,headers=DEFAULT_HEADERS,stream=True, timeout=timeout)
            response.raise_for_status()
        except Exception as e:
            self.logger.error(f"[UNEXPECTED ERROR] during request: {e}")
            return None
        
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        self.logger.info(f"Successfully Downloaded {destination.split('/')[-1]}")        
        return None
        
    def download_main_image(self) -> List[str]:
        """
        Downloads the main product image based on the 'img_src' field in the JSON.

        Returns:
            List[str]: A list containing the relative path to the saved image file,
                    or an empty list if no image was found.
        """
        img_src = self.json.get("img_src")
        
        if img_src:
            img_url = build_image_url(img_src)
        else:
            self.logger.warning("No Main Image Source Found!")
            return []
        
        self.download_file(img_url,f"{self.path}/img.jpg")
    
        return [f"{self.relative_path}/img.jpg"]

    def download_product_manual(self) -> List[str]:
        """
        Downloads the product manual PDF from the 'pdf_src' field in the JSON.

        Returns:
            List[str]: A list containing the relative path to the saved manual file,
                    or an empty list if not available.
        """
        pdf_src = self.json.get("pdf_src")
        
        if pdf_src:
            pdf_url = build_product_file_url(pdf_src)
        else:
            self.logger.warning("No Product File Source Found!")
            return []
        
        self.download_file(pdf_url,f"{self.path}/manual.pdf")

        return [f"{self.relative_path}/manual.pdf"]
      
    def download_performance(self) -> List[str]:
        """
        Downloads performance-related PDF files listed in the JSON under the 'performance' key.

        Returns:
            List[str]: A list of relative paths to the saved performance files.
        """
        performance_dict = self.json.get("performance")
        
        if not performance_dict:
            self.logger.warning("No information about Performance!")
            return []
        
        performance_curves_src = performance_dict.get("performance_curves",[])
        associated_urls = performance_dict.get("associated_urls",[])

        associated_urls.extend(performance_curves_src)
        
        if not associated_urls:
            self.logger.warning("No Associated urls in Performance")
            return []
            
        
        paths = []    
        
        for i,url in enumerate(associated_urls):
            self.download_file(url,f"{self.path}/performance_curve_{i}.pdf")
            paths.append(f"{self.relative_path}/performance_curve_{i}.pdf")

        return paths
        
    def download_drawings(self) -> Dict[str, Any]:
        """
        Downloads drawing-related files from the product JSON, including render images and CAD files.

        If no drawing information is found, logs appropriate warnings and returns empty structures.

        Returns:
            Dict[str, Any]: A dictionary with keys:
                - 'renders': List of relative paths to render files (or single string if only one)
                - 'cads': List of relative paths to CAD files (or single string if only one)
        """
        drawings_dict = self.json.get("drawings")
        
        if not drawings_dict:
            self.logger.warning("No information about Drawings!")
        
        img_list = drawings_dict.get("imgs",[])
        cad_list = drawings_dict.get("cads",[])
        
        if not img_list:
            self.logger.warning("No Images in Drawings!")
        
        if not cad_list:
            self.logger.warning("No Cads in Drawings!")
            
        paths = {"renders":[],"cads":[]}  
        
        for i,img_dict in enumerate(img_list):
            url = build_drawing_img_url(self.json['product_id'],img_dict["number"])
            self.download_file(url,f"{self.path}/render_{i}.pdf")
            paths["renders"].append(f"{self.relative_path}/render_{i}.pdf")
            
        for i,cad_dict in enumerate(cad_list):
            url = build_cad_url(cad_dict["value"],cad_dict["url"])
            
            file_type = cad_dict["value"].split(".")[-1]
            
            name = "_".join(cad_dict["name"].split(" "))
            name = f"{name}.{file_type}"
            name = self.sanitize_filename(name)
            
            self.download_file(url,f"{self.path}/{name}")
            paths["cads"].append(f"{self.relative_path}/{name}")
            
        paths["renders"] = unwrap(paths["renders"])    
        paths["cads"] = unwrap(paths["cads"])   
        
        return paths