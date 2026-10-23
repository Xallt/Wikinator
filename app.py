from functools import lru_cache
from flask import Flask, render_template, request, jsonify
from Scripts.sources import SourceUnavailable
from Scripts.term_highlighter import TermHighlighter


def create_app(highlighter=None):
    app = Flask(__name__)
    @lru_cache(maxsize=1)
    def resources():
        return highlighter if highlighter is not None else TermHighlighter()

    @app.route('/')
    def main_page():
        highlighter = resources()
        status = "Resources loaded successfully"
        if highlighter.unavailable:
            status = "Temporarily unavailable (hidden): " + ", ".join(highlighter.unavailable)
        if not highlighter.modes:
            status = "Reference sources are unavailable. Reload after restarting the service."
        return render_template("mainPage.html", availableModes=highlighter.modes,
                               status=status, statusColor="red" if highlighter.unavailable else "rgb(94, 228, 11)")

    @app.route('/highlightWithMode')
    def highlight_text():
        highlighter = resources()
        mode = request.args.get("mode", "")
        text = request.args.get("text", "")
        if mode not in highlighter.modes:
            return jsonify(error="Choose an available source"), 400
        if len(text) > 20000:
            return jsonify(error="Use at most 20,000 characters at a time"), 400
        try:
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')
            return jsonify(highlightedText=highlighter.highlight_text(text, mode))
        except SourceUnavailable:
            return jsonify(error="This source is temporarily unavailable. Try again or choose another source."), 503

    return app


app = create_app()
