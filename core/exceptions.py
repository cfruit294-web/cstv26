from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    """Uniformise le format des erreurs API : {"detail": ..., "errors": {...}}."""
    response = drf_exception_handler(exc, context)

    if response is None:
        return response

    if isinstance(response.data, dict) and 'detail' in response.data and len(response.data) == 1:
        return response

    detail = response.data.pop('detail', None) if isinstance(response.data, dict) else None
    response.data = {
        'detail': detail or 'Une erreur de validation est survenue.',
        'errors': response.data,
    }
    return response
