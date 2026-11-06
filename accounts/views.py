from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Власний обробник 403 зі зрозумілою сторінкою."""
    return render(request, "403.html", status=403)
