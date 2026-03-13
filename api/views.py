from django.http import Http404


def api_root_404(_request):
    raise Http404()
