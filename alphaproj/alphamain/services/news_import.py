"""Fetch RSS/Atom and convert source material into validated News fields."""
from datetime import datetime, timezone as datetime_timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

MAX_BYTES = 5 * 1024 * 1024
ATOM = '{http://www.w3.org/2005/Atom}'
CONTENT = '{http://purl.org/rss/1.0/modules/content/}encoded'


class FeedError(ValueError):
    pass


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if not self.hidden and tag in ('p', 'br', 'div', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if not self.hidden:
            self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value):
    parser = TextExtractor()
    parser.feed(value or '')
    return ' '.join(unescape(''.join(parser.parts)).split())


def canonical_url(value):
    value = value.strip()
    try:
        URLValidator(schemes=['http', 'https'])(value)
        parts = urlsplit(value)
        if parts.username or parts.password:
            raise ValueError('URL с учётными данными не поддерживается')
    except (ValidationError, ValueError) as exc:
        raise FeedError('Нужна корректная HTTP(S)-ссылка') from exc
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in ('fbclid', 'gclid')]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(sorted(query)), ''))


def fetch_feed(url, timeout=20):
    url = canonical_url(url)
    request = Request(url, headers={'User-Agent': 'ContextNews/1.0 (RSS reader)', 'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(MAX_BYTES + 1)
    except (OSError, ValueError) as exc:
        raise FeedError(f'Не удалось получить RSS/Atom: {exc}') from exc
    if len(payload) > MAX_BYTES:
        raise FeedError('Лента превышает ограничение 5 МБ')
    return payload


def node_text(element, path):
    node = element.find(path)
    return ''.join(node.itertext()).strip() if node is not None else ''


def publication_date(value):
    if not value:
        raise FeedError('Нет даты публикации')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        try:
            result = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError) as exc:
            raise FeedError('Не удалось разобрать дату публикации') from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise FeedError('Не указан часовой пояс публикации')
    return result.astimezone(datetime_timezone.utc)


def parse_feed(payload, feed_url, source_name=''):
    """Return (article dictionaries, skipped-entry descriptions). No network calls."""
    if len(payload) > MAX_BYTES:
        raise FeedError('Лента превышает ограничение 5 МБ')
    probe = payload.replace(b'\x00', b'').lower()
    if b'<!doctype' in probe or b'<!entity' in probe:
        raise FeedError('DTD и XML-сущности в лентах не поддерживаются')
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise FeedError(f'Некорректный XML: {exc}') from exc
    atom = root.tag == ATOM + 'feed'
    channel = root.find('channel')
    if not atom and (root.tag != 'rss' or channel is None):
        raise FeedError('Ожидается RSS 2.0 или Atom, получен другой документ')
    container = root if atom else channel
    source = plain_text(source_name or node_text(container, ATOM+'title' if atom else 'title'))
    if not source:
        raise FeedError('Нет названия источника: задайте --source-name')
    entries = container.findall(ATOM+'entry' if atom else 'item')
    articles, skipped = [], []
    for index, entry in enumerate(entries, start=1):
        try:
            if atom:
                title = plain_text(node_text(entry, ATOM+'title'))
                link = next((node.get('href', '') for node in entry.findall(ATOM+'link') if node.get('rel', 'alternate') == 'alternate'), '')
                summary = plain_text(node_text(entry, ATOM+'summary'))
                content = plain_text(node_text(entry, ATOM+'content'))
                date = node_text(entry, ATOM+'published') or node_text(entry, ATOM+'updated')
                categories = [node.get('term', '') for node in entry.findall(ATOM+'category')]
            else:
                title = plain_text(node_text(entry, 'title'))
                link = node_text(entry, 'link')
                summary = plain_text(node_text(entry, 'description'))
                content = plain_text(node_text(entry, CONTENT))
                date = node_text(entry, 'pubDate') or node_text(entry, '{http://purl.org/dc/elements/1.1/}date')
                categories = [node.text or '' for node in entry.findall('category')]
            if not title or not link:
                raise FeedError('Нет заголовка или ссылки')
            articles.append({
                'title': title[:300], 'summary': (summary or content or title)[:2000],
                'content': content or summary or title, 'source_name': source[:200],
                'source_url': canonical_url(urljoin(feed_url, link)),
                'published_at': publication_date(date),
                'category': ', '.join(plain_text(value) for value in categories if value.strip())[:120],
            })
        except (FeedError, ValueError, OverflowError) as exc:
            skipped.append(f'Запись {index}: {exc}')
    return articles, skipped
