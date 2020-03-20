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
            text = self.get_formatted_article(text=soup.find('div', class_='article-content mt3 mb3'),
                                              lead=soup.find('div', class_='h4 mt0 mb2 regular roboto-slab'))
            author_tag = soup.find('meta', attrs={'name': 'author'})
            author = author_tag['content'] if 'content' in author_tag.attrs else ""

            foreign_id_tag = soup.find('form', class_='clearfix mxn1 comment-form')
            if foreign_id_tag is not None:
                foreign_id = soup.find('form', class_='clearfix mxn1 comment-form')['data-foreign-key']
                comments = self._get_comments(foreign_id)
            else:
                comments = []
                logging.warning("Foreign ID is None.")
            total_comments = int(soup.find('a', class_='px1 light-blue').text)
            if total_comments != len(comments) and len(comments) > 0:
                logging.warning("Scraped wrong number of comments")
            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            with open(r'log/politika_errors.txt', 'a') as f:
                f.write("%s\n" % url)
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
            json_top_comments_list = json.loads(response.content)['data']
            for json_top_comment in json_top_comments_list:
                comments_counter += 1
                sub_comments_counter = 0
                top_comment = json_top_comment['Comment']
                top_comment_original_id = top_comment['id']

                top_text = top_comment['text']
                top_comment_id = str(comments_counter)
                parent_id = top_comment['parent_id']
                comments.append(Comment(top_comment_id, parent_id, top_text))
                if 'SubComment' not in json_top_comment:
                    continue
                else:
                    json_sub_comments = json_top_comment['SubComment']
                sub_comment_ids = []
                for json_sub_comment in json_sub_comments:
                    sub_comment_ids.append(json_sub_comment['id'])
                    sub_comments_counter += 1
                    sub_text = json_sub_comment['text']
                    sub_id = "%s-%d" % (top_comment_id, sub_comments_counter)
                    sub_parent_id = top_comment_id
                    comments.append(Comment(sub_id, sub_parent_id, sub_text))
                comments.extend(
                    self._get_sub_comments(foreign_id, top_comment_original_id, sub_comment_ids, top_comment_id))

    def _get_sub_comments(self, foreign_id, parent_id, sub_comment_ids, parent_local_id):
        comments = []
        if len(sub_comment_ids) == 0:
            return comments
        page = 1
        while True:
            sub_comments_url = 'http://www.politika.rs/api/v1/getComments/{}?page={}&parent_id={}&ids={}'.format(
                foreign_id, page, parent_id, ",".join(sub_comment_ids))
            sub_comments_response = requests.get(sub_comments_url).content.decode('utf-8-sig')
            try:
                sub_comments_json = json.loads(sub_comments_response)
            except json.JSONDecodeError:
                break
            if 'data' not in sub_comments_response or len(sub_comments_json['data']) == 0:
                break
            sub_comments_counter = len(sub_comment_ids) + 1
            for sub_comment in sub_comments_json['data']:
                sub_text = sub_comment['Comment']['text']
                sub_id = "%s-%d" % (parent_local_id, sub_comments_counter)
                comments.append(Comment(sub_id, parent_local_id, sub_text))
                sub_comments_counter += 1

            page += 1

        return comments

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """
        for tag in text.findAll('div', class_='caption-title'):
            tag.decompose()
        for tag in text.findAll('div', class_='article-content mt3 mb3'):
            tag.decompose()

        for tag in text.findAll():
            if tag.name == 'img':
                if tag.next.next.name == 'i':
                    tag.next.next.decompose()
                    tag.next.decompose()
                    tag.decompose()

                if tag.next.next.next.name == 'i':
                    tag.next.next.next.decompose()
                    tag.next.next.decompose()

                if tag.next.next.next.name == 'em':
                    tag.next.next.next.decompose()
                    tag.next.next.decompose()

                if tag.next.next.next.next.name == 'i':
                    tag.next.next.next.next.decompose()
                    tag.next.next.next.decompose()
        cleared = super().format_text(text)

        # for skip_tag in constants.skip_tags:
        #     for tag in text.findAll(skip_tag):
        #         tag.decompose()
        # cleared = text.text
        # cleared = cleared.replace('&quot;', '"')
        # cleared = cleared.replace('&amp;', '&')
        # cleared = cleared.strip()  # .replace("\n", " ")
        return cleared
