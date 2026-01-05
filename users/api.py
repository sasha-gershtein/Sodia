from api.decorators import api_view

@api_view
def login(request, data):
    return "Hello world!"
