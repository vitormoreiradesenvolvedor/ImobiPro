from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Papel, Tenant
from apps.core.mixins import TenantQuerySetMixin
from apps.integracoes.models import EventoIntegracao, IntegracaoPortal, StatusEnvio
from apps.integracoes.services import (
    RegraDeNegocio,
    assinatura_valida,
    integracao_do_portal,
    processar_lead_de_portal,
    registrar_evento,
    sincronizar_portal,
)


class IntegracaoPortalSerializer(serializers.ModelSerializer):
    portal_display = serializers.CharField(source="get_portal_display", read_only=True)
    url_webhook = serializers.SerializerMethodField()

    class Meta:
        model = IntegracaoPortal
        fields = [
            "id",
            "portal",
            "portal_display",
            "ativo",
            "identificador_externo",
            "segredo_webhook",
            "url_webhook",
            "ultima_sincronizacao",
            "total_publicados",
        ]
        read_only_fields = ["id", "ultima_sincronizacao", "total_publicados"]
        extra_kwargs = {"segredo_webhook": {"read_only": True}}

    def get_url_webhook(self, integracao):
        requisicao = self.context.get("request")
        caminho = (
            f"/api/v1/leads/webhook/{integracao.portal}/{integracao.tenant.subdominio}/"
        )
        return requisicao.build_absolute_uri(caminho) if requisicao else caminho


class EventoIntegracaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoIntegracao
        fields = [
            "id",
            "portal",
            "direcao",
            "evento",
            "status",
            "tentativas",
            "erro",
            "referencia",
            "criado_em",
        ]


class IntegracaoPortalViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Configuração das integrações (tela de Configurações)."""

    queryset = IntegracaoPortal.objects.all()
    serializer_class = IntegracaoPortalSerializer
    filterset_fields = ["portal", "ativo"]

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated

        return [IsAuthenticated()]

    def _exigir_admin(self, request):
        if request.user.papel not in {Papel.ADMIN, Papel.SUPERADMIN}:
            raise ValidationError({"detail": "Só o administrador configura integrações."})

    def perform_create(self, serializer):
        self._exigir_admin(self.request)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._exigir_admin(self.request)
        serializer.save()

    @extend_schema(request=None, responses=IntegracaoPortalSerializer)
    @action(detail=True, methods=["post"])
    def sincronizar(self, request, pk=None):
        integracao = self.get_object()
        enfileirados = sincronizar_portal(integracao)
        return Response(
            {
                **IntegracaoPortalSerializer(integracao, context={"request": request}).data,
                "enfileirados": enfileirados,
            }
        )

    @extend_schema(request=None, responses=IntegracaoPortalSerializer)
    @action(detail=True, methods=["post"], url_path="rotacionar-segredo")
    def rotacionar_segredo(self, request, pk=None):
        """Vazou o segredo? Gera outro e invalida o anterior na hora."""

        self._exigir_admin(request)
        from apps.integracoes.models import gerar_segredo

        integracao = self.get_object()
        integracao.segredo_webhook = gerar_segredo()
        integracao.save(update_fields=["segredo_webhook"])
        return Response(
            IntegracaoPortalSerializer(integracao, context={"request": request}).data
        )


class EventoIntegracaoViewSet(
    TenantQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Painel de reprocessamento o antídoto para portal instável."""

    queryset = EventoIntegracao.objects.all()
    serializer_class = EventoIntegracaoSerializer
    filterset_fields = ["status", "portal", "direcao", "evento"]

    @extend_schema(request=None, responses=EventoIntegracaoSerializer)
    @action(detail=True, methods=["post"])
    def reprocessar(self, request, pk=None):
        evento = self.get_object()
        if evento.status == StatusEnvio.ENVIADO:
            raise ValidationError({"status": "Este evento já foi processado."})

        from apps.integracoes.tasks import despachar_evento

        evento.status = StatusEnvio.PENDENTE
        evento.erro = ""
        evento.save(update_fields=["status", "erro"])
        despachar_evento.delay(str(evento.pk))

        return Response(EventoIntegracaoSerializer(evento).data)


@extend_schema(request=None, responses={202: None})
class WebhookLeadView(APIView):
    """POST /api/v1/leads/webhook/{portal}/{subdominio}/ entrada de portal.

    Sem JWT: a autenticidade vem da assinatura HMAC no cabeçalho
    `X-Assinatura`, conferida contra o segredo daquela integração.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "webhook_portal"

    def post(self, request, portal, subdominio):
        tenant = Tenant.objects.filter(subdominio=subdominio, ativo=True).first()
        if not tenant:
            return Response(status=status.HTTP_404_NOT_FOUND)

        integracao = integracao_do_portal(tenant, portal)
        if not integracao:
            return Response(
                {
                    "detail": "Integração não configurada.",
                    "code": "sem_integracao",
                    "campos": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        assinatura = request.headers.get("X-Assinatura", "")
        if not assinatura_valida(request.body, assinatura, integracao.segredo_webhook):
            registrar_evento(
                tenant,
                "assinatura_invalida",
                {"portal": portal},
                portal=portal,
                status=StatusEnvio.DESCARTADO,
            )
            return Response(
                {
                    "detail": "Assinatura inválida.",
                    "code": "assinatura_invalida",
                    "campos": {},
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            processar_lead_de_portal(tenant, portal, request.data)
        except RegraDeNegocio as erro:
            registrar_evento(
                tenant,
                "lead_descartado",
                request.data,
                portal=portal,
                status=StatusEnvio.DESCARTADO,
            )
            return Response(
                {"detail": str(erro), "code": "payload_invalido", "campos": {}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_202_ACCEPTED)
