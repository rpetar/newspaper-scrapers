"""
Politika newspaper scraper.
"""

import abc
import json
import logging
import os
import pickle
import re
import shutil

import requests

import constants
from model import ShortArticle, Comment

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("../debug.log"),
                              logging.StreamHandler()])


class Scraper:
    """
    Scraper class.
    """

    def __init__(self, site_name):
        self._site_name = site_name
        self._site_id = constants.site_ids[site_name]
        self._generic_url = constants.site_urls[site_name]
        self._comments_url = constants.site_comments[site_name]
        self._articles = []

    def scrape(self):
        """
        Scrape articles as follows:
        1. Scrape URLs, and basic info for articles that match search criteria
        2. Remove all duplicates
        3. Sort articles alphabetically on title
        4. Create ID for each article
        4. For each article scrape all information and save it to file
        :return:
        """
        folder = '%s/data/' % self._site_name
        file_name = 'news_list'
        file_path = os.path.join(folder, file_name)
        # If first run, save list of articles to file, otherwise load articles from file
        if not os.path.isfile(file_path):
            self._get_short_articles(self._site_id.split('-')[0])
            self._remove_duplicates()
            self._sort()
            self._build_ids()

            os.makedirs(os.path.dirname(folder), exist_ok=True)
            with open(file_path, 'wb') as f:
                pickle.dump(self._articles, f)
                logging.info("%d articles successfully saved to file %s." % (len(self._articles), file_name))
        else:
            with open(file_path, 'rb') as f:
                self._articles = pickle.load(f)
                logging.info("%d articles successfully loaded from file %s." % (len(self._articles), file_name))

        self._get_full_articles()

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

    def _remove_duplicates(self):
        """
        Remove duplicate articles from the list.
        :return:
        """
        filtered = set(self._articles)
        logging.info(
            'Removed %d duplicates from %d articles.' % (len(self._articles) - len(filtered), len(self._articles)))
        self._articles = list(set(filtered))

    def _sort(self):
        """
        Sort list of articles alphabetically.
        :return:
        """
        self._articles = sorted(self._articles)
        logging.info("Articles successfully sorted alphabetically by title.")

    def _build_ids(self):
        """
        Create ID for each article in the list.
        :return:
        """
        for article in self._articles:
            article.id = "{}-{}".format(self._site_id, self._articles.index(article) + 1)
        logging.info("IDs successfully built.")

    def _get_full_articles(self):
        """
        Iterate through a list of articles, scrape all information for each article and save it to file.
        :return:
        """
        counter = 0
        folder = '%s/data/articles/' % self._site_name
        for a in self._articles:
            counter += 1
            logging.info("%d. Get article: %s" % (counter, a.url))
            article = self._get_full_article(a)
            if article is not None:
                os.makedirs(os.path.dirname(folder), exist_ok=True)
                file_name = '%s.xml' % article.local_id
                article.save_to_file(os.path.join(folder, file_name))
        shutil.make_archive(self._site_name, 'zip', folder)
        shutil.move("%s.zip" % self._site_name, folder)

    def _get_facebook_comments(self, **kwargs):
        comments = []

        top_comments_response = requests.get(
            self._comments_url.format(kwargs['facebook_id'], kwargs['domain'], kwargs['url'])).content.decode(
            'utf-8')
        # Get IDs of first-level comments
        full_json = json.loads(re.search(r'handleServerJS\(({\"instances\".*)\);\}', top_comments_response).group(1))
        top_comments_json = full_json['require'][2][3][0]['props']['comments']
        top_comments_counter = 1
        for top_comment_id in top_comments_json['commentIDs']:
            top_comment_text = top_comments_json['idMap'][top_comment_id]['body']['text']
            # Add top-level Comment
            comments.append(Comment(comment_id=str(top_comments_counter), parent_comment_id='', text=top_comment_text))

            # Request sub-comments
            sub_comment_pager_url = 'https://www.facebook.com/plugins/comments/async/comment/{}/pager/'.format(
                top_comment_id)
            response_sub_comment_pager = requests.post(sub_comment_pager_url, data={'__a': '1'}).content.decode('utf-8')
            sub_comment_json = json.loads(re.search('({.*})', response_sub_comment_pager).group())

            sub_comments_counter = 1
            for sub_comment_id in sub_comment_json['payload']['commentIDs']:
                sub_comment_text = sub_comment_json['payload']['idMap'][sub_comment_id]['body']['text']
                comments.append(
                    Comment("%d-%d" % (top_comments_counter, sub_comments_counter), str(top_comments_counter),
                            sub_comment_text))
                sub_comments_counter += 1
            top_comments_counter += 1

        return comments

    @abc.abstractmethod
    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        """
        Returns a total number of pages for the given keyword.
        :param keyword: keyword
        :return: number of pages
        """
        raise NotImplemented("Please Implement this method.")

    @abc.abstractmethod
    def _get_articles_list(self, keyword: str, page_num: int, **kwargs):
        """
        Scrape list of articles from the given URL.
        :param keyword: keyword
        :param url: url
        :return: list of articles & whether should stop iterating (article date is smaller that min)
        """
        raise NotImplemented("Please Implement this method.")

    @abc.abstractmethod
    def _get_full_article(self, short_article: ShortArticle):
        """
        Scrape all information for the article.
        :param short_article: ShortArticle with basic article information
        :return: Article class
        """
        raise NotImplemented("Please Implement this method.")

    @abc.abstractmethod
    def _get_comments(self, **kwargs):
        """
        Load article comments.
        :return: list of Comment objects
        """
        raise NotImplemented("Please Implement this method.")
