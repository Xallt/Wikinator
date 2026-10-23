from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from nltk.stem.snowball import RussianStemmer

from Scripts.sources import SourceUnavailable, search


@dataclass(frozen=True)
class MatchResult:
    link: str
    definition: str | None


class Targeter:
    def match_words(self, words):
        words = list(dict.fromkeys(word.lower() for word in words if word))
        with ThreadPoolExecutor(max_workers=4) as pool:
            matches = pool.map(self.match_word, words)
            return {word: match for word, match in zip(words, matches) if match is not None}


class TermListTargeter(Targeter):
    @staticmethod
    def true_stem(stemmer, word):
        while word != stemmer.stem(word):
            word = stemmer.stem(word)
        return word

    def __init__(self, terms_links, definition_getter=None):
        self.stemmer = RussianStemmer()
        self.terms = {self.true_stem(self.stemmer, term.word.lower()): term for term in terms_links}
        self.get_definition = definition_getter

    def match_word(self, word):
        match = self.terms.get(self.true_stem(self.stemmer, word.lower()))
        if match is None:
            return None
        definition = match.definition
        if self.get_definition and not definition:
            try:
                definition = self.get_definition(match.link)
            except SourceUnavailable:
                pass  # A missing tooltip must not discard a valid dictionary link.
        return MatchResult(match.link, definition[:200] if definition else None)


class WikiTargeter(Targeter):
    def __init__(self, api="https://ru.wikipedia.org/w/api.php"):
        self.api = api
        self.stemmer = RussianStemmer()

    def match_word(self, word):
        for title, description, url in search(self.api, word):
            # Wikipedia's opensearch descriptions are now empty; titles still identify matches.
            if self.stemmer.stem(title.lower()) == self.stemmer.stem(word.lower()):
                return MatchResult(url, description or None)
        return None


class WiktionaryTargeter(WikiTargeter):
    def __init__(self):
        super().__init__("https://ru.wiktionary.org/w/api.php")
