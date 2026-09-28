from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Sonda usada pelo Docker Compose, pelo Nginx e pelo pipeline.

    Só aceita GET: sonda não altera estado, então não há por que expor outros
    métodos nem abrir exceção de CSRF.
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        banco = "ok"
        status = 200
    except Exception:  # pragma: no cover - caminho de indisponibilidade
        banco = "erro"
        status = 503

    return JsonResponse(
        {"status": "ok" if status == 200 else "degradado", "banco": banco}, status=status
    )
