import re
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.sax.saxutils import unescape

from transliterate import translit

from constants import site_ids


class Comment:
    """
    Class representing single article comment.
    """

    def __init__(self, comment_id, parent_comment_id, text):
        """
        Comment class.
        :param comment_id: id of the comment
        :param parent_comment_id: id of the parent comment
        :param text: text of the comment
        """
        self.id = comment_id
        self.parent_id = parent_comment_id
        self.text = self._format_comment(text)
        self.text_transliterated = translit(self.text, 'sr', reversed=True)

    def _format_comment(self, text):
        """
        Remove new lines from comment.
        :param text:
        :return:
        """
        text = text.replace('\r', '')
        text = re.sub("\n*", "", text)

        html_escape_table = {
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&gt;": ">",
            "&lt;": "<",
        }
        for k, v in html_escape_table.items():
            text = text.replace(k, v)
        return text.strip()


class ShortArticle:
    """
    Class representing article from list obtained by searching news.
    """

    def __init__(self, keyword, url, title, time, site_name, article_id=None):
        """
        Constructor.
        :param url: url of the article
        :param title: title of the article
        :param time: publishing time of the article
        """
        self._keyword = keyword
        self._url = url
        self._title = title
        self._time = time
        self._title_transliterated = translit(self._title, 'sr', reversed=True)
        self._site_name = site_name
        self._site_id = site_ids[site_name]
        self._article_id = article_id

    @property
    def keyword(self):
        return self._keyword

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, title):
        self._title = title
        self._title_transliterated = translit(self._title, 'sr', reversed=True)

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        self._time = time

    @property
    def tittle_transliterated(self):
        return self._title_transliterated

    @property
    def site_name(self):
        return self._site_name

    @property
    def site_id(self):
        return self._site_id

    @property
    def id(self):
        return self._article_id

    @id.setter
    def id(self, article_id):
        self._article_id = article_id

    def __gt__(self, other):
        return self._title_transliterated > other.tittle_transliterated

    def __hash__(self):
        return hash(self._url)

    def __eq__(self, other):
        return self._url == other.url


class Article(ShortArticle):
    """
    Class representing single article. Extends ListArticle
    """

    def __init__(self, short_article: ShortArticle, text, author, comments):
        super().__init__(short_article.keyword, short_article.url, short_article.title, short_article.time,
                         short_article.site_name, short_article.id)
        # si-01-123.xml
        self.document_name = "%s.xml" % short_article._article_id
        # Website ID: si-01
        self.source_id = short_article.site_id
        # Website name
        self.source_name = short_article.site_name
        # Article ID: 123
        self.local_id = short_article.id.split("%s-" % short_article.site_id)[-1]
        # Transliterated article title
        self.title_transliterated = short_article.tittle_transliterated
        # Article text
        self.text = text
        # Article author
        self.author = translit(author.strip(), 'sr', reversed=True)
        # Article text transliterated
        self.text_transliterated = translit(self.text, 'sr', reversed=True)
        # Article comments
        self.comments = comments

    def convert_to_xml(self):
        """
        Convert article to XML.
        :return:
        """
        document = Element('document', attrib={'global-id': self.document_name.split(".")[0]})
        # Url
        url = SubElement(document, 'url')
        url.text = self._url
        # Source ID
        source_id = SubElement(document, 'source-id')
        source_id.text = self.source_id
        # Local ID
        local_id = SubElement(document, 'local-id')
        local_id.text = self.local_id
        # Source name
        source_name = SubElement(document, 'source-name')
        source_name.text = self.source_name

        # Article
        article = SubElement(document, 'article')
        # Article title
        article_title = SubElement(article, 'article-title')
        article_title.text = self._title
        # Article title transliterated
        article_title_transliterated = SubElement(article, 'article-title-transliterated')
        article_title_transliterated.text = self.title_transliterated
        # Article time
        article_time = SubElement(article, 'article-time')
        article_time.text = self._time
        # Article author
        article_author = SubElement(article, 'article-author')
        article_author.text = self.author
        # Article text
        article_text = SubElement(article, 'article-text')
        article_text.text = self.text
        # Article text transliterated
        article_text_transliterated = SubElement(article, 'article-text-transliterated')
        article_text_transliterated.text = self.text_transliterated

        # Comments
        comments = SubElement(document, 'comments')
        # Comments count
        comments_count = SubElement(comments, 'comments-count')
        comments_count.text = str(len(self.comments))
        # Comments list
        comments_list = SubElement(comments, 'comment-list')
        for c in self.comments:
            # Comment
            comment = SubElement(comments_list, 'comment', attrib={'comment-id': c.id})
            # Comment parent ID
            comment_parent_id = SubElement(comment, 'comment-parent-id')
            comment_parent_id.text = c.parent_id
            # Comment text
            comment_text = SubElement(comment, 'comment-text')
            comment_text.text = c.text
            # Comment text transliterated
            comment_text_transliterated = SubElement(comment, 'comment-text-transliterated')
            comment_text_transliterated.text = c.text_transliterated

        xml_string = tostring(document, encoding='utf-8', method='xml')
        return unescape(xml_string.decode('utf-8'))

    def save_to_file(self, file_name):
        """
        Save Article to XML file.
        :return:
        """
        xml = self.convert_to_xml()
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(xml)


if __name__ == '__main__':
    la = ShortArticle('keyword', 'url1234', 'title', 'time', 'name')
    la1 = ShortArticle('keyword', 'url1234', 'title', 'time', 'name')
    la2 = ShortArticle('keyword', 'url12345', 'title', 'time', 'name')

    print(la == la1)
    print(la == la2)

    las = [la, la1, la2]
    print(set(las))
