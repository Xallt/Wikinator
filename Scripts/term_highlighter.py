from Scripts import searchers, targeter

SEARCHERS = {
    "Biology" : searchers.BiologySearcher,
    "Geography" : searchers.GeographySearcher,
    "Physics" : searchers.PhysicalSearcher
    # TODO: Astronomical searcher, Wikipedia searcher
}

class TermHighlighter:
    @staticmethod
    def highlight_term(word, term_link):
        return "<a href={}><high>{}</high></a>".format(term_link, word)
    def __init__(self, modes):
        self.searchers_dict = {k : SEARCHERS[k].get_term_links() for k in modes}
        self.modes = modes
        self.targeter = None
    def use_mode(self, mode):
        if mode in self.searchers_dict:
            self.targeter = targeter.TermListTargeter(self.searchers_dict.get(mode, None))
        elif mode == "Wiki" and mode in self.modes:
            self.targeter = targeter.WikiTargeter()

    def highlight_text(self, text, seps='.,?!- <>()[]"\'{}#;*:\n\t'):
        assert self.targeter is not None, "The targeter must be defined"
        for s in seps:
            if s in text:
                return s.join([self.highlight_text(t) for t in text.split(s)])
        link = self.targeter.match_word(text)
        if link is None:
            return text
        else:
            return TermHighlighter.highlight_term(text, link)