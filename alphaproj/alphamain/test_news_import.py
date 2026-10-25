from io import BytesIO, StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase

from .models import News
from .services.news_import import FeedError, MAX_BYTES, canonical_url, fetch_feed, parse_feed

RSS = b'''<rss version="2.0"><channel><title>Test source</title><item>
<title>New factory</title><link>https://example.com/news?utm_source=rss</link>
<description>&lt;p&gt;Text &amp;amp; facts&lt;/p&gt;&lt;script&gt;bad()&lt;/script&gt;</description>
<pubDate>Mon, 26 Oct 2026 10:00:00 +0300</pubDate><category>Economy</category>
</item></channel></rss>'''


class ParserTests(SimpleTestCase):
    def test_rss_fields_and_html_cleanup(self):
        rows, skipped = parse_feed(RSS, 'https://example.com/rss')
        self.assertEqual(skipped, [])
        self.assertEqual(rows[0]['source_name'], 'Test source')
        self.assertEqual(rows[0]['summary'], 'Text & facts')
        self.assertEqual(rows[0]['source_url'], 'https://example.com/news')
        self.assertEqual(rows[0]['published_at'].hour, 7)
        self.assertEqual(rows[0]['category'], 'Economy')

    def test_atom_relative_link_and_iso_date(self):
        data = b'''<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title>
        <entry><title>Event</title><link href="/article"/><summary>Summary</summary>
        <updated>2026-10-26T12:00:00Z</updated><category term="Finance"/></entry></feed>'''
        rows, skipped = parse_feed(data, 'https://example.com/feed')
        self.assertFalse(skipped)
        self.assertEqual(rows[0]['source_url'], 'https://example.com/article')
        self.assertEqual(rows[0]['category'], 'Finance')

    def test_bad_entry_does_not_prevent_good_entry(self):
        data = RSS.replace(b'</channel>', b'<item><title>Missing link</title></item></channel>')
        rows, skipped = parse_feed(data, 'https://example.com/rss')
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(skipped), 1)

    def test_missing_or_invalid_date_is_not_fabricated(self):
        for date in (b'', b'nonsense', b'2026-10-26T12:00:00'):
            data = RSS.replace(b'Mon, 26 Oct 2026 10:00:00 +0300', date)
            rows, skipped = parse_feed(data, 'https://example.com/rss')
            self.assertFalse(rows)
            self.assertEqual(len(skipped), 1)

    def test_invalid_xml_dtd_and_html_rejected(self):
        for data in (b'<broken', b'<!DOCTYPE rss><rss/>', b'<html><body>Error</body></html>'):
            with self.subTest(data=data), self.assertRaises(FeedError):
                parse_feed(data, 'https://example.com/rss')

    def test_canonical_url_preserves_meaningful_query(self):
        self.assertEqual(canonical_url('https://example.com/article?id=2&utm_source=a#top'), 'https://example.com/article?id=2')
        with self.assertRaises(FeedError):
            canonical_url('file:///etc/passwd')

    @patch('alphamain.services.news_import.urlopen')
    def test_fetch_size_limit_and_timeout(self, open_mock):
        open_mock.return_value.__enter__.return_value = BytesIO(b'x' * (MAX_BYTES+1))
        with self.assertRaises(FeedError):
            fetch_feed('https://example.com/rss', timeout=7)
        self.assertEqual(open_mock.call_args.kwargs['timeout'], 7)


class ImportCommandTests(TestCase):
    def run_import(self, **kwargs):
        out = StringIO()
        call_command('import_news', url=['https://example.com/rss'], stdout=out, stderr=StringIO(), **kwargs)
        return out.getvalue()

    @patch('alphamain.management.commands.import_news.fetch_feed', return_value=RSS)
    def test_repeated_import_and_publish(self, fetch):
        self.run_import(publish=True)
        self.run_import(publish=True)
        self.assertEqual(News.objects.count(), 1)
        self.assertEqual(News.objects.get().status, News.Status.PUBLISHED)
        self.assertEqual(News.objects.get().kind, News.Kind.NEUTRAL)

    @patch('alphamain.management.commands.import_news.fetch_feed', return_value=RSS)
    def test_draft_and_existing_edits_are_preserved(self, fetch):
        self.run_import()
        article = News.objects.get()
        self.assertEqual(article.status, News.Status.DRAFT)
        article.title = 'Editor changed title'
        article.save()
        self.run_import(publish=True)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Editor changed title')
        self.assertEqual(article.status, News.Status.DRAFT)

    @patch('alphamain.management.commands.import_news.fetch_feed', return_value=RSS)
    def test_dry_run_and_category_filter(self, fetch):
        self.run_import(dry_run=True)
        self.assertFalse(News.objects.exists())
        self.run_import(category='Sport')
        self.assertFalse(News.objects.exists())
        self.run_import(category='economy')
        self.assertEqual(News.objects.count(), 1)

    @patch('alphamain.management.commands.import_news.fetch_feed', side_effect=[FeedError('offline'), RSS])
    def test_source_failure_does_not_stop_other_sources(self, fetch):
        with self.assertRaises(CommandError):
            call_command('import_news', url=['https://offline.example/rss', 'https://example.com/rss'], stdout=StringIO(), stderr=StringIO())
        self.assertEqual(News.objects.count(), 1)
