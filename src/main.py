from scraper import Parser, Downloader

from pprint import pprint

def main():
    
    links = [
        "https://www.baldor.com/catalog/1021W"
        ]

    parser = Parser()
    downloader = Downloader()
    
    raw_data = parser.run(links[0])
    downloader.run(raw_data)
    
    

if __name__ == "__main__":
    main()
