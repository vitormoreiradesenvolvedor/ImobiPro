"""O que o cliente vê do próprio contrato. Menos do que a imobiliária vê."""

from rest_framework import serializers

from apps.atendimento.models import Ticket
from apps.contratos.models import Contrato
from apps.locacao.models import Cobranca
from apps.vistorias.models import Vistoria


class ContratoDoClienteSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    imovel_endereco = serializers.SerializerMethodField()
    papel_no_contrato = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = [
            "id",
            "numero",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "imovel_codigo",
            "imovel_titulo",
            "imovel_endereco",
            "valor",
            "dia_vencimento",
            "data_inicio",
            "data_fim",
            "proximo_reajuste_em",
            "indice_reajuste",
            "papel_no_contrato",
        ]

    def get_imovel_endereco(self, contrato):
        endereco = contrato.imovel.endereco
        rua = ", ".join(filter(None, [endereco.logradouro, endereco.numero]))
        return f"{rua} · {endereco.bairro} · {endereco.cidade}/{endereco.uf}"

    def get_papel_no_contrato(self, contrato):
        pessoa = self.context.get("pessoa")
        parte = contrato.partes.filter(pessoa=pessoa).first()
        return parte.get_papel_display() if parte else ""


class CobrancaDoClienteSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)
    dias_de_atraso = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cobranca
        fields = [
            "id",
            "contrato_numero",
            "competencia",
            "vencimento",
            "valor_aluguel",
            "valor_condominio",
            "valor_iptu",
            "valor_multa",
            "valor_juros",
            "valor_total",
            "valor_pago",
            "pago_em",
            "status",
            "status_display",
            "dias_de_atraso",
            "linha_digitavel",
            "pix_copia_cola",
        ]


class VistoriaDoClienteSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Vistoria
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "realizada_em",
            "total_itens",
            "itens_com_problema",
            "assinatura_locatario",
        ]


class ChamadoDoClienteSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    eventos = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "protocolo",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "mensagem",
            "agendado_para",
            "criado_em",
            "eventos",
        ]

    def get_eventos(self, ticket):
        return [
            {
                "descricao": evento.descricao,
                "criado_em": evento.criado_em,
            }
            for evento in ticket.eventos.all()
            if evento.visivel_ao_cliente
        ]


class AberturaChamadoSerializer(serializers.Serializer):
    """Chamado de manutenção do inquilino. Só precisa do que aconteceu."""

    mensagem = serializers.CharField()
    contrato = serializers.UUIDField(required=False, allow_null=True)
