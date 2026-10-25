from django.contrib import admin
from django.urls import include, path
from alphamain.views import feed_view

urlpatterns = [
    path('', feed_view, name='home'),
    path('admin/', admin.site.urls),
    path('v1/', include('alphamain.urls')),
]
