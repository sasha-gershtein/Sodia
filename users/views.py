from django.shortcuts import render
from django.views import View


class Home(View):
    def get(self, request):
        return render(request, 'users/unauthorised.html')

class Auth(View):  # temp debug view
    def get(self, request):
        return render(request, 'users/auth_base.html')