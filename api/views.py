from django.views.defaults import page_not_found
from django.urls import reverse

from .errors import ErrorResponse, NotFoundError

def handle404(request, exception):
    if request.path.startswith(reverse('api:root')):
        return ErrorResponse(NotFoundError())
    return page_not_found(request, exception)
