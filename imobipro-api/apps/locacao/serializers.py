from rest_framework import serializers

from apps.locacao.models import Cobranca, EventoCobranca, Repasse


class EventoCobrancaSerializer(serializers.ModelSerializer):
    etapa_display = serializers.CharField(source="get_etapa_display", read_only=True)

    class Meta:
        model = EventoCobranca
        fields = [
            "id",
            "etapa",
            "etapa_display",
            "canal",
            "destinatario",
            "detalhe",
            "criado_em",
        ]


class CobrancaSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    imovel_codigo = serializers.CharField(source="contrato.imovel.codigo", read_only=True)
    inquilino = serializers.SerializerMethodField()
    dias_de_atraso = serializers.IntegerField(read_only=True)
    saldo = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cobranca
        fields = [
            "id",
            "contrato",
            "contrato_numero",
            "imovel_codigo",
            "inquilino",
            "competencia",
            "vencimento",
            "valor_aluguel",
            "valor_condominio",
            "valor_iptu",
            "valor_seguro",
            "outros",
            "descricao_outros",
            "valor_multa",
            "valor_juros",
            "valor_total",
            "valor_pago",
            "pago_em",
            "forma_pagamento",
            "status",
            "status_display",
            "dias_de_atraso",
            "saldo",
            "linha_digitavel",
            "pix_copia_cola",
            # Identificador do boleto: é por ele que o retorno do banco casa a baixa.
            "nosso_numero",
            "criado_em",
        ]
        read_only_fields = [
            "id",
            "nosso_numero",
            "valor_multa",
            "valor_juros",
            "valor_total",
            "valor_pago",
            "pago_em",
            "status",
            "criado_em",
        ]

    def get_inquilino(self, cobranca):
        locatario = cobranca.contrato.locatario
        return locatario.pessoa.nome if locatario else None


class BaixaCobrancaSerializer(serializers.Serializer):
    valor_pago = serializers.DecimalField(max_digits=12, decimal_places=2)
    data = serializers.DateField(required=False)
    forma = serializers.ChoiceField(
        choices=["PIX", "BOLETO", "TRANSFERENCIA", "DINHEIRO", "CARTAO"],
        required=False,
        allow_blank=True,
    )


class GeracaoCobrancaSerializer(serializers.Serializer):
    meses = serializers.IntegerField(min_value=1, max_value=12, default=1)
    a_partir_de = serializers.DateField(required=False)


class RepasseSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    proprietario = serializers.SerializerMethodField()
    total_retencoes = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = Repasse
        fields = [
            "id",
            "contrato",
            "contrato_numero",
            "proprietario",
            "cobranca",
            "competencia",
            "valor_bruto",
            "taxa_administracao",
            "retencoes",
            "total_retencoes",
            "valor_liquido",
            "status",
            "status_display",
            "pago_em",
            "comprovante",
            "criado_em",
        ]
        read_only_fields = [
            "id",
            "nosso_numero",
            "valor_bruto",
            "taxa_administracao",
            "valor_liquido",
            "status",
            "pago_em",
            "criado_em",
        ]

    def get_proprietario(self, repasse):
        return repasse.contrato.imovel.proprietario.nome


class RetencaoSerializer(serializers.Serializer):
    descricao = serializers.CharField(max_length=140)
    valor = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class LiquidacaoRepasseSerializer(serializers.Serializer):
    data = serializers.DateField(required=False)


class InadimplenciaSerializer(serializers.Serializer):
    competencia = serializers.DateField()
    total_cobrancas = serializers.IntegerField()
    atrasadas = serializers.IntegerField()
    percentual = serializers.FloatField()
