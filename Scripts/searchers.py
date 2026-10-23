"""Scrapers for the surviving Russian subject dictionaries."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import re
from urllib.parse import urljoin

from Scripts.sources import SourceUnavailable, html


@dataclass(frozen=True)
class TermLink:
    word: str
    link: str
    definition: str | None = None


class Searcher:
    can_get_definition = True

    @staticmethod
    def is_word(text):
        return re.fullmatch(r"[а-яёА-ЯЁ]+", text.strip()) is not None

    @classmethod
    def get_term_links(cls):
        raise NotImplementedError


class BiologySearcher(Searcher):
    main_api_page = "https://licey.net/free/6-biologiya/25-slovar_biologicheskih_terminov.html"

    @classmethod
    def get_term_links(cls):
        return [TermLink(a.get_text(strip=True), urljoin(cls.main_api_page, a["href"]))
                for a in html(cls.main_api_page).select("a[href]")
                if a["href"].startswith("/free/6-biologiya/25-slovar_biologicheskih_terminov/stages")
                and cls.is_word(a.get_text(strip=True))]

    @staticmethod
    def get_definition(url):
        paragraph = html(url).find("p", class_="slovarP")
        return paragraph.get_text(" ", strip=True) if paragraph else None


class GeographySearcher(Searcher):
    main_api_page = "https://ecosystema.ru/07referats/slovgeo/index.htm"

    @classmethod
    def get_term_links(cls):
        return [TermLink(a.get_text(strip=True), urljoin(cls.main_api_page, a["href"]))
                for a in html(cls.main_api_page).select("a[href]")
                if re.fullmatch(r"\d+\.htm", a["href"])
                and cls.is_word(a.get_text(strip=True))]

    @staticmethod
    def get_definition(url):
        definition = html(url).find("span", itemprop="definition")
        return definition.get_text(" ", strip=True) if definition else None


class AstronomicalSearcher(Searcher):
    main_api_page = "https://www.astronet.ru/db/glossary/_e1"

    @classmethod
    def termlinks_from_page(cls, page):
        return [TermLink(a.get_text(strip=True), urljoin(cls.main_api_page, a["href"]))
                for a in page.select("a[href]")
                if (a["href"].startswith("/db/msg")
                    or a["href"].startswith("https://www.astronet.ru/db/msg"))
                and cls.is_word(a.get_text(strip=True))]

    @classmethod
    def get_term_links(cls):
        page = html(cls.main_api_page)
        pages = {urljoin(cls.main_api_page, a["href"]) for a in page.select("a[href]")
                 if re.fullmatch("[А-ЯЁ]", a.get_text(strip=True))
                 and a["href"].startswith("/db/glossary/")}
        terms = cls.termlinks_from_page(page)
        pool = ThreadPoolExecutor(max_workers=6)
        try:
            futures = [pool.submit(lambda url: cls.termlinks_from_page(html(url)), url) for url in sorted(pages)]
            for future in futures:
                terms.extend(future.result())
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
        return list({term.word: term for term in terms}.values())

    @staticmethod
    def get_definition(url):
        page = html(url)
        definition = page.find("span", itemprop="definition")
        if definition:
            return definition.get_text(" ", strip=True)
        return next((p.get_text(" ", strip=True) for p in page.select("#content p")
                     if len(p.get_text().split()) > 5), None)


SEARCHERS = {"Biology": BiologySearcher, "Geography": GeographySearcher,
             "Astronomy": AstronomicalSearcher}


def load_terms(mode):
    links = SEARCHERS[mode].get_term_links()
    if not links:
        raise SourceUnavailable(f"{mode} returned no terms")
    return links
