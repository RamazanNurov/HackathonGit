from django.contrib import admin

from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_name', 'kind', 'status', 'published_at')
    list_filter = ('status', 'kind', 'category')
    search_fields = ('title', 'summary', 'content', 'source_name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'published_at'
    fieldsets = (
        ('Новость', {'fields': ('title', 'summary', 'content', 'category', 'kind', 'status')}),
        ('Первоисточник', {'fields': ('source_name', 'source_url', 'published_at')}),
        ('Аналитика банка', {'fields': ('bank_analysis', 'bank_source_url')}),
        ('Служебные поля', {'fields': ('created_at', 'updated_at')}),
    )
