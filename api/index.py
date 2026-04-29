from server import app

def handler(request):
    return app(request)