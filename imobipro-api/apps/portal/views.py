"""Portal do cliente: só o que é do contrato dele.

Toda consulta parte da pessoa vinculada ao acesso, nunca de um identificador
que veio do navegador. É isso que impede um inquilino de ver o contrato do
vizinho trocando um id na URL.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.atendimento.models import StatusTicket, Ticket, TipoTicket
from apps.atendimento.services import abrir_ticket
from apps.contratos.models import Contrato, StatusContrato
from apps.locacao.models import Cobranca, StatusCobranca
from apps.portal.permissions import EhClienteComAcesso
from apps.portal.serializers import (
    AberturaChamadoSerializer,
    ChamadoDoClienteSerializer,
    CobrancaDoClienteSerializer,
    ContratoDoClienteSerializer,
    VistoriaDoClienteSerializer,
)
from apps.vistorias.models import Vistoria


class BaseDoCliente(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, EhClienteComAcesso]

    @property
    def pessoa(self):
        return self.request.user.pessoa

    def contratos_do_cliente(self):
        return Contrato.objects.filter(
            tenant=self.request.user.tenant,
            partes__pessoa=self.pessoa,
            deletado_em__isnull=True,
        ).distinct()

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "pessoa": self.pessoa}


class MeusContratosViewSet(BaseDoCliente, viewsets.mixins.ListModelMixin):
    serializer_class = ContratoDoClienteSerializer

    def get_queryset(self):
        return (
            self.contratos_do_cliente()
            .select_related("imovel", "imovel__endereco")
            .prefetch_related("partes__pessoa")
            .order_by("-data_inicio")
        )


class MinhasCobrancasViewSet(BaseDoCliente, viewsets.mixins.ListModelMixin):
    serializer_class = CobrancaDoClienteSerializer

    def get_queryset(self):
        return (
            Cobranca.objects.filter(contrato__in=self.contratos_do_cliente())
            .select_related("contrato")
            .order_by("-competencia")
        )


class MinhasVistoriasViewSet(BaseDoCliente, viewsets.mixins.ListModelMixin):
    serializer_class = VistoriaDoClienteSerializer

    def get_queryset(self):
        return Vistoria.objects.filter(contrato__in=self.contratos_do_cliente()).order_by(
            "-realizada_em"
        )


class MeusChamadosViewSet(
    BaseDoCliente, viewsets.mixins.ListModelMixin, viewsets.mixins.CreateModelMixin
):
    serializer_class = ChamadoDoClienteSerializer

    def get_queryset(self):
        return (
            Ticket.objects.filter(
                tenant=self.request.user.tenant,
                solicitante_email=self.request.user.email,
            )
            .prefetch_related("eventos")
            .order_by("-criado_em")
        )

    @extend_schema(
        request=AberturaChamadoSerializer, responses={201: ChamadoDoClienteSerializer}
    )
    def create(self, request):
        serializer = AberturaChamadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        contratos = self.contratos_do_cliente().filter(status=StatusContrato.ATIVO)
        if identificador := dados.get("contrato"):
            contratos = contratos.filter(pk=identificador)

        contrato = contratos.first()
        if not contrato:
            raise ValidationError(
                {"contrato": "Você não tem contrato ativo para abrir chamado."}
            )

        ticket = abrir_ticket(
            {
                "tipo": TipoTicket.MANUTENCAO,
                "solicitante_nome": self.pessoa.nome,
                "solicitante_email": request.user.email,
                "solicitante_telefone": self.pessoa.telefone,
                "mensagem": dados["mensagem"],
            },
            request.user.tenant,
            imovel=contrato.imovel,
            request=request,
        )

        return Response(
            ChamadoDoClienteSerializer(ticket).data, status=status.HTTP_201_CREATED
        )


class ResumoDoClienteView(APIView):
    """A primeira tela do portal: o que vence, o que abriu, o que assinar."""

    permission_classes = [IsAuthenticated, EhClienteComAcesso]

    def get(self, request):
        pessoa = request.user.pessoa
        contratos = Contrato.objects.filter(
            tenant=request.user.tenant, partes__pessoa=pessoa, deletado_em__isnull=True
        ).distinct()

        cobrancas = Cobranca.objects.filter(contrato__in=contratos)
        em_aberto = cobrancas.filter(
            status__in=[StatusCobranca.ABERTA, StatusCobranca.ATRASADA]
        ).order_by("vencimento")

        chamados = Ticket.objects.filter(
            tenant=request.user.tenant, solicitante_email=request.user.email
        ).exclude(status__in=[StatusTicket.CONCLUIDO, StatusTicket.CANCELADO])

        vistorias = Vistoria.objects.filter(contrato__in=contratos)

        contrato_ativo = contratos.filter(status=StatusContrato.ATIVO).first()

        return Response(
            {
                "nome": pessoa.nome,
                "contratos_ativos": contratos.filter(status=StatusContrato.ATIVO).count(),
                "contrato_atual": (
                    ContratoDoClienteSerializer(
                        contrato_ativo, context={"pessoa": pessoa}
                    ).data
                    if contrato_ativo
                    else None
                ),
                "proxima_cobranca": (
                    CobrancaDoClienteSerializer(em_aberto.first()).data
                    if em_aberto.exists()
                    else None
                ),
                "cobrancas_em_aberto": em_aberto.count(),
                "chamados_abertos": chamados.count(),
                "vistorias_a_assinar": vistorias.filter(
                    status="FINALIZADA", assinatura_locatario=False
                ).count(),
            }
        )


class AssinarVistoriaView(APIView):
    """O inquilino assina o laudo pelo portal, sem depender de papel."""

    permission_classes = [IsAuthenticated, EhClienteComAcesso]

    @extend_schema(request=None, responses=VistoriaDoClienteSerializer)
    def post(self, request, vistoria_id):
        contratos = Contrato.objects.filter(
            tenant=request.user.tenant,
            partes__pessoa=request.user.pessoa,
            deletado_em__isnull=True,
        )
        vistoria = Vistoria.objects.filter(pk=vistoria_id, contrato__in=contratos).first()
        if not vistoria:
            return Response(
                {
                    "detail": "Vistoria não encontrada.",
                    "code": "nao_encontrado",
                    "campos": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if vistoria.status != "FINALIZADA":
            raise ValidationError({"vistoria": "Só laudo finalizado pode ser assinado."})

        vistoria.assinatura_locatario = True
        vistoria.save(update_fields=["assinatura_locatario", "atualizado_em"])
        return Response(VistoriaDoClienteSerializer(vistoria).data)


class ContratoEmPdfView(APIView):
    """Segunda via do contrato para quem assinou."""

    permission_classes = [IsAuthenticated, EhClienteComAcesso]

    @extend_schema(responses={200: None})
    def get(self, request, contrato_id):
        from apps.core.pdf import resposta_pdf

        contrato = (
            Contrato.objects.filter(
                pk=contrato_id,
                tenant=request.user.tenant,
                partes__pessoa=request.user.pessoa,
                deletado_em__isnull=True,
            )
            .select_related("imovel", "imovel__endereco")
            .prefetch_related("partes__pessoa")
            .first()
        )
        if not contrato:
            return Response(
                {
                    "detail": "Contrato não encontrado.",
                    "code": "nao_encontrado",
                    "campos": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return resposta_pdf(
            "pdf/contrato.html",
            {"contrato": contrato, "tenant": request.user.tenant},
            f"{contrato.numero}.pdf",
        )
