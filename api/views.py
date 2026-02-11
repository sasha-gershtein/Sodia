from django.views.defaults import page_not_found
from django.http import Http404
from django.urls import reverse

from .errors import ErrorResponse, NotFoundError


def api_root_404(_request):
    raise Http404


def handle404(request, exception):
    if request.path.startswith(reverse('api:root')):
        return ErrorResponse(NotFoundError())
    return page_not_found(request, exception)
