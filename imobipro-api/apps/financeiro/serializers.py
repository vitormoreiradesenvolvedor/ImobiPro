from rest_framework import serializers

from apps.financeiro.models import Transacao


class TransacaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    categoria_display = serializers.CharField(
        source="get_categoria_display", read_only=True
    )
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    estornada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Transacao
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "categoria",
            "categoria_display",
            "descricao",
            "valor",
            "data_competencia",
            "data_liquidacao",
            "cobranca",
            "repasse",
            "comissao",
            "contrato",
            "contrato_numero",
            "estorno_de",
            "estornada",
            "criado_em",
        ]
        read_only_fields = ["id", "estorno_de", "criado_em"]


class EstornoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255)


class DreSerializer(serializers.Serializer):
    inicio = serializers.DateField()
    fim = serializers.DateField()
    receita_operacional = serializers.DecimalField(max_digits=14, decimal_places=2)
    despesa_operacional = serializers.DecimalField(max_digits=14, decimal_places=2)
    resultado = serializers.DecimalField(max_digits=14, decimal_places=2)
    margem_percentual = serializers.FloatField()
    volume_movimentado = serializers.DecimalField(max_digits=14, decimal_places=2)
    por_categoria = serializers.DictField()


class ConciliacaoSerializer(serializers.Serializer):
    arquivo = serializers.FileField()


class ResultadoConciliacaoSerializer(serializers.Serializer):
    conciliadas = serializers.ListField()
    nao_encontradas = serializers.ListField()
    ja_pagas = serializers.ListField()
    total_conciliado = serializers.IntegerField()


class DesempenhoCorretorSerializer(serializers.Serializer):
    corretor = serializers.CharField()
    leads = serializers.IntegerField()
    ganhos = serializers.IntegerField()
    conversao = serializers.FloatField()
    imoveis_captados = serializers.IntegerField()
    contratos = serializers.IntegerField()
    comissao_prevista = serializers.DecimalField(max_digits=14, decimal_places=2)
    comissao_paga = serializers.DecimalField(max_digits=14, decimal_places=2)
