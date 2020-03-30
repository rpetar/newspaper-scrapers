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

    def get_formatted_article(self, text, lead=None):
        """
        Format article text and lead.
        :param text: BeautifulSoup article tag
        :param lead: BeautifulSoup lead tag
        :return:
        """
        text = self.format_text(text)
        if lead is not None:
            lead = self.format_text(lead)
            if lead == "":
                return text
            if lead[-1] != ".":
                text = "%s. %s" % (lead, text)
            else:
                text = "%s %s" % (lead, text)
        return text

    @staticmethod
    def format_text(text):
        """
        Format XML text.
        :param text:
        :return:
        """
        for skip_tag in constants.skip_tags:
            for tag in text.findAll(skip_tag):
                tag.decompose()
        for br in text.findAll('br'):
            br.replace_with("\n")
        for tag in text.findAll('p'):
            tag.string = "\n%s" % tag.text
        cleared = text.text
        cleared = re.sub(r'\n{2,}', r'\n', cleared)
        cleared = cleared.strip()
        return cleared

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

    def extend_short_articles(self, path=r'C:\Users\rape9001\Downloads\naslovi.json', newspaper=""):
        """
        Load more URL-s from separate JSON file.
        :param path: path of the JSON file
        :param newspaper: name of the newspaper
        :return:
        """
        with open(path, 'r') as file:
            f = json.load(file)
        newspapers = [(np['url'], np['keyword']) for np in f if np['source'] == newspaper]
        return newspapers

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
            # if counter < 6186:
            #     continue
            logging.info("%d. Get article: %s" % (counter, a.url))
            article = self._get_full_article(a)
            if article is not None:
                os.makedirs(os.path.dirname(folder), exist_ok=True)
                article.save_to_file(os.path.join(folder, article.document_name))
        shutil.make_archive(self._site_name, 'zip', folder)
        shutil.move("%s.zip" % self._site_name, folder)

    def _get_facebook_comments_API(self, **kwargs):
        comments = []
        target_id = self._get_facebook_id(kwargs['facebook_id'], kwargs['domain'], kwargs['url'])
        top_comments_url = constants.FACEBOOK_COMMENTS_URL_API.format(target_id)
        while True:
            top_comments_response = requests.get(top_comments_url).content.decode('utf-8')
            top_comments_counter = 0
            top_comments_json = json.loads(top_comments_response)
            for top_comment in top_comments_json['data']:
                top_comments_counter += 1
                comments.append(self._get_facebook_comment(top_comment, top_comments_counter))

                sub_comments_counter = 0
                top_comment_id = top_comment['id']
                sub_comments_url = constants.FACEBOOK_COMMENTS_URL_API.format(top_comment_id)
                sub_comments_response = requests.get(sub_comments_url).content.decode('utf-8')
                for sub_comment in json.loads(sub_comments_response)['data']:
                    sub_comments_counter += 1
                    comments.append(self._get_facebook_comment(sub_comment, comment_id="%d-%d" % (
                        top_comments_counter, sub_comments_counter), parent_comment_id=str(top_comments_counter)))

            try:
                top_comments_url = top_comments_json['paging']['next']
            except KeyError:
                return comments

    def _get_facebook_comment(self, comment_json, comment_id, parent_comment_id=''):
        """
        Returns Comment object from comment json object Facebook returns.
        :param comment_json: Facebook's json
        :param comment_id: id of the comment
        :param parent_comment_id: id of the parent
        :return:
        """
        comment_text = comment_json['message']
        return Comment(comment_id=str(comment_id), parent_comment_id=parent_comment_id, text=comment_text)

    def _get_facebook_id(self, facebook_id, domain, url):
        """
        Returns target ID which is used for Facebook comments.
        :param facebook_id: Facebook ID
        :param domain: site domain
        :return:
        """
        top_comments_response = requests.get(
            constants.FACEBOOK_COMMENTS_URL.format(facebook_id, domain, url)).content.decode(
            'utf-8')
        # Get IDs of first-level comments
        full_json = json.loads(re.search(r'handleServerJS\(({\"instances\".*)\);\}', top_comments_response).group(1))
        target_fb_id = full_json['require'][2][3][0]['props']['meta']['targetFBID']
        return target_fb_id

    def _get_facebook_comments(self, **kwargs):
        comments = []
        fb_comments_response = requests.get(
            self._comments_url.format(kwargs['facebook_id'], kwargs['domain'], kwargs['url'])).content.decode('utf-8')
        fb_comments_json = json.loads(
            re.search(r'handleServerJS\(({\"instances\".*)\);\}', fb_comments_response).group(1))
        target_fb_id = fb_comments_json['require'][2][3][0]['props']['meta']['targetFBID']

        fb_pager_url = "https://www.facebook.com/plugins/comments/async/{}/pager/time".format(target_fb_id)
        top_comments_response = requests.post(fb_pager_url, data={'__a': 1, 'limit': 5000}).content.decode('utf-8')
        top_comments_json = json.loads(re.search('({.*})', top_comments_response).group())

        top_comments_list = top_comments_json['payload']['commentIDs']
        top_comments_counter = 0
        for top_comment_id in top_comments_list:
            top_comments_counter += 1
            comments.append(Comment(comment_id=str(top_comments_counter),
                                    parent_comment_id=',',
                                    text=top_comments_json['payload']['idMap'][top_comment_id]['body']['text']))

            sub_comments_url = 'https://www.facebook.com/plugins/comments/async/comment/{}/pager'.format(
                top_comment_id)
            sub_comments_response = requests.post(sub_comments_url, data={'__a': '1'}).content.decode('utf-8')
            sub_comments_json = json.loads(re.search('({.*})', sub_comments_response).group())

            sub_comments_counter = 0
            for sub_comment_id in sub_comments_json['payload']['commentIDs']:
                sub_comments_counter += 1
                sub_comment_text = sub_comments_json['payload']['idMap'][sub_comment_id]['body']['text']
                comments.append(Comment(comment_id="%d-%d" % (top_comments_counter, sub_comments_counter),
                                        parent_comment_id=str(top_comments_counter),
                                        text=sub_comment_text))
        return comments

    @abc.abstractmethod
    def _get_keyword_number_of_pages(self, keyword, **kwargs):
        """
        Returns a total number of pages for the given keyword.
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
