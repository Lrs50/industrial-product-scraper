from scraper import *

from pprint import pprint



def main():
    
    crawler = Crawler()
    
    urls,metadata = crawler.run()
    for url,mdata in list(zip(urls,metadata))[:5]:
        parser = Parser()
        downloader = Downloader()
        
        raw_data = parser.run(url)
        assets = downloader.run(raw_data)
        
        raw_data["assets"] = assets
        
        clean_json = standardize_product_json(raw_data,mdata) 
        
        print(clean_json)
    
if __name__ == "__main__":
    main()
