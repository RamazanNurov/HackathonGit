from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from alphamain.models import News
from alphamain.services.news_import import FeedError, fetch_feed, parse_feed


class Command(BaseCommand):
    help = 'Загрузить RSS/Atom в News без дублей; по умолчанию как черновики.'

    def add_arguments(self, parser):
        parser.add_argument('--url', action='append', help='RSS/Atom URL; можно указать несколько раз')
        parser.add_argument('--source-name', default='', help='Название источника вместо заголовка RSS')
        parser.add_argument('--category', default='', help='Оставить категории, содержащие эту строку')
        parser.add_argument('--limit', type=int, default=30, help='Максимум записей на источник после фильтрации')
        parser.add_argument('--timeout', type=int, default=20, help='Сетевой таймаут в секундах')
        parser.add_argument('--publish', action='store_true', help='Сразу опубликовать новые записи')
        parser.add_argument('--dry-run', action='store_true', help='Проверить импорт без записи в базу')

    def handle(self, *args, **options):
        if not 1 <= options['limit'] <= 500:
            raise CommandError('--limit должен быть от 1 до 500')
        if not 1 <= options['timeout'] <= 120:
            raise CommandError('--timeout должен быть от 1 до 120')
        urls = options['url'] or getattr(settings, 'NEWS_FEED_URLS', [])
        if not urls:
            raise CommandError('Укажите --url или NEWS_FEED_URLS в settings.py')
        created = duplicates = invalid = failures = selected = 0
        seen = set()
        for url in urls:
            try:
                rows, skipped = parse_feed(fetch_feed(url, options['timeout']), url, options['source_name'])
            except FeedError as exc:
                failures += 1
                self.stderr.write(f'Ошибка источника {url}: {exc}')
                continue
            invalid += len(skipped)
            for message in skipped:
                self.stderr.write(f'{url}: {message}')
            rows = [row for row in rows if options['category'].casefold() in row['category'].casefold()]
            for fields in rows[:options['limit']]:
                selected += 1
                link = fields['source_url']
                if link in seen or News.objects.filter(source_url=link).exists():
                    duplicates += 1
                    continue
                seen.add(link)
                article = News(**fields, status=News.Status.PUBLISHED if options['publish'] else News.Status.DRAFT)
                try:
                    article.full_clean(validate_unique=False)
                except ValidationError as exc:
                    invalid += 1
                    self.stderr.write(f'Пропущено {link}: {exc}')
                    continue
                if options['dry_run']:
                    created += 1
                    self.stdout.write(f'[Проверка] {article.title}')
                else:
                    # get_or_create also handles concurrent imports of the same URL.
                    _, was_created = News.objects.get_or_create(source_url=link, defaults={
                        **{key: value for key, value in fields.items() if key != 'source_url'},
                        'status': article.status,
                    })
                    created += int(was_created)
                    duplicates += int(not was_created)
        self.stdout.write(f"{'Проверка без записи' if options['dry_run'] else 'Импорт завершён'}: выбранo {selected}, новых {created}, дублей {duplicates}, некорректных {invalid}, ошибок источников {failures}.")
        if failures:
            raise CommandError('Не все источники доступны. Остальные обработаны; повторный запуск безопасен.')
