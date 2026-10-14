from django.db.models import Sum
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.mixins import TenantQuerySetMixin
from apps.core.pdf import resposta_pdf
from apps.locacao.models import Cobranca, Repasse, StatusCobranca, StatusRepasse
from apps.locacao.serializers import (
    BaixaCobrancaSerializer,
    CobrancaSerializer,
    EventoCobrancaSerializer,
    GeracaoCobrancaSerializer,
    InadimplenciaSerializer,
    LiquidacaoRepasseSerializer,
    RepasseSerializer,
    RetencaoSerializer,
)
from apps.locacao.services import (
    RegraDeNegocio,
    adicionar_retencao,
    baixar_cobranca,
    gerar_cobrancas_do_contrato,
    indicadores_de_inadimplencia,
    liquidar_repasse,
)


class CobrancaFilter(filters.FilterSet):
    competencia = filters.CharFilter(method="filtrar_competencia")
    vencimento_de = filters.DateFilter(field_name="vencimento", lookup_expr="gte")
    vencimento_ate = filters.DateFilter(field_name="vencimento", lookup_expr="lte")
    em_atraso = filters.BooleanFilter(method="filtrar_em_atraso")

    class Meta:
        model = Cobranca
        fields = ["status", "contrato"]

    def filtrar_competencia(self, queryset, nome, valor):
        """Aceita `2026-08` além da data completa é como o usuário pensa."""
        try:
            ano, mes = valor.split("-")[:2]
            return queryset.filter(competencia__year=int(ano), competencia__month=int(mes))
        except (ValueError, TypeError):
            return queryset.none()

    def filtrar_em_atraso(self, queryset, nome, valor):
        atrasadas = queryset.filter(
            status__in=[StatusCobranca.ABERTA, StatusCobranca.ATRASADA],
            vencimento__lt=timezone.localdate(),
        )
        return atrasadas if valor else queryset.exclude(pk__in=atrasadas.values("pk"))


class CobrancaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Cobranca.objects.select_related(
        "contrato", "contrato__imovel"
    ).prefetch_related("contrato__partes__pessoa")
    serializer_class = CobrancaSerializer
    # Sem isto, /cobrancas/conciliar/ casaria com a rota de detalhe (pk=
    # "conciliar") e responderia 405 em vez de conciliar o arquivo.
    lookup_value_regex = "[0-9a-f-]{36}"
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CobrancaFilter

    @extend_schema(request=BaixaCobrancaSerializer, responses=CobrancaSerializer)
    @action(detail=True, methods=["post"])
    def baixar(self, request, pk=None):
        """Recebimento manual a conciliação automática usa o mesmo serviço."""

        cobranca = self.get_object()
        serializer = BaixaCobrancaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            baixar_cobranca(
                cobranca,
                serializer.validated_data["valor_pago"],
                data_pagamento=serializer.validated_data.get("data"),
                forma=serializer.validated_data.get("forma", ""),
                request=request,
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro

        return Response(CobrancaSerializer(cobranca).data)

    @extend_schema(
        request=GeracaoCobrancaSerializer, responses=CobrancaSerializer(many=True)
    )
    @action(
        detail=False, methods=["post"], url_path=r"gerar/(?P<contrato_id>[0-9a-f-]{36})"
    )
    def gerar(self, request, contrato_id=None):
        from apps.contratos.models import Contrato, StatusContrato

        contrato = Contrato.objects.filter(
            pk=contrato_id, tenant=request.user.tenant, status=StatusContrato.ATIVO
        ).first()
        if not contrato:
            raise ValidationError({"contrato": "Contrato ativo não encontrado."})

        serializer = GeracaoCobrancaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        geradas = gerar_cobrancas_do_contrato(
            contrato,
            meses=serializer.validated_data["meses"],
            a_partir_de=serializer.validated_data.get("a_partir_de"),
        )
        return Response(CobrancaSerializer(geradas, many=True).data, status=201)

    @extend_schema(responses=EventoCobrancaSerializer(many=True))
    @action(detail=True, methods=["get"])
    def eventos(self, request, pk=None):
        cobranca = self.get_object()
        return Response(EventoCobrancaSerializer(cobranca.eventos.all(), many=True).data)

    @extend_schema(responses=InadimplenciaSerializer)
    @action(detail=False, methods=["get"])
    def inadimplencia(self, request):
        competencia = None
        if bruto := request.query_params.get("competencia"):
            from datetime import date

            try:
                ano, mes = bruto.split("-")[:2]
                competencia = date(int(ano), int(mes), 1)
            except (ValueError, TypeError) as erro:
                raise ValidationError({"competencia": "Use AAAA-MM."}) from erro

        return Response(indicadores_de_inadimplencia(request.user.tenant, competencia))


class RepasseViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Repasse.objects.select_related(
        "contrato", "contrato__imovel", "contrato__imovel__proprietario", "cobranca"
    )
    serializer_class = RepasseSerializer
    filterset_fields = ["status", "contrato"]

    @extend_schema(request=LiquidacaoRepasseSerializer, responses=RepasseSerializer)
    @action(detail=True, methods=["post"])
    def liquidar(self, request, pk=None):
        repasse = self.get_object()
        serializer = LiquidacaoRepasseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            liquidar_repasse(
                repasse,
                data_pagamento=serializer.validated_data.get("data"),
                request=request,
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro

        return Response(RepasseSerializer(repasse).data)

    @extend_schema(request=RetencaoSerializer, responses=RepasseSerializer)
    @action(detail=True, methods=["post"])
    def retencoes(self, request, pk=None):
        repasse = self.get_object()
        serializer = RetencaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            adicionar_retencao(
                repasse,
                serializer.validated_data["descricao"],
                serializer.validated_data["valor"],
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"retencoes": str(erro)}) from erro

        return Response(RepasseSerializer(repasse).data)

    @extend_schema(responses={200: None})
    @action(detail=True, methods=["get"])
    def extrato(self, request, pk=None):
        """Extrato do proprietário em PDF o documento que ele cobra todo mês."""

        repasse = self.get_object()
        return resposta_pdf(
            "pdf/extrato_repasse.html",
            {
                "repasse": repasse,
                "contrato": repasse.contrato,
                "cobranca": repasse.cobranca,
                "tenant": repasse.tenant,
                "proprietario": repasse.contrato.imovel.proprietario,
                "emitido_em": timezone.now(),
            },
            nome_arquivo=f"extrato-{repasse.competencia:%Y-%m}.pdf",
            base_url=request.build_absolute_uri("/"),
        )

    @extend_schema(responses=RepasseSerializer(many=True))
    @action(detail=False, methods=["get"])
    def a_pagar(self, request):
        """Fila do financeiro: repasses liberados e ainda não pagos."""

        pendentes = self.filter_queryset(
            self.get_queryset().filter(status=StatusRepasse.PENDENTE)
        )
        total = pendentes.aggregate(total=Sum("valor_liquido"))["total"] or 0
        return Response(
            {
                "total_a_pagar": total,
                "quantidade": pendentes.count(),
                "repasses": RepasseSerializer(pendentes, many=True).data,
            }
        )
