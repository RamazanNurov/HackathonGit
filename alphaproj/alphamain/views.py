from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import RegistrationForm
from .models import News


@never_cache
@require_http_methods(['GET', 'POST'])
def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            form.add_error('email', 'Аккаунт с таким email уже существует.')
        else:
            login(request, user)
            return redirect('home')
    return render(request, 'alphamain/register.html', {'form': form})


@never_cache
@login_required
def feed_view(request):
    articles = list(News.objects.filter(
        status=News.Status.PUBLISHED, published_at__lte=timezone.now(),
    ).values('id', 'title', 'summary', 'content', 'source_name', 'source_url',
             'published_at', 'category', 'kind', 'bank_analysis', 'bank_source_url'))
    return render(request, 'alphamain/feed.html', {
        'news_data': articles,
        'account_data': {'id': request.user.pk, 'name': request.user.get_full_name() or request.user.email},
        'has_news': bool(articles),
    })
