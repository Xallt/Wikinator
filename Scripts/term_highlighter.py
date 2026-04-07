#!/usr/bin/env python
# -*- coding: utf-8 -*-
import multiprocessing as mp

import requests

from Scripts import searchers, targeter

SEARCHERS = {
    "Biology" : searchers.BiologySearcher,
    "Geography" : searchers.GeographySearcher,
    "Physics" : searchers.PhysicalSearcher,
    "Astronomy" : searchers.AstronomicalSearcher
}

DEFAULT_SEPS=list('\n\t .,/\\<>?!@"\'#$%^&*()[]{}:;~`|+' + u'«»') + ['- ', ' -']

class TermHighlighter:
    @staticmethod
    def highlight_term(word, term_link, definition):
        if term_link is None:
            return word
        else:
            if definition is None:
                return "<a href=\"{}\" class=\"termlink\" contenteditable=\"false\">{}</a>".format(term_link, word)
            else:
                return "<a href=\"{}\" class=\"termlink\" contenteditable=\"false\" definition=\"{}\">{}</a>".format(term_link, definition, word)
    @staticmethod
    def get_mode_links(mode):
        if mode not in SEARCHERS:
            return None
        try:
            links = SEARCHERS[mode].get_term_links()
            print("Got " + mode)
            return links
        except requests.exceptions.RequestException:
            print("Skipped " + mode + " (failed to resolve)")
            return None
    def __init__(self, modes):
        self.searchers_dict = {}
        q = mp.Pool()
        results = q.map(TermHighlighter.get_mode_links, modes)
        for i in range(len(modes)):
            if results[i] is not None:
                self.searchers_dict[modes[i]] = results[i]
        print("Done initialising")
        self.modes = modes
        self.targeter = None
    def use_mode(self, mode):
        if mode in self.searchers_dict:
            definition_getter = None
            if SEARCHERS[mode].can_get_definition:
                definition_getter = SEARCHERS[mode].get_definition
            self.targeter = targeter.TermListTargeter(self.searchers_dict.get(mode), definition_getter)
        elif mode == 'Wiki' and mode in self.modes:
            self.targeter = targeter.WikiTargeter()
        elif mode == 'Wiktionary' and mode in self.modes:
            self.targeter = targeter.WiktionaryTargeter()
        else:
            raise ValueError("Invalid mode: " + mode)
    def highlight_text(self, text):
        if self.targeter is None:
            raise ValueError("Targeter is not initialized")
        if self.targeter.targets_many():
            return self.highlight_many(text)
        else:
            return self.highlight_single(text)
    def highlight_single(self, text, seps=DEFAULT_SEPS):
        if self.targeter is None:
            raise ValueError("Targeter is not initialized")
        for s in seps:
            if s in text:
                return s.join([self.choose_words(t, seps) for t in text.split(s)])
        parsed_word = self.targeter.match_word(text)
        if parsed_word is None:
            return text
        else:
            return TermHighlighter.highlight_term(text, parsed_word.link, parsed_word.definition)
    def highlight_many(self, text):
        if self.targeter is None:
            raise ValueError("Targeter is not initialized")
        form_text, words = TermHighlighter.choose_words(text, DEFAULT_SEPS)
        matches: dict[str, targeter.MatchResult | None] = self.targeter.match_words(words)

        res = []
        for w in words:
            match = matches.get(w.lower())
            if match is not None:
                res.append(TermHighlighter.highlight_term(w, match.link, match.definition))
            else:
                res.append(w)
        return form_text.format(*res)
    @staticmethod
    def choose_words(text, seps=DEFAULT_SEPS):
        for s in seps:
            if s in text:
                ss, ww = [], []
                for t in text.split(s):
                    chosen = TermHighlighter.choose_words(t)
                    ss.append(chosen[0])
                    ww += chosen[1]
                return (s.join(ss), ww)
        return '{}', [text]
