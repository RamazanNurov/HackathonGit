from django.db import models

from django.core.validators import URLValidator
from django.utils import timezone


class News(models.Model):
    class Kind(models.TextChoices):
        RISK = 'risk', 'Риск'
        OPPORTUNITY = 'opportunity', 'Возможность'
        NEUTRAL = 'neutral', 'К сведению'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'
        ARCHIVED = 'archived', 'В архиве'

    title = models.CharField('Заголовок', max_length=300)
    summary = models.TextField('Краткое содержание', max_length=2000)
    content = models.TextField('Полный текст')
    source_name = models.CharField('Название источника', max_length=200)
    source_url = models.URLField(
        'Ссылка на первоисточник', max_length=1000, unique=True,
        validators=[URLValidator(schemes=['http', 'https'])],
    )
    published_at = models.DateTimeField('Дата публикации источника', default=timezone.now)
    category = models.CharField('Категория / отрасль', max_length=120, blank=True)
    kind = models.CharField('Тип события', max_length=20, choices=Kind.choices, default=Kind.NEUTRAL)
    status = models.CharField('Статус', max_length=20, choices=Status.choices, default=Status.DRAFT)
    bank_analysis = models.TextField('Позиция банка (из источника)', blank=True)
    bank_source_url = models.URLField(
        'Источник позиции банка', max_length=1000, blank=True,
        validators=[URLValidator(schemes=['http', 'https'])],
    )
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'
        ordering = ['-published_at', '-pk']
        indexes = [models.Index(fields=['status', '-published_at'], name='news_status_date_idx')]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(bank_analysis='') | ~models.Q(bank_source_url=''),
                name='news_bank_analysis_has_source',
            ),
        ]

    def clean(self):
        super().clean()
        if self.bank_analysis and not self.bank_source_url:
            from django.core.exceptions import ValidationError
            raise ValidationError({'bank_source_url': 'Укажите источник позиции банка.'})

    def __str__(self):
        return self.title
