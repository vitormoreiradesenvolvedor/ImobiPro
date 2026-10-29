from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import Papel
from apps.contratos.models import Comissao, Contrato, StatusContrato
from apps.contratos.serializers import (
    AtivacaoSerializer,
    ComissaoSerializer,
    ConfiguracaoComissaoSerializer,
    ContratoDetailSerializer,
    ContratoListSerializer,
    ParteContratoSerializer,
    PreviaReajusteSerializer,
    ReajusteEntradaSerializer,
    ReajusteSerializer,
    RescisaoSerializer,
)
from apps.contratos.services import (
    RegraDeNegocio,
    adicionar_parte,
    aplicar_reajuste,
    ativar_contrato,
    configuracao_comissao,
    criar_contrato,
    encerrar_contrato,
    liberar_comissao,
    pagar_comissao,
    previa_reajuste,
    rescindir_contrato,
)
from apps.core.mixins import TenantQuerySetMixin
from apps.core.pdf import resposta_pdf


class ContratoFilter(filters.FilterSet):
    vencendo_em = filters.NumberFilter(method="filtrar_vencendo_em")
    ativo = filters.BooleanFilter(method="filtrar_ativo")

    class Meta:
        model = Contrato
        fields = ["tipo", "status", "imovel"]

    def filtrar_vencendo_em(self, queryset, nome, valor):
        from datetime import timedelta

        limite = timezone.localdate() + timedelta(days=int(valor))
        return queryset.filter(
            status=StatusContrato.ATIVO,
            data_fim__isnull=False,
            data_fim__lte=limite,
            data_fim__gte=timezone.localdate(),
        )

    def filtrar_ativo(self, queryset, nome, valor):
        return queryset.filter(status=StatusContrato.ATIVO) if valor else queryset


class ContratoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = (
        Contrato.objects.filter(deletado_em__isnull=True)
        .select_related("imovel", "imovel__endereco", "proposta")
        .prefetch_related("partes__pessoa", "reajustes", "comissoes__usuario")
    )
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ContratoFilter

    def get_serializer_class(self):
        return ContratoListSerializer if self.action == "list" else ContratoDetailSerializer

    def perform_create(self, serializer):
        try:
            serializer.instance = criar_contrato(
                dict(serializer.validated_data),
                self.request.user.tenant,
                request=self.request,
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"detail": str(erro)}) from erro

    def perform_update(self, serializer):
        if serializer.instance.status != StatusContrato.RASCUNHO:
            raise ValidationError(
                {"detail": "Contrato assinado não é editado: rescinda ou faça aditivo."}
            )
        serializer.save()

    @extend_schema(
        request=ParteContratoSerializer, responses={201: ParteContratoSerializer}
    )
    @action(detail=True, methods=["post"])
    def partes(self, request, pk=None):
        contrato = self.get_object()
        serializer = ParteContratoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            parte = adicionar_parte(
                contrato,
                serializer.validated_data["pessoa"],
                serializer.validated_data["papel"],
                serializer.validated_data.get("percentual", 100),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"papel": str(erro)}) from erro

        return Response(ParteContratoSerializer(parte).data, status=201)

    def _resposta_atualizada(self, contrato, request):
        """Serializa o contrato relido do banco.

        Ativar, rescindir e encerrar criam ou mudam filhos (comissões, cobranças,
        reajustes). A instância carregada por `get_object()` guarda o prefetch
        anterior à mudança e devolveria listas desatualizadas ao front.
        """

        atual = self.get_queryset().get(pk=contrato.pk)
        return Response(ContratoDetailSerializer(atual, context={"request": request}).data)

    @extend_schema(request=AtivacaoSerializer, responses=ContratoDetailSerializer)
    @action(detail=True, methods=["post"])
    def ativar(self, request, pk=None):
        contrato = self.get_object()
        serializer = AtivacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            ativar_contrato(
                contrato,
                request=request,
                assinado_em=serializer.validated_data.get("assinado_em"),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"ativacao": str(erro)}) from erro

        return self._resposta_atualizada(contrato, request)

    @extend_schema(request=RescisaoSerializer, responses=ContratoDetailSerializer)
    @action(detail=True, methods=["post"])
    def rescindir(self, request, pk=None):
        contrato = self.get_object()
        serializer = RescisaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rescindir_contrato(
                contrato,
                serializer.validated_data["motivo"],
                request=request,
                data_rescisao=serializer.validated_data.get("data"),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"rescisao": str(erro)}) from erro

        return self._resposta_atualizada(contrato, request)

    @extend_schema(request=None, responses=ContratoDetailSerializer)
    @action(detail=True, methods=["post"])
    def encerrar(self, request, pk=None):
        contrato = self.get_object()
        try:
            encerrar_contrato(contrato, request=request)
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return self._resposta_atualizada(contrato, request)

    @extend_schema(
        request=ReajusteEntradaSerializer,
        responses={200: PreviaReajusteSerializer, 201: ReajusteSerializer},
    )
    @action(detail=True, methods=["post"])
    def reajustar(self, request, pk=None):
        """Sem `aplicar=true` devolve só a prévia o gestor confere antes."""

        contrato = self.get_object()
        serializer = ReajusteEntradaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dados = serializer.validated_data

        try:
            if not dados["aplicar"]:
                return Response(previa_reajuste(contrato, dados["percentual"]))

            reajuste = aplicar_reajuste(
                contrato,
                dados["percentual"],
                request=request,
                data_aplicacao=dados.get("data_aplicacao"),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"percentual": str(erro)}) from erro

        return Response(ReajusteSerializer(reajuste).data, status=201)

    @extend_schema(request=None, responses={201: None})
    @action(detail=True, methods=["post"], url_path="acesso-do-inquilino")
    def acesso_do_inquilino(self, request, pk=None):
        """Cria o acesso do inquilino ao portal, depois do contrato assinado.

        Antes de assinar não existe portal: é a assinatura que dá ao cliente o
        direito de ver boleto, laudo e chamado. A senha provisória volta uma
        única vez, para a imobiliária entregar ao cliente.
        """

        import secrets

        from apps.accounts.models import Papel, Usuario
        from apps.contratos.models import PapelParte

        contrato = self.get_object()
        if contrato.status != StatusContrato.ATIVO:
            raise ValidationError(
                {"contrato": "Só contrato ativo libera o portal do inquilino."}
            )

        parte = contrato.partes.filter(
            papel__in=[PapelParte.LOCATARIO, PapelParte.COMPRADOR]
        ).first()
        if not parte:
            raise ValidationError({"contrato": "Este contrato não tem locatário."})

        pessoa = parte.pessoa
        if not pessoa.email:
            raise ValidationError({"email": f"{pessoa.nome} está sem e-mail no cadastro."})

        existente = Usuario.objects.filter(email__iexact=pessoa.email).first()
        if existente:
            existente.pessoa = pessoa
            existente.save(update_fields=["pessoa", "atualizado_em"])
            return Response(
                {
                    "email": existente.email,
                    "senha_provisoria": None,
                    "detail": "Este e-mail já tinha acesso; o cadastro foi vinculado.",
                }
            )

        senha = secrets.token_urlsafe(9)
        usuario = Usuario.objects.create_user(
            email=pessoa.email,
            password=senha,
            nome_completo=pessoa.nome,
            telefone=pessoa.telefone,
            papel=Papel.INQUILINO,
            tenant=contrato.tenant,
            pessoa=pessoa,
        )

        return Response(
            {
                "email": usuario.email,
                "senha_provisoria": senha,
                "detail": "Entregue a senha ao inquilino; ele troca no primeiro acesso.",
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses={200: None})
    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        contrato = self.get_object()
        return resposta_pdf(
            "pdf/contrato.html",
            {
                "contrato": contrato,
                "tenant": contrato.tenant,
                "partes": contrato.partes.select_related("pessoa"),
                "reajustes": contrato.reajustes.all(),
                "emitido_em": timezone.now(),
            },
            nome_arquivo=f"contrato-{contrato.numero}.pdf",
            base_url=request.build_absolute_uri("/"),
        )


class ComissaoViewSet(
    TenantQuerySetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Comissao.objects.select_related("contrato", "usuario")
    serializer_class = ComissaoSerializer
    filterset_fields = ["status", "papel", "usuario", "contrato"]

    def get_queryset(self):
        queryset = super().get_queryset()
        usuario = self.request.user

        # Corretor vê a própria comissão; gestão e financeiro veem todas.
        if usuario.papel == Papel.CORRETOR:
            return queryset.filter(usuario=usuario)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.request.query_params.get("usuario") == "me":
            return queryset.filter(usuario=self.request.user)
        return queryset

    @extend_schema(request=None, responses=ComissaoSerializer)
    @action(detail=True, methods=["post"])
    def liberar(self, request, pk=None):
        comissao = self.get_object()
        try:
            liberar_comissao(comissao, request=request)
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return Response(ComissaoSerializer(comissao).data)

    @extend_schema(request=None, responses=ComissaoSerializer)
    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        comissao = self.get_object()
        try:
            pagar_comissao(comissao, request=request)
        except RegraDeNegocio as erro:
            raise ValidationError({"status": str(erro)}) from erro
        return Response(ComissaoSerializer(comissao).data)


class ConfiguracaoComissaoView(viewsets.ViewSet):
    """Tabela de comissão da imobiliária (Configurações)."""

    serializer_class = ConfiguracaoComissaoSerializer

    @extend_schema(responses=ConfiguracaoComissaoSerializer)
    def list(self, request):
        config = configuracao_comissao(request.user.tenant)
        return Response(ConfiguracaoComissaoSerializer(config).data)

    @extend_schema(
        request=ConfiguracaoComissaoSerializer, responses=ConfiguracaoComissaoSerializer
    )
    def create(self, request):
        if request.user.papel not in {Papel.ADMIN, Papel.SUPERADMIN}:
            raise ValidationError({"detail": "Só o administrador altera a tabela."})

        config = configuracao_comissao(request.user.tenant)
        serializer = ConfiguracaoComissaoSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
