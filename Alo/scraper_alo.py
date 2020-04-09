"""
Alo newspaper scraper.
"""
import glob
import logging
import os
import shutil
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


class ScraperAlo(Scraper):
    """
    Scraper class for Alo news.
    """

    def __init__(self):
        site_name = 'Alo'
        super().__init__(site_name)

    def _get_short_articles(self, lang):
        """
        Return list of articles (ListArticle objects) within defined range.
        :return:
        """
        keywords = constants.keywords_serbian if lang == 'sr' else constants.keywords
        for keyword in keywords:
            logging.info("Keyword: %s" % keyword)
            page_num = 1
            while True:
                logging.info("%d" % page_num)
                articles_list, stop_iteration = self._get_articles_list(keyword, page_num)
                self._articles.extend(articles_list)
                # Stop iteration if article is older than min date
                if stop_iteration:
                    break
                page_num += 1
        extended = self.extend_short_articles(newspaper="alo")
        logging.info("Total articles scraped: %d" % len(self._articles))
        logging.info("Number of additional articles: %d" % len(extended))
        for e in extended:
            self._articles.append(
                ShortArticle(e[1], e[0], "%s *****" % (e[0].split('/')[-1]), "None", self._site_name))

    def _get_articles_list(self, keyword, page_num, **kwargs):
        url = self._generic_url.format(keyword, page_num)
        response = requests.get(url)

        if "Nema rezultata za ovu pretragu" in response.content.decode('utf-8'):
            return [], True
        article_divs = BeautifulSoup(response.content, 'html.parser').find_all('div', class_='categoryList__details')
        articles = []
        for article_div in article_divs:
            article_date, article_url = article_div.find('ul').findAll('li')
            days = int(article_date.text.split(" ")[-1][:-1])
            date = datetime.today() - timedelta(days=days)

            article_url = "http://www.alo.rs{}".format(article_url.find('a')['href'])

            # Get article title
            article_title = article_div.find('h2').find('span').text.strip()

            if not constants.MIN_DATE <= date < constants.MAX_DATE:
                continue

            articles.append(
                ShortArticle(keyword=keyword, url=article_url.strip(), title=article_title.strip(),
                             time=date.strftime('%Y-%m-%d'), site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article):
        url = short_article.url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        try:
            text = self.get_formatted_article(text=soup.find('div', {'id': 'newsContent'}),
                                              lead=soup.find('p', class_='lead'))
            author_tag = soup.find('span', attrs={'class': 'article-author'})
            author = author_tag.text if True else ""

            comments = []
            # TODO: scrape title and date if not exists
            total_comments = int(soup.find('div', {'class': 'all-comments-link'}).text.split(" ")[-1][1:-1])
            if total_comments > 0:
                tag = soup.find('li', {'id': 'main-comment'})
                # Add first comment and it sub-comments from page
                c, last_comment_id = self._get_comment_and_sub_comments(tag)
                comments.extend(c)
                article_id = soup.find('input', {'type': 'hidden', 'id': 'articleId'})['value']
                # Add all other comments
                comments.extend(self._get_comments(article_id=article_id, last_comment_id=last_comment_id))
            # Check if number on comments on page and scraped number of comments is equal
            if total_comments != len(comments) and len(comments) > 0:
                logging.warning("Scraped wrong number of comments: %d/%d" % (len(comments), total_comments))

            full_article = Article(short_article, text, author, comments)
            return full_article
        except AttributeError:
            with open(r'log/alo_errors.txt', 'a') as f:
                f.write("%s\n" % url)
            logging.error("Invalid URL: %s" % url)
        return None

    def _get_comments(self, **kwargs):
        """
        Scrape all comments, except first one.
        :param kwargs:
            - last_comment_id: id of the first comment
            - article_id: id of the article
        :return:
        """
        comment_counter = 1
        last_comment_id = kwargs['last_comment_id']
        comments = []
        while True:
            url = self._comments_url.format(kwargs['article_id'], last_comment_id)
            response = requests.get(url)
            if not response.content:
                return comments
            comment_divs = BeautifulSoup(response.content, 'html.parser').find_all('li', {'id': 'main-comment'})
            for comment_tag in comment_divs:
                comment_counter += 1
                # Scrape comment and it sub-comments
                c, last_comment_id = self._get_comment_and_sub_comments(comment_tag, comment_counter)
                comments.extend(c)

    def _get_comment_and_sub_comments(self, tag, comment_counter=0):
        """
        Scrape comment within tag, and it sub-comments.
        :param tag: div that contains comment
        :param comment_counter: id of the last comment
        :return: list of comments, id of the last comment
        """
        comment_id, comment_text, sub_comments = self._get_comment(tag)
        # Add top-level comment
        comments = [Comment("%s" % comment_counter, '', comment_text)]
        sub_comment_counter = 1
        # Add sub-comments, if any
        if sub_comments:
            sub_comment_tags = tag.find_all('li', {'id': 'reply-comment'})
            for sub_comment_tag in sub_comment_tags:
                _, sub_comment_text, _ = self._get_comment(sub_comment_tag)
                comments.append(
                    Comment("%s-%s" % (comment_counter, sub_comment_counter), "%s" % comment_counter,
                            sub_comment_text))
                sub_comment_counter += 1

        return comments, comment_id

    def _get_comment(self, tag):
        """
        Get single comment from comment div.
        :param tag: div that contains comment
        :return: on-page id of the comment, comment text, True if comment contains sub-comments
        """
        comment_id = tag['data-comment-id']
        comment_text = tag.find_all('div', class_='twelvecol')[1].text
        sub_comments = tag.find('li', {'id': 'reply-comment'}) is not None
        return comment_id, comment_text, sub_comments

    def format_text(self, text):
        """
        Format XML text.
        :param text:
        :return:
        """

        for tag in text.findAll('span', class_='image-plugin-description'):
            tag.decompose()
        for tag in text.findAll('div', class_='mceEditable'):
            tag.decompose()
        for tag in text.findAll('section', class_='asideList'):
            tag.decompose()
        for tag in text.findAll('blockquote'):
            tag.decompose()
        for tag in text.findAll('p'):
            tag_text = tag.text.lower()
            if 'bonus video' in tag_text:
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
        root_dir = r'Alo\data\thrash'
        thrash_articles = ['vip', 'zabava']
        for thrash_article in thrash_articles:
            folder_path = os.path.join(root_dir, 'articles_%s' % thrash_article)
            os.makedirs(folder_path, exist_ok=True)
            for path in glob.glob(os.path.join(r'Alo\data\articles', '*.xml')):
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                if 'https://www.alo.rs/%s' % thrash_article in content or \
                        'http://www.alo.rs/%s' % thrash_article in content:
                    thrash_article_path = os.path.join(folder_path, os.path.basename(path))
                    shutil.move(path, thrash_article_path)
                    cnt += 1
        logging.info("Total %d thrash articles removed." % cnt)


if __name__ == '__main__':
    ScraperAlo.remove_thrash_articles()
