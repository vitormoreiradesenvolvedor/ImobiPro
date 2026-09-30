from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.mixins import TenantQuerySetMixin
from apps.core.pdf import resposta_pdf
from apps.vistorias.models import FotoItemVistoria, Vistoria
from apps.vistorias.serializers import (
    AssinaturaSerializer,
    ComparativoSerializer,
    CriacaoVistoriaSerializer,
    ItemVistoriaSerializer,
    RegistroItemSerializer,
    VistoriaDetailSerializer,
    VistoriaListSerializer,
)
from apps.vistorias.services import (
    RegraDeNegocio,
    comparativo,
    criar_vistoria,
    finalizar_vistoria,
    registrar_item,
)


class VistoriaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Execução em campo: o vistoriador usa isso pelo celular."""

    queryset = Vistoria.objects.select_related(
        "contrato", "contrato__imovel", "vistoriador"
    ).prefetch_related("itens__fotos")
    filterset_fields = ["tipo", "status", "contrato"]
    parser_classes = [MultiPartParser, FormParser, *viewsets.ModelViewSet.parser_classes]

    def get_serializer_class(self):
        if self.action == "list":
            return VistoriaListSerializer
        if self.action == "create":
            return CriacaoVistoriaSerializer
        return VistoriaDetailSerializer

    def create(self, request, *args, **kwargs):
        from apps.contratos.models import Contrato

        serializer = CriacaoVistoriaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        contrato = Contrato.objects.filter(
            pk=dados["contrato"], tenant=request.user.tenant
        ).first()
        if not contrato:
            raise ValidationError({"contrato": "Contrato não encontrado."})

        try:
            vistoria = criar_vistoria(
                contrato,
                dados["tipo"],
                realizada_em=dados.get("realizada_em"),
                vistoriador=request.user,
                com_checklist=dados["com_checklist"],
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"tipo": str(erro)}) from erro

        return Response(
            VistoriaDetailSerializer(vistoria).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=RegistroItemSerializer, responses=ItemVistoriaSerializer)
    @action(detail=True, methods=["post"])
    def itens(self, request, pk=None):
        vistoria = self.get_object()
        serializer = RegistroItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            item = registrar_item(
                vistoria,
                dados["comodo"],
                dados["item"],
                dados["estado"],
                dados.get("observacao", ""),
                dados.get("ordem", 0),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"estado": str(erro)}) from erro

        # As fotos chegam no mesmo POST multipart do item, direto do celular.
        for arquivo in request.FILES.getlist("fotos"):
            FotoItemVistoria.objects.create(item=item, arquivo=arquivo)

        return Response(ItemVistoriaSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=VistoriaDetailSerializer)
    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        vistoria = self.get_object()
        try:
            finalizar_vistoria(vistoria)
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return Response(VistoriaDetailSerializer(vistoria).data)

    @extend_schema(request=AssinaturaSerializer, responses=VistoriaDetailSerializer)
    @action(detail=True, methods=["post"])
    def assinar(self, request, pk=None):
        vistoria = self.get_object()
        serializer = AssinaturaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        campos = []
        if serializer.validated_data.get("locatario"):
            vistoria.assinatura_locatario = True
            campos.append("assinatura_locatario")
        if serializer.validated_data.get("imobiliaria"):
            vistoria.assinatura_imobiliaria = True
            campos.append("assinatura_imobiliaria")

        if campos:
            vistoria.save(update_fields=campos)

        return Response(VistoriaDetailSerializer(vistoria).data)

    @extend_schema(responses={200: None})
    @action(detail=True, methods=["get"])
    def laudo(self, request, pk=None):
        vistoria = self.get_object()
        return resposta_pdf(
            "pdf/laudo_vistoria.html",
            {
                "vistoria": vistoria,
                "contrato": vistoria.contrato,
                "tenant": vistoria.tenant,
                "itens_por_comodo": self._agrupar_por_comodo(vistoria),
                "emitido_em": timezone.now(),
            },
            nome_arquivo=f"vistoria-{vistoria.tipo.lower()}-{vistoria.contrato.numero}.pdf",
            base_url=request.build_absolute_uri("/"),
        )

    @extend_schema(responses=ComparativoSerializer)
    @action(
        detail=False,
        methods=["get"],
        url_path=r"comparativo/(?P<contrato_id>[0-9a-f-]{36})",
    )
    def comparativo(self, request, contrato_id=None):
        from apps.contratos.models import Contrato

        contrato = Contrato.objects.filter(
            pk=contrato_id, tenant=request.user.tenant
        ).first()
        if not contrato:
            raise ValidationError({"contrato": "Contrato não encontrado."})

        try:
            return Response(comparativo(contrato))
        except RegraDeNegocio as erro:
            raise ValidationError({"comparativo": str(erro)}) from erro

    def _agrupar_por_comodo(self, vistoria):
        agrupado = {}
        for item in vistoria.itens.all():
            agrupado.setdefault(item.comodo, []).append(item)
        return agrupado
