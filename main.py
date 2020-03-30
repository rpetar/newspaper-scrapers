"""
Main method.
"""
from Delo.scraper_delo import ScraperDelo
from Dnevnik.scraper_dnevnik import ScraperDnevnik
from Kurir.scraper_kurir import ScraperKurir
from Politika.scraper_politika import ScraperPolitika
from Slovenske_novice.scraper_novice import ScraperNovice
from Svet24.scraper_svet24 import ScraperSvet24
from Večer.scraper_vecer import ScraperVecer
from ur24.scraper_24ur import ScraperUr24

if __name__ == "__main__":
    # scraper_politika = ScraperPolitika()
    # scraper_politika.scrape()

    # scraper_svet24 = ScraperSvet24()
    # scraper_svet24.scrape()

    # scraper_vecer = ScraperVecer()
    # scraper_vecer.scrape()

    # scraper_novice = ScraperNovice()
    # scraper_novice.scrape()

    # scraper_delo = ScraperDelo()
    # scraper_delo.scrape()

    # scraper_24ur = ScraperUr24()
    # scraper_24ur.scrape()

    # scraper_dnevnik = ScraperDnevnik()
    # scraper_dnevnik.scrape()

    scraper_kurir = ScraperKurir()
    scraper_kurir.scrape()