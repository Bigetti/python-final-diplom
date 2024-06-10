from django.contrib import admin
from django.urls import path, include
from backend.views import HomeView  # Импортируйте ваше представление HomeView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('backend.urls', namespace='backend')),
    path('', HomeView.as_view(), name='home'),  # Маршрут для пустого пути
]