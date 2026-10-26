"""Atendimento: o site abre o ticket, a equipe trabalha o ticket."""

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AcessoAoPainel
from apps.atendimento.models import STATUS_ENCERRADOS, StatusTicket, Ticket
from apps.atendimento.serializers import (
    AberturaTicketSerializer,
    AcompanhamentoSerializer,
    MudancaStatusTicketSerializer,
    ReatribuicaoSerializer,
    RespostaSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
)
from apps.atendimento.services import (
    RegraDeNegocio,
    abrir_ticket,
    mover_status,
    reatribuir,
    responder,
)
from apps.core.mixins import TenantQuerySetMixin


class TicketViewSet(
    TenantQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Fila de atendimento da imobiliária."""

    queryset = Ticket.objects.select_related("imovel", "analista", "lead").prefetch_related(
        "eventos__usuario"
    )
    permission_classes = [AcessoAoPainel]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "tipo", "analista", "imovel"]
    search_fields = ["protocolo", "solicitante_nome", "solicitante_telefone"]
    ordering_fields = ["criado_em", "agendado_para"]

    def get_serializer_class(self):
        return TicketListSerializer if self.action == "list" else TicketDetailSerializer

    def _resposta(self, ticket):
        atual = self.get_queryset().get(pk=ticket.pk)
        return Response(
            TicketDetailSerializer(atual, context=self.get_serializer_context()).data
        )

    @extend_schema(request=RespostaSerializer, responses=TicketDetailSerializer)
    @action(detail=True, methods=["post"])
    def responder(self, request, pk=None):
        ticket = self.get_object()
        serializer = RespostaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            responder(
                ticket,
                serializer.validated_data["mensagem"],
                usuario=request.user,
                visivel_ao_cliente=serializer.validated_data["visivel_ao_cliente"],
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"mensagem": str(erro)}) from erro

        return self._resposta(ticket)

    @extend_schema(request=MudancaStatusTicketSerializer, responses=TicketDetailSerializer)
    @action(detail=True, methods=["patch"])
    def situacao(self, request, pk=None):
        ticket = self.get_object()
        serializer = MudancaStatusTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            mover_status(
                ticket,
                dados["status"],
                usuario=request.user,
                observacao=dados.get("observacao", ""),
                agendado_para=dados.get("agendado_para"),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro

        return self._resposta(ticket)

    @extend_schema(request=ReatribuicaoSerializer, responses=TicketDetailSerializer)
    @action(detail=True, methods=["post"])
    def reatribuir(self, request, pk=None):
        from apps.accounts.models import Usuario

        ticket = self.get_object()
        serializer = ReatribuicaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        analista = Usuario.objects.filter(
            pk=serializer.validated_data["analista"], tenant=request.user.tenant
        ).first()
        if not analista:
            raise ValidationError({"analista": "Analista não encontrado na equipe."})

        try:
            reatribuir(
                ticket,
                analista,
                usuario=request.user,
                motivo=serializer.validated_data.get("motivo", ""),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"analista": str(erro)}) from erro

        return self._resposta(ticket)

    @extend_schema(responses=TicketListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def painel(self, request):
        """O que precisa de resposta agora, na ordem em que atrasa."""

        abertos = self.filter_queryset(
            self.get_queryset().exclude(status__in=STATUS_ENCERRADOS)
        )
        estourados = [ticket for ticket in abertos if ticket.sla_estourado]

        return Response(
            {
                "abertos": abertos.count(),
                "sem_resposta": abertos.filter(primeira_resposta_em__isnull=True).count(),
                "sla_estourado": len(estourados),
                "agendados_hoje": abertos.filter(
                    status=StatusTicket.AGENDADO,
                    agendado_para__date=timezone.localdate(),
                ).count(),
                "fila": TicketListSerializer(
                    abertos.order_by("primeira_resposta_em", "criado_em")[:20],
                    many=True,
                    context=self.get_serializer_context(),
                ).data,
            }
        )


class AberturaTicketPublicaView(APIView):
    """POST /api/v1/public/{subdominio}/tickets/ pedido de visita pelo site."""

    serializer_class = AberturaTicketSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "contato_publico"

    @extend_schema(
        request=AberturaTicketSerializer,
        responses={201: OpenApiResponse(description="Protocolo do atendimento")},
    )
    def post(self, request, subdominio):
        from apps.accounts.models import Tenant
        from apps.imoveis.models import Imovel

        tenant = Tenant.objects.filter(subdominio=subdominio, ativo=True).first()
        if not tenant:
            return Response(
                {
                    "detail": "Imobiliária não encontrada.",
                    "code": "nao_encontrado",
                    "campos": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AberturaTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = dict(serializer.validated_data)

        imovel = None
        if codigo := dados.pop("imovel_codigo", ""):
            imovel = Imovel.objects.filter(
                tenant=tenant, codigo=codigo, publicado_site=True
            ).first()
            if not imovel:
                raise ValidationError({"imovel_codigo": "Imóvel não está no site."})

        ticket = abrir_ticket(dados, tenant, imovel=imovel, request=request)

        return Response(
            {
                "protocolo": ticket.protocolo,
                "status": ticket.status,
                "mensagem": (
                    "Pedido registrado. Guarde o protocolo para acompanhar o atendimento."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class AcompanhamentoPublicoView(APIView):
    """GET /api/v1/public/{subdominio}/tickets/{protocolo}/ sem login.

    O protocolo sozinho não basta: pedimos também o contato usado na abertura.
    Número sequencial é fácil de adivinhar, e o histórico tem dado de pessoa.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "acompanhamento_publico"

    @extend_schema(responses=AcompanhamentoSerializer)
    def get(self, request, subdominio, protocolo):
        contato = (request.query_params.get("contato") or "").strip().lower()
        if not contato:
            raise ValidationError(
                {"contato": "Informe o telefone ou o e-mail usado no pedido."}
            )

        ticket = (
            Ticket.objects.filter(
                tenant__subdominio=subdominio, protocolo=protocolo.upper()
            )
            .select_related("imovel", "analista")
            .prefetch_related("eventos")
            .first()
        )

        somente_digitos = "".join(c for c in contato if c.isdigit())
        confere = ticket and (
            (ticket.solicitante_email and ticket.solicitante_email.lower() == contato)
            or (
                somente_digitos
                and somente_digitos
                in "".join(c for c in ticket.solicitante_telefone if c.isdigit())
            )
        )

        if not confere:
            return Response(
                {
                    "detail": "Protocolo não encontrado para este contato.",
                    "code": "nao_encontrado",
                    "campos": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(AcompanhamentoSerializer(ticket).data)
