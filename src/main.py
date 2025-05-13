from scraper import *
from tqdm import tqdm
import json
import random

def save_dict_as_json(data: dict, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    
    log_to_console = False
    log_to_file = True
    
    crawler = Crawler(log_to_console=log_to_console,log_to_file=log_to_file)
    
    urls,metadata = crawler.run()
    
    products = list(zip(urls, metadata))
    sampled_products = random.sample(products, k=15)
    
    for url, mdata in tqdm(
        sampled_products,
        desc="🛠️ Scraping Products",
        unit="page",
        dynamic_ncols=True,
        colour="green",
        bar_format="{l_bar}{bar}{r_bar}"
    ):
        parser = Parser(log_to_console=log_to_console,log_to_file=log_to_file)
        downloader = Downloader(log_to_console=log_to_console,log_to_file=log_to_file)
        
        raw_data = parser.run(url)
        assets = downloader.run(raw_data)
        
        raw_data["assets"] = assets
        
        clean_json = standardize_product_json(raw_data,mdata) 
        save_dict_as_json(clean_json,f"output/{downloader.sanitize_filename(clean_json['product_id'])}.json")
    
if __name__ == "__main__":
    main()
