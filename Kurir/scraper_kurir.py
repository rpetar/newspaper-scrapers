"""
Kurir newspaper scraper.
"""

import logging
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

import constants
from model import ShortArticle, Article, Comment
from scraper import Scraper

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("../debug.log"),
                              logging.StreamHandler()])


class ScraperKurir(Scraper):
    """
    Scraper class for Kurir news.
    """

    def __init__(self):
        site_name = 'Kurir'
        super().__init__(site_name)

    def _get_short_articles(self, lang):
        """
        Return list of articles (ListArticle objects) within defined range.
        :return:
        """
        keywords = constants.keywords_serbian if lang == 'sr' else constants.keywords
        for keyword in keywords:
            logging.info("Keyword: %s" % keyword)
            number_of_pages = self._get_keyword_number_of_pages(keyword)
            logging.info("Number of pages: %s" % number_of_pages)
            for page_num in range(1, number_of_pages + 1):
                logging.info("%d" % page_num)
                articles_list, stop_iteration = self._get_articles_list(keyword, page_num)
                self._articles.extend(articles_list)
                # Stop iteration if article is older than min date
                if stop_iteration:
                    break
        extended = self.extend_short_articles(newspaper='kurir')
        for e in extended:
            self._articles.append(
                ShortArticle(e[1], e[0], "%s *****" % (e[0].split('/')[-1]), "None", self._site_name))

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        response = requests.get(self._generic_url.format(1, keyword))
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            pages = soup.find("a", class_="pag_last")['href'].split('/')[-1].split('?')[0]
        except TypeError:
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword, page_num, **kwargs):
        url = self._generic_url.format(page_num, keyword)
        response = requests.get(url)
        article_divs = BeautifulSoup(response.content, 'html.parser').find_all('div', class_='itemContent')
        articles = []
        for article_div in article_divs:
            article_url = "https://www.kurir.rs%s" % article_div.find('a', class_='itemLnk')['href']
            try:
                date_div = article_div.find('div', class_='time')
                # If article time is in format: "pre Xh Ym"
                if 'pre' in date_div.text:
                    hours, minutes = date_div.text.split(" ")[1:]
                    date = datetime.today() - timedelta(hours=int(hours[:-1]), minutes=int(minutes[:-1]))
                else:
                    date = datetime.strptime(date_div.text, '%d-%m-%Y')
            except ValueError:
                continue
            except AttributeError:
                continue

            if not constants.MIN_DATE <= date < constants.MAX_DATE:
                continue
            for spn in article_div.find_all('span'):
                spn.decompose()
            article_title = article_div.find('h2').text.strip()
            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article):
        url = short_article.url
        response = requests.get(url)

        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            author = soup.find('span', {'itemprop': 'author'}).find('span', {'itemprop': 'name'})
            if author is None or "Foto" in author:
                author = ""
            else:
                author = author.text

            if '*****' in short_article.title:
                short_article.title = soup.find('div', class_='shareWrap')['data-title'].strip()
                date = soup.find('span', {'itemprop': 'datePublished'})['content']
                date = datetime.strptime(date, '%Y-%m-%dT%H:%M')
                short_article.time = date.strftime('%Y-%m-%d')
            text = self.get_formatted_article(text=soup.find('div', {'itemprop': 'articleBody'}),
                                              lead=soup.find('div', class_='lead'))

            article_id = soup.find('div', class_='articleNav')['data-id']
            comments = self._get_comments(article_id)

            if len(comments) > 0:
                logging.info('Total comments: %d' % len(comments))
            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self, id):
        page = 1
        comment_counter = 0
        sub_comment_counter = 1
        comments = []
        while True:
            url = self._comments_url.format(id, page)
            response = requests.get(url)
            if not response.content:
                return comments
            comment_divs = BeautifulSoup(response.content, 'html.parser').find_all('div', class_='com_comment')
            for comment_div in comment_divs:
                comment_text = comment_div.find('div', class_='comTxt').text
                if 'comReply' in comment_div['class']:
                    comments.append(
                        Comment("%s-%s" % (comment_counter, sub_comment_counter), "%s" % comment_counter, comment_text))
                    sub_comment_counter += 1
                else:
                    sub_comment_counter = 1
                    comment_counter += 1
                    comments.append(Comment("%s" % comment_counter, '', comment_text))
            page += 1

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """
        for tag in text.findAll('div', class_='wdgRelated'):
            tag.decompose()
        for tag in text.findAll('div', class_='articleImageCaption  '):
            tag.decompose()
        for tag in text.findAll('div', class_='artSource'):
            tag.decompose()
        for tag in text.findAll('div', class_='embeddedContent'):
            tag.decompose()
        for tag in text.findAll('div', class_='galNfo'):
            tag.decompose()

        paragraphs = text.findAll('p')
        decompose = False
        for i, tag in enumerate(paragraphs):
            tag_text = tag.text.lower()
            next_p = paragraphs[i + 1].text if i + 1 < len(paragraphs) else ""
            if ("kurir.rs" in tag_text or "kurir" in tag_text) and \
                    ("foto" in tag_text or "foto" in next_p.lower()):
                decompose = True
            if decompose:
                tag.decompose()
            if "pogledajte bonus video" in tag_text:
                tag.decompose()
            if "foto:" in tag_text:
                tag.decompose()

        for tag in text.findAll('span', {'itemprop': 'author'}):
            tag.decompose()
        for tag in text.findAll('span', {'itemprop': 'publisher'}):
            tag.decompose()

        cleared = super().format_text(text)
        return cleared
