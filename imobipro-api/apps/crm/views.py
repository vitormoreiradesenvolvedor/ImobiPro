from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import Extract
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Papel
from apps.core.mixins import TenantQuerySetMixin
from apps.crm.filters import LeadFilter, VisitaFilter
from apps.crm.models import (
    ESTAGIOS_FECHADOS,
    ORDEM_DO_FUNIL,
    EstagioLead,
    Lead,
    MotivoPerda,
    OrigemLead,
    Proposta,
    TipoInteracao,
    Visita,
)
from apps.crm.serializers import (
    AtribuicaoLeadSerializer,
    ContatoPublicoSerializer,
    EstatisticasCrmSerializer,
    FeedbackVisitaSerializer,
    InteracaoSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    MovimentacaoLeadSerializer,
    PropostaSerializer,
    RespostaPropostaSerializer,
    VisitaSerializer,
)
from apps.crm.services import (
    RegraDeNegocio,
    aceitar_proposta,
    agendar_visita,
    atribuir_lead,
    criar_lead,
    criar_proposta,
    marcar_primeiro_contato,
    mover_estagio,
    recusar_proposta,
    registrar_feedback_visita,
    registrar_interacao,
)

GESTAO = {Papel.ADMIN, Papel.GERENTE, Papel.SUPERADMIN}


class EscopoDoCorretorMixin:
    """Corretor enxerga a própria carteira; gestão enxerga a equipe inteira."""

    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user
        if usuario.papel in GESTAO:
            return queryset
        return queryset.filter(corretor=usuario)


class LeadViewSet(EscopoDoCorretorMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Lead.objects.select_related(
        "corretor", "imovel_interesse", "imovel_interesse__endereco"
    ).prefetch_related("imovel_interesse__fotos")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LeadFilter
    search_fields = ["nome", "email", "telefone"]
    ordering_fields = ["criado_em", "valor_estimado"]

    def get_serializer_class(self):
        if self.action in {"list", "funil"}:
            return LeadListSerializer
        return LeadDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            return queryset.prefetch_related("interacoes__usuario")
        return queryset

    def perform_create(self, serializer):
        dados = dict(serializer.validated_data)
        serializer.instance = criar_lead(
            dados, self.request.user.tenant, request=self.request
        )

    @extend_schema(request=MovimentacaoLeadSerializer, responses=LeadDetailSerializer)
    @action(detail=True, methods=["patch"])
    def mover(self, request, pk=None):
        """Arrastar o cartão no kanban cai aqui."""
        lead = self.get_object()
        serializer = MovimentacaoLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            mover_estagio(
                lead,
                serializer.validated_data["estagio"],
                request=request,
                motivo_perda=serializer.validated_data.get("motivo_perda", ""),
                observacao=serializer.validated_data.get("observacao", ""),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"estagio": str(erro)}) from erro

        return Response(LeadDetailSerializer(lead).data)

    @extend_schema(request=InteracaoSerializer, responses={201: InteracaoSerializer})
    @action(detail=True, methods=["post"])
    def interacoes(self, request, pk=None):
        lead = self.get_object()
        serializer = InteracaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        interacao = registrar_interacao(
            lead,
            serializer.validated_data["tipo"],
            serializer.validated_data["descricao"],
            usuario=request.user,
        )
        # Qualquer contato humano fecha o cronômetro do SLA.
        if serializer.validated_data["tipo"] != TipoInteracao.SISTEMA:
            marcar_primeiro_contato(lead)

        return Response(InteracaoSerializer(interacao).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=AtribuicaoLeadSerializer, responses=LeadDetailSerializer)
    @action(detail=True, methods=["post"])
    def atribuir(self, request, pk=None):
        if request.user.papel not in GESTAO:
            raise ValidationError({"detail": "Só a gestão redistribui leads."})

        lead = self.get_object()
        serializer = AtribuicaoLeadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.accounts.models import Usuario

        corretor = Usuario.objects.filter(
            pk=serializer.validated_data["corretor_id"],
            tenant=request.user.tenant,
            ativo=True,
        ).first()
        if not corretor:
            raise ValidationError({"corretor_id": "Corretor não encontrado."})

        atribuir_lead(lead, corretor, request=request, motivo="redistribuição manual")
        return Response(LeadDetailSerializer(lead).data)

    @extend_schema(responses=EstatisticasCrmSerializer)
    @action(detail=False, methods=["get"])
    def funil(self, request):
        """Kanban já agrupado por estágio uma requisição, não nove."""

        leads = self.filter_queryset(self.get_queryset()).exclude(
            estagio__in=ESTAGIOS_FECHADOS
        )
        agrupado = {estagio: [] for estagio in ORDEM_DO_FUNIL}
        for lead in leads:
            agrupado.setdefault(lead.estagio, []).append(lead)

        rotulos = dict(EstagioLead.choices)
        colunas = []
        for estagio in ORDEM_DO_FUNIL:
            if estagio in ESTAGIOS_FECHADOS:
                continue
            do_estagio = agrupado.get(estagio, [])
            colunas.append(
                {
                    "estagio": estagio,
                    "rotulo": rotulos[estagio],
                    "total": len(do_estagio),
                    "valor_total": sum((lead.valor_estimado or 0) for lead in do_estagio),
                    "leads": LeadListSerializer(
                        do_estagio, many=True, context=self.get_serializer_context()
                    ).data,
                }
            )

        return Response(colunas)

    @extend_schema(responses=EstatisticasCrmSerializer)
    @action(detail=False, methods=["get"])
    def estatisticas(self, request):
        base = self.filter_queryset(self.get_queryset())
        total = base.count()
        ganhos = base.filter(estagio=EstagioLead.FECHADO_GANHO).count()
        perdidos = base.filter(estagio=EstagioLead.FECHADO_PERDIDO).count()
        fechados = ganhos + perdidos

        com_sla = base.filter(sla_cumprido__isnull=False)
        total_sla = com_sla.count()
        cumpridos = com_sla.filter(sla_cumprido=True).count()

        tempo_medio = base.filter(primeiro_contato_em__isnull=False).aggregate(
            media=Avg(Extract(F("primeiro_contato_em") - F("criado_em"), "epoch"))
        )["media"]

        def agrupar(campo, rotulos=None):
            resultado = {}
            for linha in base.values(campo).annotate(total=Count("id")).order_by("-total"):
                bruto = linha[campo]
                rotulo = rotulos.get(bruto, bruto) if rotulos else bruto
                if bruto in (None, ""):
                    continue
                resultado[rotulo] = linha["total"]
            return resultado

        return Response(
            {
                "total_geral": total,
                "abertos": total - fechados,
                "ganhos": ganhos,
                "perdidos": perdidos,
                "taxa_conversao": round(ganhos / fechados * 100, 2) if fechados else 0.0,
                "sla_cumprido_percentual": (
                    round(cumpridos / total_sla * 100, 2) if total_sla else 0.0
                ),
                "tempo_medio_primeiro_contato_min": (
                    round(tempo_medio / 60, 1) if tempo_medio else 0.0
                ),
                "por_estagio": agrupar("estagio", dict(EstagioLead.choices)),
                "por_origem": agrupar("origem", dict(OrigemLead.choices)),
                "por_corretor": agrupar("corretor__nome_completo"),
                "por_motivo_perda": agrupar("motivo_perda", dict(MotivoPerda.choices)),
                "valor_em_negociacao": base.filter(
                    estagio__in=[EstagioLead.PROPOSTA, EstagioLead.NEGOCIACAO]
                ).aggregate(total=Sum("valor_estimado"))["total"]
                or 0,
            }
        )


class VisitaViewSet(EscopoDoCorretorMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Visita.objects.select_related("lead", "imovel", "corretor")
    serializer_class = VisitaSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VisitaFilter
    ordering_fields = ["agendada_para"]

    def perform_create(self, serializer):
        dados = serializer.validated_data
        try:
            serializer.instance = agendar_visita(
                dados["lead"],
                dados["imovel"],
                dados["agendada_para"],
                request=self.request,
                corretor=dados.get("corretor"),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"agendada_para": str(erro)}) from erro

    @extend_schema(request=FeedbackVisitaSerializer, responses=VisitaSerializer)
    @action(detail=True, methods=["post"])
    def feedback(self, request, pk=None):
        visita = self.get_object()
        serializer = FeedbackVisitaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registrar_feedback_visita(
            visita,
            serializer.validated_data["feedback"],
            serializer.validated_data.get("interesse_pos_visita", ""),
            request=request,
        )
        return Response(VisitaSerializer(visita).data)

    @extend_schema(request=None, responses=VisitaSerializer)
    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        visita = self.get_object()
        visita.cancelada = True
        visita.save(update_fields=["cancelada"])
        registrar_interacao(
            visita.lead,
            TipoInteracao.SISTEMA,
            f"Visita de {visita.agendada_para:%d/%m/%Y %H:%M} cancelada.",
            usuario=request.user,
        )
        return Response(VisitaSerializer(visita).data)

    @extend_schema(responses=VisitaSerializer(many=True))
    @action(detail=False, methods=["get"])
    def agenda(self, request):
        """Visitas do dia primeira tela do corretor pela manhã."""
        from django.utils import timezone

        dia = request.query_params.get("data")
        data = timezone.localdate()
        if dia:
            from datetime import date

            try:
                data = date.fromisoformat(dia)
            except ValueError as erro:
                raise ValidationError({"data": "Use o formato AAAA-MM-DD."}) from erro

        visitas = (
            self.get_queryset()
            .filter(agendada_para__date=data, cancelada=False)
            .order_by("agendada_para")
        )
        return Response(VisitaSerializer(visitas, many=True).data)


class PropostaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Proposta.objects.select_related("lead", "imovel", "criada_por")
    serializer_class = PropostaSerializer
    filterset_fields = ["status", "imovel", "lead"]

    def perform_create(self, serializer):
        dados = dict(serializer.validated_data)
        lead = dados.pop("lead")
        imovel = dados.pop("imovel")
        try:
            serializer.instance = criar_proposta(lead, imovel, dados, request=self.request)
        except RegraDeNegocio as erro:
            raise ValidationError({"imovel": str(erro)}) from erro

    @extend_schema(request=None, responses=PropostaSerializer)
    @action(detail=True, methods=["post"])
    def aceitar(self, request, pk=None):
        proposta = self.get_object()
        try:
            aceitar_proposta(proposta, request=request)
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return Response(PropostaSerializer(proposta).data)

    @extend_schema(request=RespostaPropostaSerializer, responses=PropostaSerializer)
    @action(detail=True, methods=["post"])
    def recusar(self, request, pk=None):
        proposta = self.get_object()
        serializer = RespostaPropostaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            recusar_proposta(
                proposta, serializer.validated_data.get("motivo", ""), request=request
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return Response(PropostaSerializer(proposta).data)


@extend_schema(request=ContatoPublicoSerializer, responses={201: None})
class ContatoPublicoView(APIView):
    """POST /api/v1/public/{subdominio}/contato/ formulário do site vira lead."""

    serializer_class = ContatoPublicoSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "contato_publico"

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

        serializer = ContatoPublicoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        imovel = None
        if codigo := dados.get("imovel_codigo"):
            imovel = Imovel.objects.filter(
                tenant=tenant, codigo=codigo, publicado_site=True
            ).first()

        criar_lead(
            {
                "nome": dados["nome"],
                "email": dados.get("email", ""),
                "telefone": dados.get("telefone", ""),
                "mensagem": dados.get("mensagem", ""),
                "origem": OrigemLead.SITE,
                "imovel_interesse": imovel,
            },
            tenant,
        )

        # Não devolvemos o lead criado: é endpoint anônimo.
        return Response(status=status.HTTP_201_CREATED)
