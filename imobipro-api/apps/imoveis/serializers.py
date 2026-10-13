from rest_framework import serializers

from apps.imoveis.models import (
    Caracteristica,
    FotoImovel,
    HistoricoImovel,
    Imovel,
    MidiaImovel,
    SituacaoImovel,
)
from apps.pessoas.serializers import EnderecoSerializer, PessoaResumoSerializer


class CaracteristicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caracteristica
        fields = ["id", "nome", "slug", "grupo"]


class FotoImovelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoImovel
        fields = ["id", "arquivo", "arquivo_thumb", "legenda", "ordem", "capa"]
        read_only_fields = ["id", "arquivo_thumb"]


class MidiaImovelSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = MidiaImovel
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "arquivo",
            "titulo",
            "descricao",
            "ordem",
            "destaque",
        ]
        read_only_fields = ["id"]


class CategoriaSerializer(serializers.Serializer):
    """Uma prateleira do catálogo: o valor do filtro e quantos imóveis tem."""

    valor = serializers.CharField()
    rotulo = serializers.CharField()
    total = serializers.IntegerField()


class CatalogoSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    por_finalidade = CategoriaSerializer(many=True)
    por_tipo = CategoriaSerializer(many=True)
    por_bairro = CategoriaSerializer(many=True)
    por_cidade = CategoriaSerializer(many=True)
    por_faixa_de_aluguel = CategoriaSerializer(many=True)
    quartos_disponiveis = serializers.ListField(child=serializers.IntegerField())


class HistoricoImovelSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = HistoricoImovel
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "descricao",
            "valor_anterior",
            "valor_novo",
            "usuario_nome",
            "criado_em",
        ]


class ImovelListSerializer(serializers.ModelSerializer):
    """Payload leve do grid e do mapa: nada de histórico ou galeria inteira."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    situacao_display = serializers.CharField(source="get_situacao_display", read_only=True)
    finalidade_display = serializers.CharField(
        source="get_finalidade_display", read_only=True
    )
    foto_capa = serializers.SerializerMethodField()
    bairro = serializers.CharField(source="endereco.bairro", read_only=True)
    cidade = serializers.CharField(source="endereco.cidade", read_only=True)
    latitude = serializers.DecimalField(
        source="endereco.latitude", max_digits=9, decimal_places=6, read_only=True
    )
    longitude = serializers.DecimalField(
        source="endereco.longitude", max_digits=9, decimal_places=6, read_only=True
    )

    class Meta:
        model = Imovel
        fields = [
            "id",
            "codigo",
            "titulo",
            "tipo",
            "tipo_display",
            "finalidade",
            "finalidade_display",
            "situacao",
            "situacao_display",
            "quartos",
            "suites",
            "banheiros",
            "vagas",
            "area_util",
            "valor_venda",
            "valor_locacao",
            "valor_condominio",
            "foto_capa",
            "bairro",
            "cidade",
            "latitude",
            "longitude",
            "publicado_site",
            "destaque",
            "criado_em",
        ]

    def get_foto_capa(self, imovel):
        foto = imovel.foto_capa
        if not foto:
            return None
        arquivo = foto.arquivo_thumb or foto.arquivo
        requisicao = self.context.get("request")
        return requisicao.build_absolute_uri(arquivo.url) if requisicao else arquivo.url


class ImovelDetailSerializer(serializers.ModelSerializer):
    endereco = EnderecoSerializer()
    proprietario_detalhe = PessoaResumoSerializer(source="proprietario", read_only=True)
    caracteristicas_detalhe = CaracteristicaSerializer(
        source="caracteristicas", many=True, read_only=True
    )
    fotos = FotoImovelSerializer(many=True, read_only=True)
    midias = MidiaImovelSerializer(many=True, read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    situacao_display = serializers.CharField(source="get_situacao_display", read_only=True)
    finalidade_display = serializers.CharField(
        source="get_finalidade_display", read_only=True
    )
    captador_nome = serializers.CharField(source="captador.nome_completo", read_only=True)
    valor_iptu_mensal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    pendencias_publicacao = serializers.SerializerMethodField()

    class Meta:
        model = Imovel
        fields = [
            "id",
            "codigo",
            "titulo",
            "descricao",
            "tipo",
            "tipo_display",
            "finalidade",
            "finalidade_display",
            "situacao",
            "situacao_display",
            "proprietario",
            "proprietario_detalhe",
            "captador",
            "captador_nome",
            "endereco",
            "area_total",
            "area_util",
            "quartos",
            "suites",
            "banheiros",
            "vagas",
            "andar",
            "ano_construcao",
            "mobiliado",
            "aceita_pet",
            "valor_venda",
            "valor_locacao",
            "valor_condominio",
            "valor_iptu_anual",
            "parcelas_iptu",
            "valor_iptu_mensal",
            "matricula",
            "inscricao_municipal",
            "exclusividade_ate",
            "autorizacao_assinada",
            "caracteristicas",
            "caracteristicas_detalhe",
            "fotos",
            "midias",
            "publicado_site",
            "destaque",
            "visualizacoes",
            "tour_360_url",
            "video_url",
            "planta_baixa",
            "pendencias_publicacao",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "codigo",
            "situacao",
            "publicado_site",
            "visualizacoes",
            "criado_em",
            "atualizado_em",
        ]

    def get_pendencias_publicacao(self, imovel):
        return imovel.pendencias_para_publicar()

    def validate(self, attrs):
        finalidade = attrs.get("finalidade", getattr(self.instance, "finalidade", None))
        venda = attrs.get("valor_venda", getattr(self.instance, "valor_venda", None))
        locacao = attrs.get("valor_locacao", getattr(self.instance, "valor_locacao", None))

        if finalidade == "VENDA" and locacao:
            raise serializers.ValidationError(
                {"valor_locacao": "Imóvel só para venda não deve ter valor de locação."}
            )
        if finalidade == "LOCACAO" and venda:
            raise serializers.ValidationError(
                {"valor_venda": "Imóvel só para locação não deve ter valor de venda."}
            )
        return attrs

    def validate_proprietario(self, pessoa):
        tenant = self.context["request"].user.tenant
        if pessoa.tenant_id != getattr(tenant, "id", None):
            raise serializers.ValidationError(
                "Proprietário não pertence a esta imobiliária."
            )
        return pessoa


class MudancaSituacaoSerializer(serializers.Serializer):
    situacao = serializers.ChoiceField(choices=SituacaoImovel.choices)
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ReordenacaoFotosSerializer(serializers.Serializer):
    ordem = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class EstatisticasImoveisSerializer(serializers.Serializer):
    """Documenta o payload do dashboard (mesma ideia de /tccs/estatisticas/)."""

    total_geral = serializers.IntegerField()
    publicados = serializers.IntegerField()
    por_situacao = serializers.DictField(child=serializers.IntegerField())
    por_tipo = serializers.DictField(child=serializers.IntegerField())
    por_finalidade = serializers.DictField(child=serializers.IntegerField())
    por_bairro = serializers.DictField(child=serializers.IntegerField())
    por_captador = serializers.DictField(child=serializers.IntegerField())
    valor_medio_venda = serializers.DecimalField(max_digits=12, decimal_places=2)
    valor_medio_locacao = serializers.DecimalField(max_digits=12, decimal_places=2)
    carteira_venda = serializers.DecimalField(max_digits=14, decimal_places=2)
