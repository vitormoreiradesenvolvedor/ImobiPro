from rest_framework import serializers

from apps.contratos.models import (
    Comissao,
    ConfiguracaoComissao,
    Contrato,
    ParteContrato,
    Reajuste,
)
from apps.pessoas.serializers import PessoaResumoSerializer


class ParteContratoSerializer(serializers.ModelSerializer):
    pessoa_detalhe = PessoaResumoSerializer(source="pessoa", read_only=True)
    papel_display = serializers.CharField(source="get_papel_display", read_only=True)

    class Meta:
        model = ParteContrato
        fields = ["id", "pessoa", "pessoa_detalhe", "papel", "papel_display", "percentual"]


class ReajusteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reajuste
        fields = [
            "id",
            "data_aplicacao",
            "indice",
            "percentual",
            "valor_anterior",
            "valor_novo",
            "aditivo_pdf",
        ]


class ComissaoSerializer(serializers.ModelSerializer):
    papel_display = serializers.CharField(source="get_papel_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)

    class Meta:
        model = Comissao
        fields = [
            "id",
            "contrato",
            "contrato_numero",
            "usuario",
            "usuario_nome",
            "papel",
            "papel_display",
            "percentual_snapshot",
            "base_calculo",
            "valor",
            "status",
            "status_display",
            "liberada_em",
            "paga_em",
        ]
        read_only_fields = fields


class ContratoListSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True)
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contrato
        fields = [
            "id",
            "numero",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "imovel",
            "imovel_codigo",
            "imovel_titulo",
            "data_inicio",
            "data_fim",
            "valor",
            "dia_vencimento",
            "dias_para_vencer",
            "vigente",
            "criado_em",
        ]


class ContratoDetailSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    garantia_tipo_display = serializers.CharField(
        source="get_garantia_tipo_display", read_only=True
    )
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    partes = ParteContratoSerializer(many=True, read_only=True)
    reajustes = ReajusteSerializer(many=True, read_only=True)
    comissoes = ComissaoSerializer(many=True, read_only=True)
    dias_para_vencer = serializers.IntegerField(read_only=True)
    meses_restantes = serializers.IntegerField(read_only=True)
    proximo_reajuste_em = serializers.DateField(read_only=True)
    vigente = serializers.BooleanField(read_only=True)
    pendencias_ativacao = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = [
            "id",
            "numero",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "imovel",
            "imovel_codigo",
            "imovel_titulo",
            "proposta",
            "data_inicio",
            "data_fim",
            "valor",
            "dia_vencimento",
            "indice_reajuste",
            "taxa_administracao_percent",
            "taxa_intermediacao",
            "garantia_tipo",
            "garantia_tipo_display",
            "garantia_valor",
            "multa_rescisoria_meses",
            "multa_atraso_percent",
            "juros_mora_mes_percent",
            "inclui_condominio",
            "inclui_iptu",
            "valor_seguro_incendio",
            "arquivo_pdf",
            "assinado_em",
            "rescindido_em",
            "motivo_rescisao",
            "multa_rescisao_calculada",
            "observacoes",
            "partes",
            "reajustes",
            "comissoes",
            "dias_para_vencer",
            "meses_restantes",
            "proximo_reajuste_em",
            "vigente",
            "pendencias_ativacao",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "numero",
            "status",
            "assinado_em",
            "rescindido_em",
            "motivo_rescisao",
            "multa_rescisao_calculada",
            "criado_em",
            "atualizado_em",
        ]

    def get_pendencias_ativacao(self, contrato):
        from apps.contratos.services import validar_para_ativacao

        return validar_para_ativacao(contrato) if contrato.status == "RASCUNHO" else []

    def validate_imovel(self, imovel):
        if imovel.tenant_id != self.context["request"].user.tenant_id:
            raise serializers.ValidationError("Imóvel não pertence a esta imobiliária.")
        return imovel

    def validate(self, attrs):
        inicio = attrs.get("data_inicio", getattr(self.instance, "data_inicio", None))
        fim = attrs.get("data_fim", getattr(self.instance, "data_fim", None))

        if inicio and fim and fim <= inicio:
            raise serializers.ValidationError(
                {"data_fim": "O término deve ser posterior ao início."}
            )

        dia = attrs.get("dia_vencimento")
        if dia is not None and not 1 <= dia <= 28:
            raise serializers.ValidationError(
                {"dia_vencimento": "Use um dia entre 1 e 28 para valer em todo mês."}
            )
        return attrs


class AtivacaoSerializer(serializers.Serializer):
    assinado_em = serializers.DateField(required=False)


class RescisaoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255)
    data = serializers.DateField(required=False)


class ReajusteEntradaSerializer(serializers.Serializer):
    percentual = serializers.DecimalField(max_digits=6, decimal_places=3)
    aplicar = serializers.BooleanField(default=False)
    data_aplicacao = serializers.DateField(required=False)


class PreviaReajusteSerializer(serializers.Serializer):
    valor_anterior = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentual = serializers.DecimalField(max_digits=6, decimal_places=3)
    valor_novo = serializers.DecimalField(max_digits=12, decimal_places=2)
    diferenca = serializers.DecimalField(max_digits=12, decimal_places=2)
    indice = serializers.CharField()


class ConfiguracaoComissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoComissao
        fields = [
            "id",
            "percentual_venda",
            "rateio_captador",
            "rateio_vendedor",
            "rateio_imobiliaria",
        ]

    def validate(self, attrs):
        soma = (
            attrs.get("rateio_captador", getattr(self.instance, "rateio_captador", 0))
            + attrs.get("rateio_vendedor", getattr(self.instance, "rateio_vendedor", 0))
            + attrs.get(
                "rateio_imobiliaria", getattr(self.instance, "rateio_imobiliaria", 0)
            )
        )
        if soma != 100:
            raise serializers.ValidationError(
                {"rateio_imobiliaria": f"O rateio deve somar 100% (soma atual: {soma}%)."}
            )
        return attrs
