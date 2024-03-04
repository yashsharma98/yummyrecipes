from django.middleware.common import MiddlewareMixin
from django.http import HttpResponsePermanentRedirect

class TrailingSlashMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.path.endswith('/'):
            return HttpResponsePermanentRedirect(request.path + '/')

