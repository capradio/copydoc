# -*- coding: utf-8 -*-
import re

from bs4 import BeautifulSoup, element
from copy import copy

try:
    # Python 2
    from urlparse import parse_qs, urlsplit
except ImportError:
    # Python 3
    from urllib.parse import parse_qs, urlsplit

try:
    # Python 2
    unicode
except NameError:
    # Python 3
    unicode = str

ATTR_WHITELIST = {
    'a': ['href'],
    'img': ['src', 'alt'],
}


class CopyDoc:
    """
    Clean up Google Doc html.

    To use, create a doc parser instance:

    .. code:: python

        parser = CopyDoc('<html><body><h1>My fake doc</h1></body></html>')

    Access rendered, parsed document:

    .. code:: python

        print(str(parser))

    Access parsed, Beautifulsoup object:

    ..code:: python

        soup = parser.soup
    """
    def __init__(self, html_string, tokens=[],multiline_tokens=[]):
        """
        Constructor takes an HTML string and sets up object.
        """
        self.soup = BeautifulSoup(html_string, 'html.parser')
        self.tags_blacklist = []
        self.tokens = tokens
        self.multiline_tokens = multiline_tokens
        self.text = ''
        self.text_tags = []
        self.text_list = []
        self.parse()

    def parse(self):
        """
        Run all parsing functions.
        """

        for tag in self.soup.findAll('span'):
            self.create_italic(tag)
            self.create_strong(tag)
            # self.create_underline(tag)
            self.unwrap_span(tag)

        for tag in self.soup.findAll('a'):
            self.remove_comments(tag)
            self.check_next(tag)

        for tag in self.soup.body.findAll():
            self.remove_empty(tag)
            self.remove_inline_comment(tag)
            self.parse_attrs(tag)
            for token, target in self.tokens:
                self.find_token(tag, token, target)

            self.remove_blacklisted_tags(tag)

        for tag in self.soup.findAll('p'):
            for token, attr, end in self.multiline_tokens:
                self.find_multiline_token(tag,token,attr,end)

    def remove_comments(self, tag):
        """
        Remove comments.
        """
        if tag.get('id', '').startswith('cmnt'):
            tag.parent.extract()

    def check_next(self, tag):
        """
        If next tag is link with same href, combine them.
        """
        if (type(tag.next_sibling) == element.Tag and
                tag.next_sibling.name == 'a'):

            next_tag = tag.next_sibling
            if tag.get('href') and next_tag.get('href'):
                href = self._parse_href(tag.get('href'))
                next_href = self._parse_href(next_tag.get('href'))

                if href == next_href:
                    next_text = next_tag.get_text()
                    tag.append(next_text)
                    self.tags_blacklist.append(next_tag)

    def remove_blacklisted_tags(self, tag):
        if tag in self.tags_blacklist:
            tag.decompose()

    def create_italic(self, tag):
        """
        See if span tag has italic style and wrap with em tag.
        """
        style = tag.get('style')
        if style and 'font-style:italic' in style:
            tag.wrap(self.soup.new_tag('em'))

    def create_strong(self, tag):
        """
        See if span tag has bold style and wrap with strong tag.
        """
        style = tag.get('style')
        if (style and
                ('font-weight:bold' in style or 'font-weight:700' in style)):
            tag.wrap(self.soup.new_tag('strong'))

    def create_underline(self, tag):
        """
        See if span tag has underline style and wrap with u tag.
        """
        style = tag.get('style')
        if style and 'text-decoration:underline' in style:
            tag.wrap(self.soup.new_tag('u'))

    def unwrap_span(self, tag):
        """
        Remove span tags while preserving contents.
        """
        tag.unwrap()

    def parse_attrs(self, tag):
        """
        Reject attributes not defined in ATTR_WHITELIST.
        """
        if tag.name in ATTR_WHITELIST.keys():
            attrs = copy(tag.attrs)
            for attr, value in attrs.items():
                if attr in ATTR_WHITELIST[tag.name]:
                    tag.attrs[attr] = self._parse_attr(tag.name, attr, value)
                else:
                    del tag.attrs[attr]
        else:
            tag.attrs = {}

    def remove_empty(self, tag):
        """
        Remove non-self-closing tags with no children *and* no content.
        """
        
        has_children = len(tag.contents)
        has_text = len(list(tag.stripped_strings))

        if not has_children and not has_text and not tag.is_empty_element:
            extracted_tag = tag.extract()

    def find_token(self, tag, token, attr):
        try:
            if not hasattr(self, attr): #or not getattr(self, attr):
                text = tag.text
                if text.startswith(token):
                    setattr(self, attr, text.split(':', 1)[-1].strip())
                    # print "parsing tag %s" % tag
                    # print "token | %s" % token
                    # print "text | %s" % text
                    # print "processed | %s" % text.split(':', 1)[-1].strip()
                    # print "has attr %s | %s" % (attr, hasattr(self, attr))
                    # print "get attr %s | %s" % (attr, getattr(self, attr))
                    # tag.extract()
                   
        except TypeError:
            pass

    def find_multiline_token(self, tag, token, attr, end):
        
        try:
            if not hasattr(self, attr) or not getattr(self, attr):
                text = tag.text
                try:
                    token = token.decode('utf-8')
                except AttributeError as e:
                    pass

                if text.startswith(token):
                    t = tag.text.split(':',1)
                    if len(t) == 1:
                        multiline_text = unicode(t[0]).replace(token,'')
                    else:
                        multiline_text = unicode(t[1]).replace(token,'')
                    multiline_text_tags = []
                    sibs = tag.next_siblings
                    
                    for sib in sibs:
                        
                        if sib.text.startswith(end):
                            break
                        else:
                            multiline_text += unicode(sib)
                            multiline_text_tags.append(sib)


                    multiline_text = multiline_text.replace('<p></p>','').replace('(build in relevant links, subheadings):','').replace('(build in relevant links, subheadings)','')
                    setattr(self, attr, multiline_text.strip())
                    setattr(self, '%s_tags' % attr, multiline_text_tags)

        except TypeError:
            pass

    def remove_inline_comment(self, tag):
        text = tag.text
        if text.startswith('##'):
            tag.extract()

    def clean_linebreaks(self, tag):
        """
        get unicode string without any other content transformation.
        and clean extra spaces
        """
        stripped = tag.decode(formatter=None)
        stripped = re.sub('\s+', ' ', stripped)
        stripped = re.sub('\n', '', stripped)
        return stripped

    def _parse_href(self, href):
        """
        Extract "real" URL from Google redirected url by getting `q`
        querystring parameter.
        """
        params = parse_qs(urlsplit(href).query)
        return params.get('q')

    def _parse_attr(self, tagname, attr, value):
        """
        Parse attribute. Delegate to href parser for hrefs, otherwise return
        value.
        """
        if tagname == 'a' and attr == 'href':
            return self._parse_href(value)
        else:
            return value

    def __unicode__(self):
        return ''.join([unicode(self.clean_linebreaks(tag))
                        for tag in self.soup.body.children])

    def __str__(self):
        return ''.join([str(self.clean_linebreaks(tag))
                       for tag in self.soup.body.children])
