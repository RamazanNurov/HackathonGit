from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .forms import EmailAuthenticationForm
from .views import feed_view, register_view

urlpatterns = [
    path('', feed_view, name='feed'),
    path('register/', register_view, name='register'),
    path('login/', LoginView.as_view(template_name='alphamain/registerAndName.html', authentication_form=EmailAuthenticationForm, redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
