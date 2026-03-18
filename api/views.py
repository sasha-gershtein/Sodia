"""This file defines the view to raise a 404 error on request to /api/
(defined for pattern matching to determine if a path is of an api endpoint)"""

from django.http import Http404


def api_root_404(_request):
    """Return 404 error on request to /api/"""
    raise Http404()
