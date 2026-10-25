from django.shortcuts import render


def register_view(request):
    return render(request, 'alphamain/register.html')


def feed_view(request):
    return render(request, 'alphamain/feed.html')
