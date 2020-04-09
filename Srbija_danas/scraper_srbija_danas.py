"""
Srbija Danas newspaper scraper.
"""
import glob
import logging
import os
import shutil
from builtins import staticmethod
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


class ScraperSrbijaDanas(Scraper):
    """
    Scraper class for Srbija Danas news.
    """

    def __init__(self):
        site_name = 'Srbija_danas'
        super().__init__(site_name)

    def _get_short_articles(self, lang):
        """
        Return list of articles (ListArticle objects) within defined range.
        :return:
        """
        super()._get_short_articles(self._site_id.split('-')[0])

        extended = self.extend_short_articles(newspaper="srbija-danas")
        for e in extended:
            self._articles.append(
                ShortArticle(e[1], e[0], "%s *****" % (e[0].split('/')[-1]), "None", self._site_name))

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        response = requests.get(self._generic_url.format(keyword, 1))
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            pages = soup.find_all("li", class_="pager-item")[-1].text.split(" ")[-1]
        except (TypeError, IndexError):
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword, page_num, **kwargs):
        url = self._generic_url.format(keyword, page_num)
        response = requests.get(url)
        article_divs = BeautifulSoup(response.content, 'html.parser').find_all('article', class_='o-media')
        articles = []
        for article_div in article_divs:
            article_url = "https://www.srbijadanas.com%s" % article_div.find('a', class_='o-media__link')['href']
            date = article_div.find('time', class_='o-media__date')['datetime']
            date = datetime.utcfromtimestamp(int(date))

            if date >= constants.MAX_DATE:
                continue
            if date < constants.MIN_DATE:
                return articles, True

            article_title = article_div.find('h2').text.strip()
            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article):
        url = short_article.url
        try:
            response = requests.get(url)
        except requests.exceptions.ConnectionError:
            logging.error("Invalid URL: %s" % url)
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            author = soup.find('span', {'class': 'article__author'})
            if author is None or "Foto" in author:
                author = ""
            else:
                author = author.text

            if '*****' in short_article.title:
                short_article.title = soup.find('meta', {'property': 'og:title'})['content'].strip()
                date = soup.find('time', {'class': 'article__post-time'}).text.split(" ")[0]
                date = datetime.strptime(date.strip(), '%d.%m.%Y.')
                short_article.time = date.strftime('%Y-%m-%d')

            text = self.get_formatted_article(text=soup.find('div', {'class': 'article__body'}),
                                              lead=soup.find('div', {'class': 'field-article-forspan'}))

            article_comments_url = soup.find('div', class_='article-comment--buttons__wrapper').find_all('a')[-1][
                'href']
            comments = []  # self._get_comments(article_comments_url)
            total_comments = int(soup.find('span', class_='article-comment__show-btn').text.split(' ')[0])
            if total_comments > 0:
                comments = self._get_comments(article_comments_url)
                if len(comments) != total_comments:
                    logging.warning("Different number of comments: %d/%d." % (len(comments), total_comments))

            full_article = Article(short_article, text, author, comments)
            return full_article
        except (AttributeError, TypeError):
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self, id):
        comment_counter = 0
        comments = []
        url = self._comments_url.format(id)
        response = requests.get(url)
        comment_divs = BeautifulSoup(response.content, 'html.parser').find_all('p', class_='article-content__body')
        for comment_div in comment_divs:
            comment_text = comment_div.text
            comment_counter += 1
            comments.append(Comment("%s" % comment_counter, '', comment_text))
        return comments

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """
        for tag in text.findAll('div', class_='article__tags-wrapper'):
            tag.decompose()
        for tag in text.findAll('h2', class_='pane-title'):
            tag.decompose()
        for tag in text.findAll('h2', class_='o-media__title'):
            tag.decompose()
        for tag in text.findAll('h2'):
            text = tag.text.lower()
            if "(video)" in text or "(foto)" in text:
                tag.decompose()
        for tag in text.findAll('div', class_='field-type-text'):
            tag.decompose()
        for tag in text.findAll('div', class_='o-media-container__body'):
            tag.decompose()
        for tag in text.findAll('div', class_='read-latest'):
            tag.decompose()
        for tag in text.findAll('div', class_='in-article-reference'):
            tag.decompose()
        for tag in text.findAll('div', class_='poll'):
            tag.decompose()
        for tag in text.findAll('div', {'class': 'social-media-embed'}):
            tag.decompose()
        for tag in text.findAll('li', {'class': 'read-also__item'}):
            tag.decompose()
        for tag in text.findAll('blockquote'):
            tag.decompose()
        for tag in text.findAll('div', class_='highlighted'):
            tag.decompose()

        bold_strong = text.findAll('b')
        bold_strong.extend(text.findAll('strong'))
        bold_strong.extend(text.findAll('a'))
        for tag in bold_strong:
            tag_text = tag.text.lower()
            if "(video)" in tag_text or '(foto)' in tag_text or 'bonus video' in tag_text or 'bonus galerija' in \
                    tag_text or 'pročitajte i' in tag_text:
                tag.decompose()

        cleared = super().format_text(text)
        return cleared

    @staticmethod
    def remove_thrash_articles():
        """
        Remove thrash articles.
        :return:
        """
        cnt = 0
        root_dir = r'Srbija_danas\data\thrash'
        thrash_articles = ['vip', 'snajke']
        for thrash_article in thrash_articles:
            folder_path = os.path.join(root_dir, 'articles_%s' % thrash_article)
            os.makedirs(folder_path, exist_ok=True)
            for path in glob.glob(os.path.join(r'Srbija_danas\data\articles', '*.xml')):
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                if 'https://www.srbijadanas.com/%s' % thrash_article in content or \
                        'https://www.srbijadanas.com/zabava/%s' % thrash_article in content:
                    thrash_article_path = os.path.join(folder_path, os.path.basename(path))
                    shutil.move(path, thrash_article_path)
                    cnt += 1
        logging.info("Total %d thrash articles removed." % cnt)


if __name__ == '__main__':
    ScraperSrbijaDanas.remove_thrash_articles()
