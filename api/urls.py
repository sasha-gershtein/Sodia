from django.urls import path
from django.http import Http404

import users.api


def api_root_404(_request):
    raise Http404


app_name = 'api'

urlpatterns = [
    path('', api_root_404, name='root'),
    path('login', users.api.login, name='login'),
]
