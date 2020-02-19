"""
Politika newspaper scraper.
"""

import json
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import constants
from model import ShortArticle, Article, Comment
from scraper import Scraper

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("../debug.log"),
                              logging.StreamHandler()])


class ScraperPolitika(Scraper):
    """
    Scraper class for Politika news.
    """

    def __init__(self):
        site_name = 'Politika'
        super().__init__(site_name)

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        response = requests.get(self._generic_url.format(keyword, 1))
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            pages = soup.find("div", class_="pagination").find("ul").find_all("li")[-1].text
        except AttributeError:
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword, page_num, **kwargs):
        url = self._generic_url.format(keyword, page_num)
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []

        date_divs = soup.find_all('div', class_="arial light-gray inline-block uppercase border-left px1 ml1")
        url_title_divs = soup.find_all('div', class_="clearfix h4 bold roboto-slab mt1")

        assert len(url_title_divs) == len(date_divs)

        for date_div, url_title_div in zip(date_divs, url_title_divs):
            # Get article date
            article_date = "{}, {}".format(date_div.find('span', class_='item-date').text,
                                           date_div.find('span', class_='item-time').text.split(' ')[-1])
            # Get article url
            article_url = "http://www.politika.rs{}".format(url_title_div.find("a")['href'])

            # Get article title
            article_title = url_title_div.text

            date = datetime.strptime(article_date, '%d.%m.%Y, %H:%M') if len(
                article_date.split(',')) > 1 else datetime.strptime(article_date, '%d.%m.%Y')
            if date >= constants.MAX_DATE:
                continue
            if date < constants.MIN_DATE:
                return articles, True

            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article):
        url = short_article.url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            text = soup.find('div', class_='article-content mt3 mb3').text

            author_tag = soup.find('meta', attrs={'name': 'author'})
            author = author_tag['content'] if 'content' in author_tag.attrs else ""

            foreign_id_tag = soup.find('form', class_='clearfix mxn1 comment-form')
            if foreign_id_tag is not None:
                foreign_id = soup.find('form', class_='clearfix mxn1 comment-form')['data-foreign-key']
                comments = self._get_comments(foreign_id)
            else:
                comments = []
                logging.warning("Foreign ID is None.")

            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self, foreign_id=None):
        comments = []
        comments_counter = 0
        comments_page_counter = 0
        while True:
            comments_page_counter += 1
            response = requests.get(self._comments_url.format(foreign_id, comments_page_counter))
            if response.status_code == 404:
                return comments
            json_comments_list = json.loads(response.content)['data']
            for json_comment in json_comments_list:
                comments_counter += 1
                sub_comments_counter = 0
                comment = json_comment['Comment']

                text = comment['text']
                comment_id = str(comments_counter)
                parent_id = comment['parent_id']
                comments.append(Comment(comment_id, parent_id, text))
                if 'SubComment' not in json_comment:
                    continue
                else:
                    json_sub_comments = json_comment['SubComment']

                for json_sub_comment in json_sub_comments:
                    sub_comments_counter += 1
                    sub_text = json_sub_comment['text']
                    sub_id = "%s-%d" % (comment_id, sub_comments_counter)
                    sub_parent_id = comment_id
                    comments.append(Comment(sub_id, sub_parent_id, sub_text))
