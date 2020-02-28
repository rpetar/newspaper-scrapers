import json
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


class ScraperDnevnik(Scraper):
    """
    Scraper class for Slovenske novice news
    """

    def __init__(self):
        site_name = 'Dnevnik'
        super().__init__(site_name)

    def _get_short_articles(self, lang):
        for keyword in constants.keywords:
            logging.info("Keyword: %s" % keyword)
            offset = 0
            url = self._generic_url.format(keyword, constants.MIN_DATE.strftime("%Y-%m-%dT%H:%M:%S"),
                                           constants.MAX_DATE.strftime("%Y-%m-%dT%H:%M:%S"), offset)

            while True:
                response = requests.get(url)
                json_response = json.loads(response.content.decode('utf-8'))
                articles_list = self._get_articles_list(keyword, json_response=json_response)
                self._articles.extend(articles_list)
                url = json_response['meta']['next']
                if url == "":
                    break
                else:
                    offset += 60
                    url = self._generic_url.format(keyword, constants.MIN_DATE.strftime("%Y-%m-%dT%H:%M:%S"),
                                                   constants.MAX_DATE.strftime("%Y-%m-%dT%H:%M:%S"), offset)
                logging.info("%d/%d" % (offset, json_response['meta']['total_count']))

    def _get_articles_list(self, keyword, **kwargs):
        json_response = kwargs['json_response']
        articles = []

        for article in json_response['objects']:
            article_title = article['title'] if article['title'] is not None else ""
            article_url = article['url']
            date = datetime.strptime(article['date_published'], '%Y-%m-%dT%H:%M:%SZ')

            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles

    def _get_full_article(self, short_article):
        url = short_article.url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            text = soup.find('div', class_='article-body article-wrap').find('article').text
            author = soup.find('div', class_='article-source').text
            comments = self._get_comments()
            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self):
        return []
