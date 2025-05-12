from scraper import Parser, Downloader

from pprint import pprint

def main():
    
    links = [
        "https://www.baldor.com/catalog/027603",
        "https://www.baldor.com/catalog/1021W",
        # "https://www.baldor.com/catalog/CD1803R",
        # "https://www.baldor.com/catalog/BSM100C-1150AA",
        # "https://www.baldor.com/catalog/CD3433",
        # "https://www.baldor.com/catalog/024018",
        # "https://www.baldor.com/catalog/027550"
        
    ]

    for link in links:
        parser = Parser()
        downloader = Downloader()
        
        raw_data = parser.run(link)
        assets = downloader.run(raw_data)
        
        pprint(assets)
    
if __name__ == "__main__":
    main()
