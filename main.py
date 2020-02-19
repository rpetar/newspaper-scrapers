"""
Main method.
"""
from Politika.scraper_politika import ScraperPolitika
from Svet24.scraper_svet24 import ScraperSvet24
from Večer.scraper_vecer import ScraperVecer
from ur24.scraper_24ur import ScraperUr24

if __name__ == "__main__":
    # scraper_politika = ScraperPolitika()
    # scraper_politika.scrape()

    # scraper_24ur = ScraperUr24()
    # scraper_24ur.scrape()
    #
    # scraper_svet24 = ScraperSvet24()
    # scraper_svet24.scrape()

    scraper_vecer = ScraperVecer()
    scraper_vecer.scrape()
