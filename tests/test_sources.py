import unittest
from unittest.mock import patch
import requests
from bs4 import BeautifulSoup

from app import create_app
from Scripts.searchers import BiologySearcher, GeographySearcher, AstronomicalSearcher
from Scripts.sources import SourceUnavailable
from Scripts.term_highlighter import TermHighlighter


HTML = {
    BiologySearcher.main_api_page: '<a href="/free/6-biologiya/25-slovar_biologicheskih_terminov/stages/1.html">Клетка</a>',
    GeographySearcher.main_api_page: '<a href="003.htm">Абразия</a>',
    AstronomicalSearcher.main_api_page: '<a>Missing href</a><a href="/db/glossary/_e2">Б</a><a href="/db/msg/1">Азимут</a>',
    'https://www.astronet.ru/db/glossary/_e2': '<a href="/db/msg/2">Болид</a>',
}


def provider_response(url, params=None, headers=None, timeout=None):
    if not headers or 'Wikinator' not in headers.get('User-Agent', '') or timeout is None:
        raise AssertionError('Provider requests must identify themselves and have a timeout')
    response = requests.Response()
    response.status_code = 200
    response.url = url
    if params:
        word = params['search']
        response._content = ('["' + word + '",["' + word + '"],[""],["https://example.org/wiki/' + word + '"]]').encode()
        response.encoding = 'utf-8'
    else:
        response._content = HTML.get(url, '<p class="slovarP">A "quoted" definition &lt;tag&gt;</p>').encode('windows-1251')
        response.encoding = 'ISO-8859-1'
    return response


class SourcesTests(unittest.TestCase):
    @patch('Scripts.sources.requests.get', side_effect=provider_response)
    def test_every_listed_source_highlights_and_links_with_legacy_encoding(self, _request):
        highlighter = TermHighlighter()
        client = create_app(highlighter).test_client()
        page = BeautifulSoup(client.get('/').data, 'html.parser')
        modes = [option['value'] for option in page.select('option[value]') if option['value']]
        self.assertEqual(modes, ['Biology', 'Geography', 'Astronomy', 'Wiki', 'Wiktionary'])
        for mode, word in zip(modes, ['клетка', 'абразия', 'болид', 'атом', 'атом']):
            response = client.get('/highlightWithMode', query_string={'mode': mode, 'text': word})
            self.assertEqual(response.status_code, 200)
            link = BeautifulSoup(response.json['highlightedText'], 'html.parser').find('a')
            self.assertIsNotNone(link, mode)
            self.assertEqual(link.text, word)
            self.assertTrue(link['href'].startswith('https://'))

    def test_failed_and_empty_sources_are_hidden_without_breaking_others(self):
        def unavailable(url, **kwargs):
            if url == BiologySearcher.main_api_page:
                raise requests.Timeout()
            if url == GeographySearcher.main_api_page:
                response = provider_response(url, **kwargs)
                response._content = b'<html>No dictionary here</html>'
                return response
            return provider_response(url, **kwargs)
        with patch('Scripts.sources.requests.get', side_effect=unavailable):
            highlighter = TermHighlighter()
            self.assertEqual(highlighter.modes, ['Astronomy', 'Wiki', 'Wiktionary'])
            self.assertEqual(highlighter.unavailable, ['Biology', 'Geography'])
            client = create_app(highlighter).test_client()
            self.assertEqual(client.get('/highlightWithMode', query_string={'mode': 'Physics'}).status_code, 400)
            self.assertIn(b'Temporarily unavailable', client.get('/').data)

    @patch('Scripts.sources.requests.get', side_effect=provider_response)
    def test_plain_text_and_tooltip_are_escaped_and_mode_is_request_specific(self, _request):
        highlighter = TermHighlighter()
        client = create_app(highlighter).test_client()
        response = client.get('/highlightWithMode', query_string={'mode': 'Biology', 'text': '<script>x</script> {клетка}\n&'})
        html = response.json['highlightedText']
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&quot;quoted&quot;', html)
        self.assertIn('{<a ', html)
        self.assertIn('\n&amp;', html)
        self.assertNotIn('<a ', highlighter.highlight_text('клетка', 'Geography'))
        with patch('Scripts.sources.requests.get', side_effect=requests.Timeout()):
            failure = client.get('/highlightWithMode', query_string={'mode': 'Wiki', 'text': 'атом'})
            self.assertEqual(failure.status_code, 503)
            self.assertIn('temporarily unavailable', failure.json['error'])
            self.assertIn('<a ', highlighter.highlight_text('клетка', 'Biology'))

    def test_invalid_api_data_reports_failure_instead_of_no_matches(self):
        def invalid(url, **kwargs):
            response = provider_response(url, **kwargs)
            response._content = b'{"error":"unavailable"}'
            return response
        with patch('Scripts.sources.requests.get', side_effect=invalid):
            from Scripts.targeter import WikiTargeter
            with self.assertRaises(SourceUnavailable):
                WikiTargeter().match_word('атом')


if __name__ == '__main__':
    unittest.main()
