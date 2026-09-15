from rest_framework import serializers

from apps.vistorias.models import FotoItemVistoria, ItemVistoria, Vistoria


class FotoItemVistoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FotoItemVistoria
        fields = ["id", "arquivo", "legenda"]


class ItemVistoriaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    fotos = FotoItemVistoriaSerializer(many=True, read_only=True)

    class Meta:
        model = ItemVistoria
        fields = [
            "id",
            "comodo",
            "item",
            "estado",
            "estado_display",
            "observacao",
            "ordem",
            "fotos",
        ]


class VistoriaListSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    imovel_codigo = serializers.CharField(source="contrato.imovel.codigo", read_only=True)
    total_itens = serializers.IntegerField(read_only=True)
    itens_com_problema = serializers.IntegerField(read_only=True)

    class Meta:
        model = Vistoria
        fields = [
            "id",
            "contrato",
            "contrato_numero",
            "imovel_codigo",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "realizada_em",
            "total_itens",
            "itens_com_problema",
            "assinatura_locatario",
            "assinatura_imobiliaria",
            "criado_em",
        ]


class VistoriaDetailSerializer(VistoriaListSerializer):
    itens = ItemVistoriaSerializer(many=True, read_only=True)
    vistoriador_nome = serializers.CharField(
        source="vistoriador.nome_completo", read_only=True
    )
    assinada = serializers.BooleanField(read_only=True)

    class Meta(VistoriaListSerializer.Meta):
        fields = VistoriaListSerializer.Meta.fields + [
            "itens",
            "vistoriador",
            "vistoriador_nome",
            "observacoes_gerais",
            "laudo_pdf",
            "assinada",
            "finalizada_em",
        ]
        read_only_fields = ["id", "status", "finalizada_em", "laudo_pdf", "criado_em"]


class CriacaoVistoriaSerializer(serializers.Serializer):
    contrato = serializers.UUIDField()
    tipo = serializers.ChoiceField(choices=["ENTRADA", "PERIODICA", "SAIDA"])
    realizada_em = serializers.DateField(required=False)
    com_checklist = serializers.BooleanField(default=True)


class RegistroItemSerializer(serializers.Serializer):
    comodo = serializers.CharField(max_length=60)
    item = serializers.CharField(max_length=80)
    estado = serializers.ChoiceField(choices=["OTIMO", "BOM", "REGULAR", "RUIM", "AUSENTE"])
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ordem = serializers.IntegerField(required=False, default=0)


class AssinaturaSerializer(serializers.Serializer):
    locatario = serializers.BooleanField(required=False)
    imobiliaria = serializers.BooleanField(required=False)


class LinhaComparativoSerializer(serializers.Serializer):
    comodo = serializers.CharField()
    item = serializers.CharField()
    estado_entrada = serializers.CharField(allow_null=True)
    estado_saida = serializers.CharField(allow_null=True)
    observacao_entrada = serializers.CharField(allow_blank=True)
    observacao_saida = serializers.CharField(allow_blank=True)
    variacao = serializers.IntegerField()
    piorou = serializers.BooleanField()


class ComparativoSerializer(serializers.Serializer):
    contrato = serializers.CharField()
    entrada_em = serializers.DateField()
    saida_em = serializers.DateField()
    total_itens = serializers.IntegerField()
    itens_que_pioraram = serializers.IntegerField()
    percentual_com_avaria = serializers.FloatField()
    itens = LinhaComparativoSerializer(many=True)
