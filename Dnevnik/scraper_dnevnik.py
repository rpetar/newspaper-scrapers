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

        if "article-lock" in response.content.decode('utf-8'):
            logging.error("Pay-wall: %s" % url)
            return None

        try:
            article_text = soup.find('div', class_='article-body article-wrap')
            if article_text.find('article') is not None:
                article_text = article_text.find('article')
            text = self.get_formatted_article(
                text=article_text,
                lead=soup.find('p', class_='lead'))
            author = soup.find('div', class_='article-source')
            if author is None:
                author = ""
            else:
                author = author.text

            comments = self._get_comments()
            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self):
        return []

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """

        for tag in text.findAll('div', class_='gallery-slider'):
            tag.decompose()
        for tag in text.findAll('p', class_='image-caption'):
            tag.decompose()
        for tag in text.findAll('blockquote', class_='twitter-tweet'):
            tag.decompose()
        for tag in text.findAll('img'):
            if tag.next.text is not None and 'Foto' in tag.next.text:
                tag.next.decompose()
            if tag.next.next.text is not None and 'Foto' in tag.next.next.text:
                tag.next.next.decompose()
            if tag.next.next.next.text is not None and 'Foto' in tag.next.next.next.text:
                tag.next.next.next.decompose()
            tag.decompose()

        cleared = super().format_text(text)
        return cleared
