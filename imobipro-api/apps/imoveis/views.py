from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import Avg, Count, F, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import AcessoAoPainel
from apps.core.mixins import TenantQuerySetMixin
from apps.imoveis.filters import ImovelFilter
from apps.imoveis.geocodificacao import EnderecoNaoLocalizado, geocodificar_imovel
from apps.imoveis.models import (
    Caracteristica,
    Finalidade,
    FotoImovel,
    Imovel,
    MidiaImovel,
    SituacaoImovel,
    TipoImovel,
    TipoMidia,
)
from apps.imoveis.permissions import ImovelPermission
from apps.imoveis.serializers import (
    CaracteristicaSerializer,
    CatalogoSerializer,
    EstatisticasImoveisSerializer,
    FotoImovelSerializer,
    HistoricoImovelSerializer,
    ImovelDetailSerializer,
    ImovelListSerializer,
    MidiaImovelSerializer,
    MudancaSituacaoSerializer,
    ReordenacaoFotosSerializer,
)
from apps.imoveis.services import (
    RegraDeNegocio,
    atualizar_imovel,
    criar_imovel,
    definir_capa,
    despublicar,
    mudar_situacao,
    publicar,
    reordenar_fotos,
)
from apps.imoveis.tasks import gerar_thumbnail


class BuscaTextualBackend(filters.BaseFilterBackend):
    """Usa o índice GIN quando há `?search=`; sem termo, não toca no queryset."""

    def filter_queryset(self, request, queryset, view):
        termo = request.query_params.get("search", "").strip()
        if not termo:
            return queryset

        consulta = SearchQuery(termo, config="portuguese", search_type="websearch")
        return (
            queryset.filter(busca=consulta)
            .annotate(relevancia=SearchRank(F("busca"), consulta))
            .order_by("-relevancia")
        )


class ImovelViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Carteira de imóveis da imobiliária."""

    queryset = (
        Imovel.objects.filter(deletado_em__isnull=True)
        .select_related("endereco", "proprietario", "captador")
        .prefetch_related("fotos", "caracteristicas")
    )
    permission_classes = [AcessoAoPainel, ImovelPermission]
    filter_backends = [DjangoFilterBackend, BuscaTextualBackend, filters.OrderingFilter]
    filterset_class = ImovelFilter
    ordering_fields = [
        "valor_venda",
        "valor_locacao",
        "criado_em",
        "visualizacoes",
        "area_util",
    ]
    parser_classes = [MultiPartParser, FormParser, *viewsets.ModelViewSet.parser_classes]

    def get_queryset(self):
        consulta = super().get_queryset()
        # Banner, vídeo e planta só aparecem na ficha; a listagem não paga por eles.
        if self.action in {"list", "mapa", "estatisticas"}:
            return consulta
        return consulta.prefetch_related("midias")

    def get_serializer_class(self):
        if self.action in {"list", "mapa"}:
            return ImovelListSerializer
        return ImovelDetailSerializer

    def perform_create(self, serializer):
        dados = dict(serializer.validated_data)
        dados_endereco = dados.pop("endereco")
        caracteristicas = dados.pop("caracteristicas", [])

        from apps.pessoas.models import Endereco

        dados["endereco"] = Endereco.objects.create(**dados_endereco)
        dados.setdefault("captador", self.request.user)

        imovel = criar_imovel(dados, self.request.user.tenant, request=self.request)
        if caracteristicas:
            imovel.caracteristicas.set(caracteristicas)

        serializer.instance = imovel

    def perform_update(self, serializer):
        dados = dict(serializer.validated_data)
        dados_endereco = dados.pop("endereco", None)
        caracteristicas = dados.pop("caracteristicas", None)
        imovel = serializer.instance

        if dados_endereco:
            for campo, valor in dados_endereco.items():
                setattr(imovel.endereco, campo, valor)
            imovel.endereco.save()

        atualizar_imovel(imovel, dados, request=self.request)
        if caracteristicas is not None:
            imovel.caracteristicas.set(caracteristicas)

    def retrieve(self, request, *args, **kwargs):
        imovel = self.get_object()
        Imovel.objects.filter(pk=imovel.pk).update(visualizacoes=F("visualizacoes") + 1)
        return Response(self.get_serializer(imovel).data)

    # ------------------------------------------------------------------ ações

    @extend_schema(request=MudancaSituacaoSerializer, responses=ImovelDetailSerializer)
    @action(detail=True, methods=["patch"])
    def situacao(self, request, pk=None):
        imovel = self.get_object()
        serializer = MudancaSituacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            mudar_situacao(
                imovel,
                serializer.validated_data["situacao"],
                request=request,
                motivo=serializer.validated_data.get("motivo", ""),
            )
        except RegraDeNegocio as erro:
            raise ValidationError({"situacao": str(erro)}) from erro

        return Response(
            ImovelDetailSerializer(imovel, context=self.get_serializer_context()).data
        )

    @extend_schema(request=None, responses=ImovelDetailSerializer)
    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        imovel = self.get_object()
        try:
            publicar(imovel, request=request)
        except RegraDeNegocio as erro:
            raise ValidationError({"publicacao": str(erro)}) from erro
        return Response(
            ImovelDetailSerializer(imovel, context=self.get_serializer_context()).data
        )

    @extend_schema(request=None, responses=ImovelDetailSerializer)
    @action(detail=True, methods=["post"])
    def despublicar(self, request, pk=None):
        imovel = self.get_object()
        despublicar(imovel, request=request, motivo=request.data.get("motivo", ""))
        return Response(
            ImovelDetailSerializer(imovel, context=self.get_serializer_context()).data
        )

    @extend_schema(
        request=FotoImovelSerializer, responses={201: FotoImovelSerializer(many=True)}
    )
    @action(detail=True, methods=["post"], url_path="fotos")
    def enviar_fotos(self, request, pk=None):
        imovel = self.get_object()
        arquivos = request.FILES.getlist("arquivo") or request.FILES.getlist("arquivos")

        if not arquivos:
            raise ValidationError({"arquivo": "Envie ao menos uma imagem."})

        ultima_ordem = imovel.fotos.count()
        criadas = []

        for indice, arquivo in enumerate(arquivos):
            foto = FotoImovel.objects.create(
                imovel=imovel,
                arquivo=arquivo,
                ordem=ultima_ordem + indice,
                capa=(ultima_ordem + indice) == 0,
            )
            gerar_thumbnail.delay(str(foto.pk))
            criadas.append(foto)

        return Response(
            FotoImovelSerializer(criadas, many=True).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=None, responses=ImovelDetailSerializer)
    @action(detail=True, methods=["post"])
    def geocodificar(self, request, pk=None):
        """Busca as coordenadas do endereço no mapa aberto do OpenStreetMap."""

        imovel = self.get_object()
        try:
            geocodificar_imovel(imovel)
        except EnderecoNaoLocalizado as erro:
            raise ValidationError({"endereco": str(erro)}) from erro

        imovel.refresh_from_db()
        return Response(
            ImovelDetailSerializer(imovel, context=self.get_serializer_context()).data
        )

    @extend_schema(
        request=MidiaImovelSerializer, responses={201: MidiaImovelSerializer(many=True)}
    )
    @action(detail=True, methods=["post"], url_path="midias")
    def enviar_midias(self, request, pk=None):
        """Banner, vídeo, planta e tour do anúncio, hospedados aqui mesmo."""

        imovel = self.get_object()
        arquivos = request.FILES.getlist("arquivo")
        if not arquivos:
            raise ValidationError({"arquivo": "Envie ao menos um arquivo."})

        tipo = request.data.get("tipo", TipoMidia.BANNER)
        if tipo not in TipoMidia.values:
            raise ValidationError({"tipo": "Tipo de mídia desconhecido."})

        ultima_ordem = imovel.midias.count()
        criadas = [
            MidiaImovel.objects.create(
                imovel=imovel,
                tipo=tipo,
                arquivo=arquivo,
                titulo=request.data.get("titulo", ""),
                descricao=request.data.get("descricao", ""),
                ordem=ultima_ordem + indice,
            )
            for indice, arquivo in enumerate(arquivos)
        ]

        return Response(
            MidiaImovelSerializer(criadas, many=True).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=None, responses=MidiaImovelSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path=r"midias/(?P<midia_id>[0-9a-f-]{36})/destaque",
    )
    def destacar_midia(self, request, pk=None, midia_id=None):
        """Só um banner abre a página: marcar um novo desmarca o anterior."""

        imovel = self.get_object()
        midia = imovel.midias.filter(pk=midia_id).first()
        if not midia:
            raise ValidationError({"midia": "Mídia não encontrada."})

        MidiaImovel.objects.filter(imovel=imovel, tipo=midia.tipo).update(destaque=False)
        midia.destaque = True
        midia.save(update_fields=["destaque", "atualizado_em"])
        return Response(MidiaImovelSerializer(midia).data)

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["delete"], url_path=r"midias/(?P<midia_id>[0-9a-f-]{36})")
    def remover_midia(self, request, pk=None, midia_id=None):
        imovel = self.get_object()
        midia = imovel.midias.filter(pk=midia_id).first()
        if not midia:
            return Response(
                {"detail": "Mídia não encontrada.", "code": "nao_encontrado", "campos": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        midia.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=ReordenacaoFotosSerializer, responses=FotoImovelSerializer(many=True)
    )
    @action(detail=True, methods=["patch"], url_path="fotos/reordenar")
    def reordenar_fotos(self, request, pk=None):
        imovel = self.get_object()
        serializer = ReordenacaoFotosSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            fotos = reordenar_fotos(imovel, serializer.validated_data["ordem"])
        except RegraDeNegocio as erro:
            raise ValidationError({"ordem": str(erro)}) from erro

        return Response(FotoImovelSerializer(fotos, many=True).data)

    @extend_schema(request=None, responses={204: None})
    # O regex de UUID evita que esta rota capture `fotos/reordenar/` o DRF
    # ordena as ações extras por nome, e "remover_foto" vem antes.
    @action(detail=True, methods=["delete"], url_path=r"fotos/(?P<foto_id>[0-9a-f-]{36})")
    def remover_foto(self, request, pk=None, foto_id=None):
        imovel = self.get_object()
        foto = imovel.fotos.filter(pk=foto_id).first()
        if not foto:
            return Response(
                {"detail": "Foto não encontrada.", "code": "nao_encontrado", "campos": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
        era_capa = foto.capa
        foto.delete()

        # Consulta nova: o prefetch de `get_object` ainda enxerga a foto apagada.
        proxima = FotoImovel.objects.filter(imovel=imovel).order_by("ordem").first()
        if era_capa and proxima:
            definir_capa(imovel, proxima)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses=FotoImovelSerializer)
    @action(
        detail=True, methods=["post"], url_path=r"fotos/(?P<foto_id>[0-9a-f-]{36})/capa"
    )
    def marcar_capa(self, request, pk=None, foto_id=None):
        imovel = self.get_object()
        foto = imovel.fotos.filter(pk=foto_id).first()
        if not foto:
            raise ValidationError({"foto": "Foto não pertence a este imóvel."})
        return Response(FotoImovelSerializer(definir_capa(imovel, foto)).data)

    @extend_schema(responses=HistoricoImovelSerializer(many=True))
    @action(detail=True, methods=["get"])
    def historico(self, request, pk=None):
        imovel = self.get_object()
        eventos = imovel.historico.select_related("usuario")
        return Response(HistoricoImovelSerializer(eventos, many=True).data)

    @extend_schema(responses=ImovelListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def mapa(self, request):
        """Payload enxuto para o mapa: só o que tem coordenada."""
        imoveis = self.filter_queryset(self.get_queryset()).exclude(
            endereco__latitude__isnull=True
        )[:500]
        return Response(self.get_serializer(imoveis, many=True).data)

    @extend_schema(responses=EstatisticasImoveisSerializer)
    @action(detail=False, methods=["get"])
    def estatisticas(self, request):
        """Agregações do dashboard mesmo padrão de /tccs/estatisticas/."""

        base = self.get_queryset()
        rotulos_situacao = dict(Imovel._meta.get_field("situacao").choices)
        rotulos_tipo = dict(Imovel._meta.get_field("tipo").choices)
        rotulos_finalidade = dict(Imovel._meta.get_field("finalidade").choices)

        def agrupar(campo, rotulos=None):
            linhas = base.values(campo).annotate(total=Count("id")).order_by("-total")
            resultado = {}
            for linha in linhas:
                bruto = linha[campo]
                rotulo = rotulos.get(bruto, bruto) if rotulos else bruto
                resultado[rotulo or ""] = linha["total"]
            return resultado

        medias = base.aggregate(
            media_venda=Avg("valor_venda"),
            media_locacao=Avg("valor_locacao"),
            carteira=Sum("valor_venda", filter=Q(situacao=SituacaoImovel.DISPONIVEL)),
        )

        return Response(
            {
                "total_geral": base.count(),
                "publicados": base.filter(publicado_site=True).count(),
                "por_situacao": agrupar("situacao", rotulos_situacao),
                "por_tipo": agrupar("tipo", rotulos_tipo),
                "por_finalidade": agrupar("finalidade", rotulos_finalidade),
                "por_bairro": agrupar("endereco__bairro"),
                "por_captador": agrupar("captador__nome_completo"),
                "valor_medio_venda": medias["media_venda"] or 0,
                "valor_medio_locacao": medias["media_locacao"] or 0,
                "carteira_venda": medias["carteira"] or 0,
            }
        )


class CaracteristicaViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo global usado pelos filtros e pelo formulário de captação."""

    queryset = Caracteristica.objects.all()
    serializer_class = CaracteristicaSerializer
    pagination_class = None


class ImovelPublicoViewSet(viewsets.ReadOnlyModelViewSet):
    """Vitrine do site da imobiliária: sem token, só imóvel publicado."""

    serializer_class = ImovelListSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = "codigo"
    filter_backends = [DjangoFilterBackend, BuscaTextualBackend, filters.OrderingFilter]
    filterset_class = ImovelFilter
    ordering_fields = ["valor_venda", "valor_locacao", "criado_em"]

    def get_queryset(self):
        consulta = (
            Imovel.objects.filter(
                tenant__subdominio=self.kwargs["subdominio"],
                tenant__ativo=True,
                publicado_site=True,
                deletado_em__isnull=True,
                situacao__in=[SituacaoImovel.DISPONIVEL, SituacaoImovel.RESERVADO],
            )
            .select_related("endereco")
            .prefetch_related("fotos")
        )

        # A ficha pública mostra banner e vídeo; catálogo e listagem, não.
        if self.action == "retrieve":
            consulta = consulta.prefetch_related("midias")
        return consulta

    def get_serializer_class(self):
        return ImovelListSerializer if self.action == "list" else ImovelDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        imovel = self.get_object()
        Imovel.objects.filter(pk=imovel.pk).update(visualizacoes=F("visualizacoes") + 1)
        return Response(self.get_serializer(imovel).data)

    @extend_schema(responses=CatalogoSerializer)
    @action(detail=False, methods=["get"])
    def categorias(self, request, subdominio=None):
        """Vitrine categorizada: o que existe hoje, com quantidade e preço.

        O visitante escolhe por finalidade, tipo, bairro ou faixa de preço, e
        cada categoria já vem com quantos imóveis tem. Categoria sem imóvel não
        aparece: catálogo com prateleira vazia irrita quem está procurando.
        """

        base = self.filter_queryset(self.get_queryset())

        def agrupar(campo, rotulos=None):
            linhas = (
                base.values(campo)
                .annotate(total=Count("id"))
                .order_by("-total")
                .filter(total__gt=0)
            )
            return [
                {
                    "valor": linha[campo],
                    "rotulo": (
                        rotulos.get(linha[campo], linha[campo]) if rotulos else linha[campo]
                    ),
                    "total": linha["total"],
                }
                for linha in linhas
                if linha[campo] not in (None, "")
            ]

        faixas = [
            ("ate_1500", "Até R$ 1.500", None, 1500),
            ("1500_3000", "R$ 1.500 a R$ 3.000", 1500, 3000),
            ("3000_5000", "R$ 3.000 a R$ 5.000", 3000, 5000),
            ("acima_5000", "Acima de R$ 5.000", 5000, None),
        ]
        por_faixa = []
        for chave, rotulo, minimo, maximo in faixas:
            consulta = base.filter(valor_locacao__isnull=False)
            if minimo is not None:
                consulta = consulta.filter(valor_locacao__gte=minimo)
            if maximo is not None:
                consulta = consulta.filter(valor_locacao__lt=maximo)
            total = consulta.count()
            if total:
                por_faixa.append({"valor": chave, "rotulo": rotulo, "total": total})

        return Response(
            {
                "total": base.count(),
                "por_finalidade": agrupar("finalidade", dict(Finalidade.choices)),
                "por_tipo": agrupar("tipo", dict(TipoImovel.choices)),
                "por_bairro": agrupar("endereco__bairro"),
                "por_cidade": agrupar("endereco__cidade"),
                "por_faixa_de_aluguel": por_faixa,
                "quartos_disponiveis": sorted(
                    {
                        linha["quartos"]
                        for linha in base.values("quartos")
                        if linha["quartos"]
                    }
                ),
            }
        )

    @extend_schema(responses=ImovelListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def destaques(self, request, subdominio=None):
        """Vitrine da home: o que a imobiliária quer mostrar primeiro."""

        consulta = (
            self.get_queryset()
            .filter(midias__tipo=TipoMidia.BANNER, midias__destaque=True)
            .distinct()
        )
        if not consulta.exists():
            consulta = self.get_queryset().order_by("-visualizacoes")[:6]

        serializer = ImovelListSerializer(
            consulta, many=True, context=self.get_serializer_context()
        )
        return Response(serializer.data)
