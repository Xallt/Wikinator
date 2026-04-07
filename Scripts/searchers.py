import requests
from bs4 import BeautifulSoup
import re


def ffilter(f, ar):
    return list(filter(f, ar))


def fmap(f, ar):
    return list(map(f, ar))

class TermLink:
    def __init__(self, word, link, definition = None):
        self.word = word
        self.link = link
        self.definition = definition
    def __str__(self):
        return "{{word={} link=\"{}\"}}".format(self.word, self.link)
class ManyTermsLink:
    def __init__(self, words, link):
        self.words = words
        self.link = link

    def __str__(self):
        return "{{words={} link=\"{}\"}}".format(self.words, self.link)
    def to_term_links(self):
        return [TermLink(w, self.link) for w in self.words]

class Searcher:
    main_api_page = ""
    can_get_definition = False
    # Returns only the singular-word terms
    # (Maybe sometime I'll be able to highlight double-word terms, but i'd need ML for that)
    @staticmethod
    def split_words(line):
        return fmap(lambda x: x.strip(' '), re.split('[\\.,]', line))

    # Returns list of TermLinks extracted from main_api_page
    @classmethod
    def get_term_links(cls) -> list[TermLink]:
        raise NotImplementedError("Subclass must implement this method")
    @classmethod
    def is_word(cls, line):
        return re.match(r'^[а-яА-Я]+$', line)


class BiologySearcher(Searcher):
    main_api_page = "https://licey.net/free/6-biologiya/25-slovar_biologicheskih_terminov.html"
    can_get_definition = True
    @classmethod
    def get_term_links(cls):
        soup = BeautifulSoup(requests.get(cls.main_api_page).text, 'html.parser')
        a_tags = soup.find_all('a')
        right_tags = ffilter(
            lambda s: s.text.capitalize() == s.text and \
            s.get('href') is not None and \
            s.get('href').startswith(
                '/free/6-biologiya/25-slovar_biologicheskih_terminov/stages') and \
            cls.is_word(s.text),
            a_tags
        )
        pre_link = "https://licey.net"
        return fmap(
            lambda a: TermLink(a.text, pre_link + a.get('href')),#, cls.get_definition(pre_link + a.get('href'))),
            right_tags
        )
    @classmethod
    def get_definition(cls, url):
        p = BeautifulSoup(requests.get(url).content, 'html.parser').find('p', {'class' : 'slovarP'})
        if p is None:
            return None
        else:
            return p.text



class GeographySearcher(Searcher):
    main_api_page="http://www.ecosystema.ru/07referats/slovgeo/index.htm"
    can_get_definition = True
    @classmethod
    def get_term_links(cls):
        soup=BeautifulSoup(requests.get(cls.main_api_page).text, 'html.parser')
        a_tags=soup.find_all("a")
        right_tags=ffilter(
            lambda s: s.get('href') is not None and \
            re.match(r'\d+\.htm', s.get('href')) and \
            cls.is_word(s.text),
            a_tags
        )
        pre_link="http://www.ecosystema.ru/07referats/slovgeo/"
        return fmap(
            lambda s: TermLink(s.text, pre_link + s.get('href')),
            right_tags
        )
    @classmethod
    def get_definition(cls, url):
        soup = BeautifulSoup(requests.get(url).content, 'html.parser').find('span', {'itemprop' : 'definition'})
        return soup.text if soup is not None else None
class PhysicalSearcher(Searcher):
    main_api_page='http://www.physics.org.ua/info/voc/a.html'
    @classmethod
    def ok_term_name(cls, word):
        return re.match(r'^[А-Я]+$', word)
    @classmethod
    def term_links_from_url(cls, url):
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        lines = soup.find_all('p', {'class' : 'MsoNormal'})
        res = []
        for line in lines:
            if len(line.text.split()) <= 1:
                continue
            first_word = line.text.split()[0]
            if cls.ok_term_name(first_word):
                res.append(TermLink(first_word, url, line.text))
        return res
    @classmethod
    def get_term_links(cls):
        soup = BeautifulSoup(requests.get(cls.main_api_page).content, 'html.parser')
        if soup is None:
            return []
        marquee = soup.find('marquee')
        if marquee is None:
            return []
        pages = marquee.find_all('a')
        res = []
        pre_link = 'http://www.physics.org.ua/info/voc/'
        for i in pages:
            href = i.get('href')
            if href is None:
                continue
            href = str(href)
            res += cls.term_links_from_url(pre_link + href)
        return res
class AstronomicalSearcher(Searcher):
    main_api_page = 'http://www.astronet.ru/db/glossary/_e1'
    can_get_definition = True
    @classmethod
    def termlinks_from_url(cls, url):
        if url is None:
            return []
        soup = BeautifulSoup(requests.get(url).content, 'html.parser')
        if soup is None:
            return []
        a_list = soup.find_all('a')
        pre_link = 'http://www.astronet.ru'
        a_correct = ffilter(
            lambda a : (a.get('href').startswith('/db/msg') or a.get('href').startswith(pre_link + '/db/msg')) and cls.is_word(a.text),
            a_list
        )
        res = []
        for a in a_correct:
            href = a.get('href')
            if href is None:
                continue
            href = str(href)
            if href.startswith('/db/msg'):
                res.append(TermLink(a.text, pre_link + href))
            else:
                res.append(TermLink(a.text, href))
        return res
    @classmethod
    def get_term_links(cls):
        b = BeautifulSoup(requests.get(cls.main_api_page).content, 'html.parser')

        termlinks = cls.termlinks_from_url(cls.main_api_page)
        letter_links = ffilter(
            lambda a : len(a.text) == 1 and \
             ord('А') <= ord(a.text) <= ord('Я'),
            b.find_all('a')
        )
        letter_dict = {}
        pre_link = 'http://www.astronet.ru'
        for l in letter_links:
            href = l.get('href')
            if href is None:
                continue
            href = str(href)
            letter_dict[l.text.lower()] = pre_link + href
        for k, v in letter_dict.items():
            if k != 'А':
                termlinks += cls.termlinks_from_url(v)
        return termlinks
    @classmethod
    def get_definition(cls, url):
        b = BeautifulSoup(requests.get(url).content.decode('windows-1251'), 'html.parser')
        definition = b.find('span', {'itemprop' : 'definition'})
        if definition is not None:
            definision_span = definition.find('span', {'itemprop' : 'definition'})
            return definision_span.text if definision_span is not None else None
        else:
            p_list = b.select("#content p")
            for p in p_list:
                if len(p.text.split()) > 5 and ord('А') <= ord(p.text[0]) <= ord('Я'):
                    return p.text
            return None
if __name__ == '__main__':
    for t in AstronomicalSearcher.get_term_links():
        print(t.word, t.link)