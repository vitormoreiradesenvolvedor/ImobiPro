from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AcessoAoPainel
from apps.onboarding.services import avaliar, concluir_tour, definir_dispensa, reiniciar


class PertenceAImobiliaria(BasePermission):
    """O guia mede a operação de uma imobiliária.

    O operador da plataforma (superadmin sem tenant) não tem missões: sem esta
    guarda, o progresso seria criado sem imobiliária e estouraria no banco.
    """

    message = "Este usuário não pertence a uma imobiliária."

    def has_permission(self, request, view):
        return bool(getattr(request.user, "tenant_id", None))


class MissaoSerializer(serializers.Serializer):
    chave = serializers.CharField()
    titulo = serializers.CharField()
    descricao = serializers.CharField()
    dica = serializers.CharField()
    trilha = serializers.CharField()
    trilha_nome = serializers.CharField()
    trilha_icone = serializers.CharField()
    rota = serializers.CharField()
    pontos = serializers.IntegerField()
    concluida = serializers.BooleanField()
    proxima = serializers.BooleanField()


class TrilhaSerializer(serializers.Serializer):
    chave = serializers.CharField()
    nome = serializers.CharField()
    icone = serializers.CharField()
    total = serializers.IntegerField()
    concluidas = serializers.IntegerField()


class ProgressoSerializer(serializers.Serializer):
    missoes = MissaoSerializer(many=True)
    trilhas = TrilhaSerializer(many=True)
    concluidas = serializers.IntegerField()
    total = serializers.IntegerField()
    pontos = serializers.IntegerField()
    total_pontos = serializers.IntegerField()
    percentual = serializers.IntegerField()
    nivel = serializers.CharField()
    proxima_missao = serializers.CharField(allow_null=True)
    tours_concluidos = serializers.ListField(child=serializers.CharField())
    dispensado = serializers.BooleanField()
    concluido = serializers.BooleanField()


class DispensaSerializer(serializers.Serializer):
    dispensado = serializers.BooleanField(default=True)


@extend_schema(responses=ProgressoSerializer)
class ProgressoOnboardingView(APIView):
    """GET /api/v1/onboarding/ missões conferidas contra os dados reais."""

    permission_classes = [AcessoAoPainel, PertenceAImobiliaria]
    serializer_class = ProgressoSerializer

    def get(self, request):
        return Response(avaliar(request.user))


@extend_schema(request=None, responses=ProgressoSerializer)
class ConcluirTourView(APIView):
    """Marca um tour guiado como visto, para não reabrir sozinho."""

    permission_classes = [AcessoAoPainel, PertenceAImobiliaria]

    def post(self, request, identificador):
        concluir_tour(request.user, identificador)
        return Response(avaliar(request.user))


@extend_schema(request=DispensaSerializer, responses=ProgressoSerializer)
class DispensarView(APIView):
    permission_classes = [AcessoAoPainel, PertenceAImobiliaria]
    serializer_class = DispensaSerializer

    def post(self, request):
        serializer = DispensaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        definir_dispensa(request.user, serializer.validated_data["dispensado"])
        return Response(avaliar(request.user))


@extend_schema(request=None, responses=ProgressoSerializer)
class ReiniciarView(APIView):
    """Reabre o guia do zero. Não apaga nada da operação."""

    permission_classes = [AcessoAoPainel, PertenceAImobiliaria]

    def post(self, request):
        reiniciar(request.user)
        return Response(avaliar(request.user), status=status.HTTP_200_OK)
