from django.urls import path
from .views import feed_view, register_view

urlpatterns = [
    path('', feed_view, name='feed'),
    path('register/', register_view, name='register'),
]
