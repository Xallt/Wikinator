# Wikinator

Detects Russian science terms in text and links them to reference pages.
Originally an individual final project for the HSE lyceum; powered by Python,
Flask, and NLTK's Russian stemmer.

Choose Biology, Geography, Astronomy, Wiki, or Wiktionary, paste text, and select
**Highlight terms**. Hover over dictionary links for definitions where available;
**Get HTML** copies the linked text and **Clear highlight** restores editing.
Physics was removed because its former provider (`www.physics.org.ua`) no longer
resolves.

The retained providers are Licey, Ecosystema, Astronet, Russian Wikipedia, and
Russian Wiktionary. Requests identify Wikinator, enforce timeouts, and decode the
legacy dictionary pages as Windows-1251. Wikipedia matches article titles even
when its search API omits descriptions. Unique words are looked up with bounded
threads; each request keeps its own mode. User text and tooltip markup are escaped.

Sources are checked and dictionaries loaded on the worker's first request.
Empty or unreachable sources are hidden from the selector, with a visible status
message; restart the service to retry loading them. A later provider outage shows
an error and lets you retry or choose another source. Unavailable optional
hover definitions do not prevent highlighting valid dictionary links.

Install dependencies with `uv sync --locked`. The deployment entry point is
`app:app`; site-root supervises it with Gunicorn. Run offline regressions with:

```sh
uv run python -m unittest discover -s tests -v
```

To verify providers live without starting a server, import `app`, use
`app.test_client()`, and request `/highlightWithMode` for each mode with a known
term (e.g. клетка, абразия, азимут, атом, атом). This performs real reference
requests; it does not deploy or bind a listening socket.
