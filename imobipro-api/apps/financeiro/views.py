from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Papel
from apps.accounts.permissions import AcessoAoPainel
from apps.core.mixins import TenantQuerySetMixin
from apps.financeiro.models import Transacao
from apps.financeiro.permissions import PodeVerFinanceiro
from apps.financeiro.serializers import (
    ConciliacaoSerializer,
    DesempenhoCorretorSerializer,
    DreSerializer,
    EstornoSerializer,
    ResultadoConciliacaoSerializer,
    TransacaoSerializer,
)
from apps.financeiro.services import (
    RegraDeNegocio,
    conciliar_retorno_cnab,
    contas_a_pagar,
    contas_a_receber,
    dre,
    estornar,
    fluxo_mensal,
)


class TransacaoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Transacao.objects.select_related("contrato", "criado_por")
    serializer_class = TransacaoSerializer
    permission_classes = [AcessoAoPainel, PodeVerFinanceiro]
    filterset_fields = ["tipo", "categoria", "contrato"]

    def perform_destroy(self, instance):
        raise ValidationError(
            {"detail": "Transação não é excluída. Use o estorno para reverter."}
        )

    @extend_schema(request=EstornoSerializer, responses=TransacaoSerializer)
    @action(detail=True, methods=["post"])
    def estornar(self, request, pk=None):
        transacao = self.get_object()
        serializer = EstornoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            estorno = estornar(
                transacao, serializer.validated_data["motivo"], request=request
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"estorno": str(erro)}) from erro

        return Response(TransacaoSerializer(estorno).data, status=201)


class RelatoriosView(APIView):
    """DRE, fluxo de caixa e desempenho a aba Relatórios do painel."""

    permission_classes = [AcessoAoPainel, PodeVerFinanceiro]

    @extend_schema(responses=DreSerializer)
    def get(self, request, relatorio):
        tenant = request.user.tenant

        if relatorio == "dre":
            inicio, fim = self._periodo(request)
            return Response(dre(tenant, inicio, fim))

        if relatorio == "fluxo":
            return Response(fluxo_mensal(tenant))

        if relatorio == "desempenho-corretores":
            return Response(self._desempenho(tenant))

        if relatorio == "contas-a-receber":
            cobrancas = contas_a_receber(tenant)
            return Response(
                {
                    "quantidade": cobrancas.count(),
                    "total": cobrancas.aggregate(t=Sum("valor_total"))["t"] or 0,
                    "vencidas": cobrancas.filter(
                        vencimento__lt=timezone.localdate()
                    ).count(),
                }
            )

        if relatorio == "contas-a-pagar":
            dados = contas_a_pagar(tenant)
            return Response(
                {
                    "total": dados["total"],
                    "repasses": dados["repasses"].count(),
                    "comissoes": dados["comissoes"].count(),
                }
            )

        raise ValidationError({"relatorio": f"Relatório '{relatorio}' não existe."})

    def _periodo(self, request):
        hoje = timezone.localdate()
        padrao_inicio = hoje.replace(day=1)
        try:
            inicio = (
                date.fromisoformat(request.query_params["inicio"])
                if "inicio" in request.query_params
                else padrao_inicio
            )
            fim = (
                date.fromisoformat(request.query_params["fim"])
                if "fim" in request.query_params
                else hoje
            )
        except ValueError as erro:
            raise ValidationError({"periodo": "Use datas no formato AAAA-MM-DD."}) from erro

        if fim < inicio:
            raise ValidationError({"fim": "O fim do período é anterior ao início."})
        return inicio, fim

    @extend_schema(responses=DesempenhoCorretorSerializer(many=True))
    def _desempenho(self, tenant):
        from apps.accounts.models import Usuario
        from apps.contratos.models import StatusComissao

        corretores = (
            Usuario.objects.filter(tenant=tenant, papel=Papel.CORRETOR)
            .annotate(
                total_leads=Count("leads", distinct=True),
                ganhos=Count(
                    "leads", filter=Q(leads__estagio="FECHADO_GANHO"), distinct=True
                ),
                captados=Count("imoveis_captados", distinct=True),
                comissao_prevista=Sum(
                    "comissoes__valor",
                    filter=Q(comissoes__status=StatusComissao.PREVISTA),
                ),
                comissao_paga=Sum(
                    "comissoes__valor", filter=Q(comissoes__status=StatusComissao.PAGA)
                ),
            )
            .order_by("-ganhos")
        )

        return [
            {
                "corretor": corretor.nome_completo,
                "leads": corretor.total_leads,
                "ganhos": corretor.ganhos,
                "conversao": (
                    round(corretor.ganhos / corretor.total_leads * 100, 2)
                    if corretor.total_leads
                    else 0.0
                ),
                "imoveis_captados": corretor.captados,
                "contratos": corretor.ganhos,
                "comissao_prevista": corretor.comissao_prevista or 0,
                "comissao_paga": corretor.comissao_paga or 0,
            }
            for corretor in corretores
        ]


class ConciliacaoView(APIView):
    """POST /api/v1/cobrancas/conciliar/ upload do arquivo de retorno."""

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ConciliacaoSerializer
    permission_classes = [AcessoAoPainel, PodeVerFinanceiro]

    @extend_schema(request=ConciliacaoSerializer, responses=ResultadoConciliacaoSerializer)
    def post(self, request):
        serializer = ConciliacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        arquivo = serializer.validated_data["arquivo"]
        if arquivo.size > 5 * 1024 * 1024:
            raise ValidationError({"arquivo": "Arquivo maior que 5 MB."})

        conteudo = arquivo.read().decode("latin-1", errors="ignore")
        return Response(
            conciliar_retorno_cnab(conteudo, request.user.tenant, request=request)
        )


class ResumoFinanceiroView(APIView):
    """Bloco financeiro do dashboard, em uma requisição só."""

    permission_classes = [AcessoAoPainel, PodeVerFinanceiro]

    def get(self, request):
        from apps.locacao.services import indicadores_de_inadimplencia

        tenant = request.user.tenant
        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)

        resultado = dre(tenant, inicio_mes, hoje)
        receber = contas_a_receber(tenant)
        pagar = contas_a_pagar(tenant)

        return Response(
            {
                "receita_do_mes": resultado["receita_operacional"],
                "despesa_do_mes": resultado["despesa_operacional"],
                "resultado_do_mes": resultado["resultado"],
                "a_receber": receber.aggregate(t=Sum("valor_total"))["t"] or 0,
                "a_receber_vencido": receber.filter(vencimento__lt=hoje).aggregate(
                    t=Sum("valor_total")
                )["t"]
                or 0,
                "a_pagar": pagar["total"],
                "inadimplencia": indicadores_de_inadimplencia(tenant),
                "proximos_7_dias": receber.filter(
                    vencimento__gte=hoje, vencimento__lte=hoje + timedelta(days=7)
                ).count(),
            }
        )
