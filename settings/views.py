from django.shortcuts import render

from users.decorators import login_required


@login_required
def index(request, user):
    return render(request, 'settings/index.html')
