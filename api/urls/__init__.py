from django.urls import path, include

from api.views import api_root_404

app_name = 'api'

urlpatterns = [
    path('', api_root_404, name='root'),
    path('users/', include('api.urls.users', namespace='users')),
    path('settings/', include('api.urls.settings', namespace='settings')),
]
