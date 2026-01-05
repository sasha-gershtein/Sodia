from django.views.defaults import page_not_found

from .errors import ErrorResponse, NotFoundError

def handle404(request, exception):
    if request.path.startswith('/api/'):
        return ErrorResponse(NotFoundError())
    return page_not_found(request, exception)
