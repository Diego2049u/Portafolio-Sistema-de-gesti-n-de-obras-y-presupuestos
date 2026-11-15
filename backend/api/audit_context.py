from contextvars import ContextVar

from django.utils.deprecation import MiddlewareMixin


_current_request = ContextVar('fyag_audit_request', default=None)


def get_current_request():
    return _current_request.get()


class AuditContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._fyag_audit_context_token = _current_request.set(request)

    def process_response(self, request, response):
        token = getattr(request, '_fyag_audit_context_token', None)
        if token is not None:
            _current_request.reset(token)
            request._fyag_audit_context_token = None
        return response

    def process_exception(self, request, exception):
        token = getattr(request, '_fyag_audit_context_token', None)
        if token is not None:
            _current_request.reset(token)
            request._fyag_audit_context_token = None
        return None
