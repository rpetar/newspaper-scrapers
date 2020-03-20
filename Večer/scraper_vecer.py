"""
Večer newspaper scraper.
"""

import logging
import time
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


class ScraperVecer(Scraper):
    """
    Scraper class for Večer news.
    """

    def __init__(self):
        site_name = 'Večer'
        super().__init__(site_name)

    def _get_short_articles(self, lang):
        """
        Return list of articles (ListArticle objects) within defined range.
        :return:
        """
        for keyword in constants.keywords:
            logging.info("Keyword: %s" % keyword)
            for year in range(constants.MIN_DATE.year, constants.MAX_DATE.year):
                logging.info("Year: %s" % year)
                number_of_pages = self._get_keyword_number_of_pages(keyword, year=year)
                logging.info("Number of pages: %s" % number_of_pages)
                for page_num in range(1, number_of_pages + 1):
                    logging.info("%d" % page_num)
                    articles_list, stop_iteration = self._get_articles_list(keyword, page_num, year=year)
                    self._articles.extend(articles_list)
                    # Stop iteration if article is older than min date
                    if stop_iteration:
                        break

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        response = requests.get(self._generic_url.format(keyword, kwargs['year'], 1))
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            pages = soup.find("a", class_="Pagination-link last")['data-page']
        except TypeError:
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword, page_num, **kwargs):
        url = self._generic_url.format(keyword, kwargs['year'], page_num)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []

        article_titles_divs = soup.find_all('div', class_="card_title has_ellipsis")
        article_date_divs = soup.find_all('div', class_="card_date")

        assert len(article_titles_divs) == len(article_date_divs)
        for title_div, date_div in zip(article_titles_divs, article_date_divs):
            article_title = title_div.text
            article_url = "https://www.vecer.com%s" % date_div.parent.parent.find_all('a')[0]['href']

            date = datetime.strptime(date_div.text, '%d.%m.%Y, %H.%M')

            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article):
        url = short_article.url
        response = requests.get(url)

        while response.status_code == 429:
            time.sleep(5)
            print('Retry')
            response = requests.get(url)

        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            text = self.get_formatted_article(text=soup.find('div', class_='itemFullText'),
                                              lead=soup.find('h2', class_='itemSubTitle'))
            author = soup.find('div', class_='col-authorname')
            if author is None:
                author = ""
            else:
                author = author.text
            facebook_id = soup.find('meta', {'property': 'fb:app_id'})['content']
            domain = self._generic_url.split('https://')[1].split('/')[0]

            comments = self._get_facebook_comments(url=url, facebook_id=facebook_id, domain=domain)
            if len(comments) > 0:
                logging.info('Total comments: %d' % len(comments))
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
        gray_boxes = text.findAll('p', class_='GrayBox')
        for gb in gray_boxes:
            for br in gb.findAll('br'):
                br.replace_with("\n")

        for tag in text.findAll('span'):
            if 'Potrebujete Javascript' in tag.text:
                tag.decompose()

        for tag in text.findAll('div', class_='ArticleImage-description'):
            tag.decompose()
        cleared = super().format_text(text)
        return cleared
