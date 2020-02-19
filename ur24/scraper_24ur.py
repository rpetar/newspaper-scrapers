"""
24ur newspaper scraper.
"""
import json
import logging
from datetime import datetime
from math import ceil

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait

import constants
from model import ShortArticle, Article, Comment
from scraper import Scraper

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("../debug.log"),
                              logging.StreamHandler()])
driver = webdriver.Chrome(executable_path=constants.DRIVER_PATH)


class ScraperUr24(Scraper):
    """
    Scraper class for 24ur news.
    """

    def __init__(self):
        site_name = 'ur24'
        super().__init__(site_name)

    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        driver.get(self._generic_url.format(keyword, 1))
        try:
            # Total number of pages is located in span that contains text: Konec
            WebDriverWait(driver, 3).until(
                lambda x: x.find_element_by_xpath("//*[contains(text(), 'Konec')]"))
            pages = \
                driver.find_element_by_class_name('pagination').find_elements_by_class_name('pagination__item')[
                    -1].get_attribute('href').split("stran=")[-1]
        except TimeoutException:
            pages = 1
        return int(pages)

    def _get_articles_list(self, keyword: str, page_num: int, **kwargs):
        url = self._generic_url.format(keyword, page_num)
        driver.get(url)
        articles = []

        try:
            WebDriverWait(driver, 3).until(
                lambda x: x.find_elements_by_class_name("card__details"))
            dates = driver.find_elements_by_class_name("card__details")
        except TimeoutException:
            dates = []

        for str_date in dates:
            # Get article url
            article_url = str_date.find_element_by_xpath('../../../..').get_attribute('href')
            # Get article title
            title = str_date.find_element_by_xpath('..').find_element_by_class_name('card__title-inside').text
            # Get article date
            date = datetime.strptime(str_date.text, '%d.%m.%Y, %H:%M') if len(
                str_date.text.split(',')) > 1 else datetime.strptime(str_date.text, '%d.%m.%Y')

            if date >= constants.MAX_DATE:
                continue
            if date < constants.MIN_DATE:
                return articles, True

            articles.append(ShortArticle(keyword=keyword, url=article_url, title=title, time=date.strftime('%Y-%m-%d'),
                                         site_name=self._site_name))
        return articles, False

    def _get_full_article(self, short_article: ShortArticle):
        url = short_article.url
        driver.get(url)

        try:
            WebDriverWait(driver, 3).until(
                lambda x: x.find_element_by_class_name('article__body'))
            text = driver.find_element_by_class_name('article__body').text
            author = driver.find_element_by_class_name('article__details-main').text
            article_id = driver.find_element_by_xpath('//meta[@name="onl:articleId"]').get_attribute('content')
            comments = self._get_comments(article_id)
            full_article = Article(short_article, text, author, comments)
            return full_article
        except TimeoutException:
            logging.error('%s' % url)

    def _get_comments(self, article_id=None):
        headers = {"content-type": "application/graphql"}
        raw_body = "{comments( itemType: ARTICLE itemId: %s page: %d perPage: %d )  {total totalShown comments {" \
                   "id body replies {id body}}}}"
        page = 1
        per_page = 100
        comments = []
        while True:
            response = requests.post(self._comments_url, data=raw_body % (article_id, page, per_page),
                                     headers=headers)
            if response.status_code != 200:
                logging.error("Error loading comments page %d." %
                              page)
                return comments
            response = json.loads(response.content.decode('utf-8'))
            total_comments = int(response['data']['comments']['total'])

            # If there is no comment return
            if total_comments == 0:
                return comments
            # If first iteration comment_id = 1, otherwise last comment id increased by 1
            comment_id = 1 if len(comments) == 0 else int(comments[-1].id.split('-')[0]) + 1
            # Get comments
            comments.extend(self._load_comments(comments=response['data']['comments']['comments'],
                                                comment_id=str(comment_id)))
            # If last page, return
            if page == ceil(total_comments / per_page):
                return comments
            page += 1

    def _load_comments(self, comments, comments_list=None, comment_id="1", parent_comment_id=''):
        """
        Load all comments recursively.
        :param comments: list of comments on same level that need to be processed
        :param comments_list: output list of Comment objects
        :param comment_id: current comment id (integer that represents number of current comment)
        :param parent_comment_id: id of comment parent (x-y-z)
        :return:
        """
        if comments_list is None:
            comments_list = []
        if len(comments) > 0:
            # Get first comment
            comment = comments.pop(0)
            # Build comment ID
            c_id = "%s-%s" % (parent_comment_id, comment_id) if parent_comment_id else comment_id
            # Comment parent ID
            c_parent_id = parent_comment_id

            comments_list.append(Comment(c_id, c_parent_id, comment['body']))

            if 'replies' in comment and len(comment['replies']) > 0:
                c_parent_id = 0 if not c_parent_id else c_parent_id
                # If comment contains replies, process all replies
                # parent_comment_id is current comment id, comment_id is 1
                self._load_comments(comments=comment['replies'], comments_list=comments_list,
                                    parent_comment_id=c_id)

            # If comment doesn't contain replies, process the rest of the list
            # Parent is the same, comment_id is increased by one
            return self._load_comments(comments=comments, comments_list=comments_list,
                                       comment_id=str(int(comment_id) + 1), parent_comment_id=c_parent_id)
        else:
            return comments_list
