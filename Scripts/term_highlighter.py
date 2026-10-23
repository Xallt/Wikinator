"""Load usable sources once and keep highlighting state within each request."""
from concurrent.futures import ThreadPoolExecutor
from html import escape
import logging
import re

from Scripts.searchers import SEARCHERS, load_terms
from Scripts.sources import SourceUnavailable
from Scripts.targeter import TermListTargeter, WikiTargeter, WiktionaryTargeter

MODES = (*SEARCHERS, "Wiki", "Wiktionary")
WORDS = re.compile(r"[а-яёА-ЯЁ]+")


class TermHighlighter:
    def __init__(self, modes=MODES):
        self.targeters = {}
        self.unavailable = []

        def load(mode):
            try:
                if mode in SEARCHERS:
                    return mode, TermListTargeter(load_terms(mode), SEARCHERS[mode].get_definition)
                targeter = WikiTargeter() if mode == "Wiki" else WiktionaryTargeter()
                if targeter.match_word("атом") is None:
                    raise SourceUnavailable("Source probe found no reference")
                return mode, targeter
            except SourceUnavailable as error:
                logging.warning("%s unavailable: %s", mode, error)
                return mode, None

        with ThreadPoolExecutor(max_workers=5) as pool:
            for mode, targeter in pool.map(load, modes):
                if targeter is not None:
                    self.targeters[mode] = targeter
                else:
                    self.unavailable.append(mode)
        self.modes = list(self.targeters)

    @staticmethod
    def highlight_term(word, link, definition):
        tooltip = f' definition="{escape(definition, quote=True)}"' if definition else ""
        return f'<a href="{escape(link, quote=True)}" class="termlink" contenteditable="false"{tooltip}>{escape(word)}</a>'

    def highlight_text(self, text, mode):
        if mode not in self.targeters:
            raise ValueError("Choose an available source")
        targeter = self.targeters[mode]
        matches = targeter.match_words(WORDS.findall(text))
        parts = []
        previous = 0
        for word in WORDS.finditer(text):
            parts.append(escape(text[previous:word.start()]))
            match = matches.get(word.group().lower())
            parts.append(self.highlight_term(word.group(), match.link, match.definition)
                         if match else escape(word.group()))
            previous = word.end()
        parts.append(escape(text[previous:]))
        return "".join(parts)
