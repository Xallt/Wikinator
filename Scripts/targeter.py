from dataclasses import dataclass
from Scripts import searchers
from nltk.stem.snowball import RussianStemmer
from requests import get
from bs4 import BeautifulSoup
import re
import multiprocessing as mp

def ffilter(f, ar):
    return list(filter(f, ar))


def fmap(f, ar):
    return list(map(f, ar))

@dataclass
class MatchResult:
    link: str | None
    definition: str | None

class Targeter:
    many_targeting = False
    @staticmethod
    def word_root_match(word1, word2, stemmer):
        return stemmer.stem(word1) == stemmer.stem(word2)
    def match_word(self, word) -> MatchResult | None:
        raise NotImplementedError("Subclass must implement this method")
    @classmethod
    def targets_many(cls):
        return cls.many_targeting

class TermListTargeter(Targeter):
    many_targeting = True
    @staticmethod
    def true_stem(stemmer, word):
        while word != stemmer.stem(word):
            word = stemmer.stem(word)
        return word
    @staticmethod
    def to_term_searcher(terms_links, stemmer):
        future_links_searcher = {}
        for t in terms_links:
            future_links_searcher[TermListTargeter.true_stem(stemmer, t.word.lower())] = t
        return future_links_searcher

    def match_word(self, word) -> MatchResult | None:
        match = self.term_searcher.get(TermListTargeter.true_stem(self.stemmer, word.lower()))
        if match is None:
            return None
        else:
            definition = match.definition
            if (self.get_definition is not None) and (definition is None):
                definition = self.get_definition(match.link)
            # print(definition)
            if (definition is not None) and (len(definition) > 200):
                definition = definition[:200] + '...'
            return MatchResult(match.link, definition)
    def match_words(self, words):
        q = mp.Pool()
        matches = q.map(self.match_word, words)
        res = {}
        for i in range(len(words)):
            if matches[i] is not None:
                res[words[i].lower()] = matches[i]
        return res
    def __init__(self, terms_links, definition_getter = None):
        self.stemmer = RussianStemmer()
        self.term_searcher = TermListTargeter.to_term_searcher(terms_links, self.stemmer)
        self.get_definition = definition_getter

class WikiTargeter(Targeter):
    many_targeting = True
    @staticmethod
    def only_letters(word):
        return ''.join(ffilter(lambda c : ord(c) >= ord('а') and ord(c) <= ord('я'), word.lower()))
    def match_word(self, word, lim = 5) -> MatchResult | None:
        # print('Searching for ' + word)
        PARAMS = {
            'format' : 'json',
            'utf8' : '',
            'action':'opensearch',
            'search' : word,
            'limit' : lim
        }
        resp = get(self.wiki, PARAMS).json()
        print(resp)
        try:
            for i in range(lim):
                if resp[2][i].endswith(':') or len(resp[2][i].split()) <= 1:
                    continue
                res_word = WikiTargeter.only_letters(resp[1][i].split()[0])
                print(word, res_word)
                if self.stemmer.stem(res_word).lower() == self.stemmer.stem(word).lower():
                    return MatchResult(resp[3][i], resp[2][i])
            return None
        except:
            return None
    def match_words(self, words, lim = 5) -> dict[str, MatchResult | None]:
        q = mp.Pool()
        results = q.map(self.match_word, words)
        return {words[i].lower() : results[i] for i in range(len(words)) if results[i] is not None}
    def __init__(self, api='https://ru.wikipedia.org/w/api.php'):
        self.wiki = api
        self.stemmer = RussianStemmer()
class WiktionaryTargeter(Targeter):
    many_targeting = True
    @staticmethod
    def only_letters(word):
        return ''.join(ffilter(lambda c : ord(c) >= ord('а') and ord(c) <= ord('я'), word.lower()))
    def match_word(self, word, lim = 5) -> MatchResult | None:
        # print('Searching for ' + word)
        PARAMS = {
            'format' : 'json',
            'utf8' : '',
            'action':'opensearch',
            'search' : word,
            'limit' : lim
        }
        resp = get(self.wiktionary, PARAMS).json()
        try:
            return MatchResult(resp[3][0], None)
        except:
            return None
    def match_words(self, words, lim = 5):
        q = mp.Pool()
        results = q.map(self.match_word, words)
        return {words[i].lower() : results[i] for i in range(len(words)) if results[i] is not None}
    def __init__(self, api='https://ru.wiktionary.org/w/api.php'):
        self.wiktionary = api
        self.stemmer = RussianStemmer()
