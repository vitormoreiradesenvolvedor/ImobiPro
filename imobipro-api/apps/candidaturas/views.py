"""Candidaturas: a equipe analisa por aqui, o pretendente envia pelo link."""

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import AcessoAoPainel
from apps.candidaturas.models import Candidatura, StatusCandidatura
from apps.candidaturas.serializers import (
    AberturaCandidaturaSerializer,
    CandidaturaDetailSerializer,
    CandidaturaListSerializer,
    ConferenciaSerializer,
    DecisaoSerializer,
    DocumentoSerializer,
    EnvioDocumentoSerializer,
    GeracaoContratoSerializer,
    PortalCandidaturaSerializer,
)
from apps.candidaturas.services import (
    RegraDeNegocio,
    abrir_candidatura,
    anexar_documento,
    aprovar,
    conferir_documento,
    gerar_contrato,
    mover_status,
)
from apps.core.mixins import TenantQuerySetMixin


class CandidaturaViewSet(
    TenantQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Esteira de análise: da papelada à aprovação."""

    queryset = Candidatura.objects.select_related(
        "imovel", "analista", "contrato", "pessoa"
    ).prefetch_related("documentos__conferido_por", "eventos__usuario")
    permission_classes = [AcessoAoPainel]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "analista", "imovel"]
    search_fields = ["protocolo", "pretendente_nome", "pretendente_cpf"]
    ordering_fields = ["criado_em"]

    def get_serializer_class(self):
        if self.action == "list":
            return CandidaturaListSerializer
        return CandidaturaDetailSerializer

    def _resposta(self, candidatura):
        atual = self.get_queryset().get(pk=candidatura.pk)
        return Response(
            CandidaturaDetailSerializer(atual, context=self.get_serializer_context()).data
        )

    @extend_schema(
        request=AberturaCandidaturaSerializer, responses=CandidaturaDetailSerializer
    )
    def create(self, request):
        from apps.atendimento.models import Ticket
        from apps.imoveis.models import Imovel

        serializer = AberturaCandidaturaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = dict(serializer.validated_data)

        imovel = Imovel.objects.filter(
            pk=dados.pop("imovel"), tenant=request.user.tenant
        ).first()
        if not imovel:
            raise ValidationError({"imovel": "Imóvel não encontrado."})

        ticket = None
        if identificador := dados.pop("ticket", None):
            ticket = Ticket.objects.filter(
                pk=identificador, tenant=request.user.tenant
            ).first()

        try:
            candidatura = abrir_candidatura(
                dados, request.user.tenant, imovel, ticket=ticket, usuario=request.user
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"imovel": str(erro)}) from erro

        return Response(
            CandidaturaDetailSerializer(
                candidatura, context=self.get_serializer_context()
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ConferenciaSerializer, responses=CandidaturaDetailSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"documentos/(?P<documento_id>[0-9a-f-]{36})/conferir",
    )
    def conferir(self, request, pk=None, documento_id=None):
        candidatura = self.get_object()
        documento = candidatura.documentos.filter(pk=documento_id).first()
        if not documento:
            raise ValidationError({"documento": "Documento não encontrado."})

        serializer = ConferenciaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            conferir_documento(
                documento,
                serializer.validated_data["aprovado"],
                usuario=request.user,
                observacao=serializer.validated_data.get("observacao", ""),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"observacao": str(erro)}) from erro

        return self._resposta(candidatura)

    @extend_schema(request=DecisaoSerializer, responses=CandidaturaDetailSerializer)
    @action(detail=True, methods=["patch"])
    def situacao(self, request, pk=None):
        candidatura = self.get_object()
        serializer = DecisaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            if dados["status"] == StatusCandidatura.APROVADA:
                aprovar(
                    candidatura,
                    usuario=request.user,
                    observacao=dados.get("observacao", ""),
                )
            else:
                mover_status(
                    candidatura,
                    dados["status"],
                    usuario=request.user,
                    observacao=dados.get("observacao", ""),
                )
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro

        return self._resposta(candidatura)

    @extend_schema(request=GeracaoContratoSerializer, responses=CandidaturaDetailSerializer)
    @action(detail=True, methods=["post"], url_path="gerar-contrato")
    def gerar_contrato(self, request, pk=None):
        candidatura = self.get_object()
        serializer = GeracaoContratoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            gerar_contrato(
                candidatura,
                dict(serializer.validated_data),
                usuario=request.user,
                request=request,
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"contrato": str(erro)}) from erro

        return self._resposta(candidatura)

    @extend_schema(responses=CandidaturaListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def painel(self, request):
        """Onde a esteira está travada agora."""

        base = self.filter_queryset(self.get_queryset())
        return Response(
            {
                "aguardando_documentos": base.filter(
                    status=StatusCandidatura.RASCUNHO
                ).count(),
                "em_analise": base.filter(status=StatusCandidatura.EM_ANALISE).count(),
                "com_pendencia": base.filter(status=StatusCandidatura.PENDENTE).count(),
                "aprovadas_sem_contrato": base.filter(
                    status=StatusCandidatura.APROVADA, contrato__isnull=True
                ).count(),
            }
        )


class PortalCandidaturaView(APIView):
    """GET/POST /api/v1/public/{subdominio}/candidatura/{token}/

    O pretendente não tem conta: o token do link é a credencial. Ele é longo e
    aleatório justamente porque abre dado pessoal.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "acompanhamento_publico"
    parser_classes = [MultiPartParser, FormParser]

    def _buscar(self, subdominio, token):
        return (
            Candidatura.objects.filter(tenant__subdominio=subdominio, token=token)
            .select_related("imovel")
            .prefetch_related("documentos", "eventos")
            .first()
        )

    @extend_schema(responses=PortalCandidaturaSerializer)
    def get(self, request, subdominio, token):
        candidatura = self._buscar(subdominio, token)
        if not candidatura:
            return Response(
                {"detail": "Link inválido.", "code": "nao_encontrado", "campos": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PortalCandidaturaSerializer(candidatura).data)

    @extend_schema(request=EnvioDocumentoSerializer, responses={201: DocumentoSerializer})
    def post(self, request, subdominio, token):
        candidatura = self._buscar(subdominio, token)
        if not candidatura:
            return Response(
                {"detail": "Link inválido.", "code": "nao_encontrado", "campos": {}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = EnvioDocumentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arquivo = serializer.validated_data["arquivo"]

        try:
            documento = anexar_documento(
                candidatura,
                serializer.validated_data["tipo"],
                arquivo,
                nome_original=getattr(arquivo, "name", ""),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"arquivo": str(erro)}) from erro

        return Response(DocumentoSerializer(documento).data, status=status.HTTP_201_CREATED)
