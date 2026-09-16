from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.mixins import TenantQuerySetMixin
from apps.notificacoes.models import Notificacao


class NotificacaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Notificacao
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "titulo",
            "descricao",
            "dados",
            "lida",
            "criado_em",
        ]


class ContadorSerializer(serializers.Serializer):
    nao_lidas = serializers.IntegerField()


class NotificacaoViewSet(
    TenantQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Sino do topo da tela. Cada usuário só vê as próprias notificações."""

    queryset = Notificacao.objects.all()
    serializer_class = NotificacaoSerializer
    filterset_fields = ["lida", "tipo"]

    def get_queryset(self):
        return super().get_queryset().filter(usuario=self.request.user)

    @extend_schema(request=None, responses=NotificacaoSerializer)
    @action(detail=True, methods=["post"])
    def marcar_lida(self, request, pk=None):
        notificacao = self.get_object()
        notificacao.lida = True
        notificacao.lida_em = timezone.now()
        notificacao.save(update_fields=["lida", "lida_em"])
        return Response(self.get_serializer(notificacao).data)

    @extend_schema(request=None, responses=ContadorSerializer)
    @action(detail=False, methods=["post"], url_path="marcar-todas-lidas")
    def marcar_todas_lidas(self, request):
        self.get_queryset().filter(lida=False).update(lida=True, lida_em=timezone.now())
        return Response({"nao_lidas": 0})

    @extend_schema(responses=ContadorSerializer)
    @action(detail=False, methods=["get"], url_path="nao-lidas")
    def nao_lidas(self, request):
        return Response({"nao_lidas": self.get_queryset().filter(lida=False).count()})
