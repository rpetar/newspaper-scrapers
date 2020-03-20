import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import constants
from model import ShortArticle, Article
from scraper import Scraper

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("../debug.log"),
                              logging.StreamHandler()])


class ScraperSvet24(Scraper):
    """
    Scraper class for Svet24 news
    """

    def __init__(self):
        site_name = 'Svet24'
        super().__init__(site_name)

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        response = requests.get(self._generic_url.format(keyword, 1))
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            pages = soup.find("div", class_="flex items-center justify-center").find_all("a")[-2].text
        except AttributeError:
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword: str, page_num: int, **kwargs):
        url = self._generic_url.format(keyword, page_num)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []

        date_divs = soup.find_all('div', class_="sub-article-info")
        url_title_divs = soup.find_all('a', class_="sub-article group img-lin-grad")

        assert len(url_title_divs) == len(date_divs)

        for date_div, url_title_div in zip(date_divs, url_title_divs):
            # Get article date
            article_date = date_div.text.strip().split('\n')[-1].strip()
            # Get article url
            article_url = "https://novice.svet24.si{}".format(url_title_div['href'])
            # Get article title
            article_title = url_title_div.find('h4').text.strip()

            date = datetime.strptime(article_date, '%d. %b %Y, %H:%M')
            if date >= constants.MAX_DATE or date < constants.MIN_DATE:
                continue

            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article: ShortArticle):
        url = short_article.url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        try:
            text = self.get_formatted_article(
                text=soup.find('div', class_='article-text article-video-scroll clearfix'),
                lead=soup.find('p', {'itemprop': 'description'}))
            author = soup.find('span', class_='inline-flex items-center')
            if author is None:
                author = ""
            else:
                author = author.text.strip()

            facebook_id = soup.find('meta', {'property': 'fb:app_id'})['content']
            domain = self._generic_url.split('https://')[1].split('/')[0]

            comments = self._get_facebook_comments(url=url, facebook_id=facebook_id, domain=domain)

            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            logging.error("Invalid URL: %s" % url)
        return None

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """
        for tag in text.findAll('div', class_='article-img-desc'):
            tag.decompose()
        for tag in text.findAll('div', class_='author'):
            tag.decompose()
        cleared = super().format_text(text)
        return cleared
