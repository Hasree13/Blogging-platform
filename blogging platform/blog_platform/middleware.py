from django.shortcuts import redirect

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        allowed_paths = ['/login', '/login/', '/register', '/register/']

        # allow static files also
        if request.path.startswith('/static/'):
            return self.get_response(request)

        # allow login/register
        if request.path in allowed_paths:
            return self.get_response(request)

        # allow root redirect
        if request.path == '/':
            return redirect('/login')
        
        # check session
        if not request.session.get('user_id'):
            return redirect(f'/login?next={request.path}')

        return self.get_response(request)