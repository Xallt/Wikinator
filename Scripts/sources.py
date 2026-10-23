"""Bounded, identifiable requests to reference providers."""
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Wikinator/0.1 (https://github.com/Xallt/Wikinator; reference lookup)"


class SourceUnavailable(Exception):
    """The provider could not supply usable reference data."""


def fetch(url, params=None):
    try:
        response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=(3, 8))
        response.raise_for_status()
        if not response.content:
            raise SourceUnavailable("Source returned an empty response")
        return response
    except requests.RequestException as error:
        raise SourceUnavailable("Reference source is temporarily unavailable") from error


def html(url, encoding="windows-1251"):
    # These older dictionaries declare Windows-1251 inconsistently in HTTP headers.
    return BeautifulSoup(fetch(url).content.decode(encoding, errors="replace"), "html.parser")


def search(api, word, limit=5):
    try:
        result = fetch(api, {"action": "opensearch", "search": word, "limit": limit,
                             "format": "json", "namespace": 0}).json()
    except ValueError as error:
        raise SourceUnavailable("Source returned invalid search data") from error
    if not isinstance(result, list) or len(result) != 4 or not all(isinstance(part, list) for part in result[1:]):
        raise SourceUnavailable("Source returned unexpected search data")
    if not (len(result[1]) == len(result[2]) == len(result[3])):
        raise SourceUnavailable("Source returned incomplete search data")
    rows = list(zip(result[1], result[2], result[3]))
    if any(not all(isinstance(value, str) for value in row) or not row[2].startswith("https://") for row in rows):
        raise SourceUnavailable("Source returned invalid reference links")
    return rows
