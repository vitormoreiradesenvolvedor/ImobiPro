from rest_framework import serializers

from apps.crm.models import (
    EstagioLead,
    Interacao,
    Lead,
    MotivoPerda,
    Proposta,
    Visita,
)
from apps.imoveis.serializers import ImovelListSerializer

# Nome do corretor vem do usuário ligado ao lead, em todas as listagens.
FONTE_NOME_CORRETOR = "corretor.nome_completo"


class InteracaoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = Interacao
        fields = ["id", "tipo", "tipo_display", "descricao", "usuario_nome", "criado_em"]
        read_only_fields = ["id", "criado_em", "usuario_nome"]


class LeadListSerializer(serializers.ModelSerializer):
    """Cartão do kanban: leve, mas com tudo que o corretor precisa ver."""

    estagio_display = serializers.CharField(source="get_estagio_display", read_only=True)
    origem_display = serializers.CharField(source="get_origem_display", read_only=True)
    corretor_nome = serializers.CharField(source=FONTE_NOME_CORRETOR, read_only=True)
    imovel_codigo = serializers.CharField(source="imovel_interesse.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel_interesse.titulo", read_only=True)
    minutos_para_sla = serializers.FloatField(read_only=True)
    sla_estourado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "nome",
            "email",
            "telefone",
            "origem",
            "origem_display",
            "estagio",
            "estagio_display",
            "temperatura",
            "valor_estimado",
            "corretor",
            "corretor_nome",
            "imovel_interesse",
            "imovel_codigo",
            "imovel_titulo",
            "minutos_para_sla",
            "sla_estourado",
            "primeiro_contato_em",
            "criado_em",
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    estagio_display = serializers.CharField(source="get_estagio_display", read_only=True)
    origem_display = serializers.CharField(source="get_origem_display", read_only=True)
    motivo_perda_display = serializers.CharField(
        source="get_motivo_perda_display", read_only=True
    )
    corretor_nome = serializers.CharField(source=FONTE_NOME_CORRETOR, read_only=True)
    imovel_detalhe = ImovelListSerializer(source="imovel_interesse", read_only=True)
    interacoes = InteracaoSerializer(many=True, read_only=True)
    minutos_para_sla = serializers.FloatField(read_only=True)
    sla_estourado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id",
            "nome",
            "email",
            "telefone",
            "origem",
            "origem_display",
            "mensagem",
            "estagio",
            "estagio_display",
            "temperatura",
            "valor_estimado",
            "corretor",
            "corretor_nome",
            "imovel_interesse",
            "imovel_detalhe",
            "motivo_perda",
            "motivo_perda_display",
            "observacao_perda",
            "primeiro_contato_em",
            "sla_cumprido",
            "minutos_para_sla",
            "sla_estourado",
            "atribuido_em",
            "fechado_em",
            "interacoes",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "estagio",
            "motivo_perda",
            "observacao_perda",
            "primeiro_contato_em",
            "sla_cumprido",
            "atribuido_em",
            "fechado_em",
            "criado_em",
            "atualizado_em",
        ]


class MovimentacaoLeadSerializer(serializers.Serializer):
    estagio = serializers.ChoiceField(choices=EstagioLead.choices)
    motivo_perda = serializers.ChoiceField(
        choices=MotivoPerda.choices, required=False, allow_blank=True
    )
    observacao = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AtribuicaoLeadSerializer(serializers.Serializer):
    corretor_id = serializers.UUIDField()


class ColunaFunilSerializer(serializers.Serializer):
    estagio = serializers.CharField()
    rotulo = serializers.CharField()
    total = serializers.IntegerField()
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    leads = LeadListSerializer(many=True)


class EstatisticasCrmSerializer(serializers.Serializer):
    total_geral = serializers.IntegerField()
    abertos = serializers.IntegerField()
    ganhos = serializers.IntegerField()
    perdidos = serializers.IntegerField()
    taxa_conversao = serializers.FloatField()
    sla_cumprido_percentual = serializers.FloatField()
    tempo_medio_primeiro_contato_min = serializers.FloatField()
    por_estagio = serializers.DictField(child=serializers.IntegerField())
    por_origem = serializers.DictField(child=serializers.IntegerField())
    por_corretor = serializers.DictField(child=serializers.IntegerField())
    por_motivo_perda = serializers.DictField(child=serializers.IntegerField())
    valor_em_negociacao = serializers.DecimalField(max_digits=14, decimal_places=2)


class VisitaSerializer(serializers.ModelSerializer):
    lead_nome = serializers.CharField(source="lead.nome", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    corretor_nome = serializers.CharField(source=FONTE_NOME_CORRETOR, read_only=True)
    atrasada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Visita
        fields = [
            "id",
            "lead",
            "lead_nome",
            "imovel",
            "imovel_codigo",
            "imovel_titulo",
            "corretor",
            "corretor_nome",
            "agendada_para",
            "realizada",
            "cancelada",
            "feedback",
            "interesse_pos_visita",
            "atrasada",
            "criado_em",
        ]
        read_only_fields = [
            "id",
            "realizada",
            "feedback",
            "interesse_pos_visita",
            "criado_em",
        ]


class FeedbackVisitaSerializer(serializers.Serializer):
    feedback = serializers.CharField(max_length=2000)
    interesse_pos_visita = serializers.ChoiceField(
        choices=["ALTO", "MEDIO", "BAIXO"], required=False, allow_blank=True
    )


class PropostaSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lead_nome = serializers.CharField(source="lead.nome", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    desconto_percentual = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    expirada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Proposta
        fields = [
            "id",
            "lead",
            "lead_nome",
            "imovel",
            "imovel_codigo",
            "valor_ofertado",
            "condicoes_pagamento",
            "validade",
            "status",
            "status_display",
            "desconto_percentual",
            "expirada",
            "observacao_resposta",
            "respondida_em",
            "criado_em",
        ]
        read_only_fields = [
            "id",
            "status",
            "respondida_em",
            "observacao_resposta",
            "criado_em",
        ]


class RespostaPropostaSerializer(serializers.Serializer):
    motivo = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ContatoPublicoSerializer(serializers.Serializer):
    """Formulário do site da imobiliária entrada de lead sem autenticação."""

    nome = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    telefone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    mensagem = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    imovel_codigo = serializers.CharField(required=False, allow_blank=True, max_length=20)

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("telefone"):
            raise serializers.ValidationError(
                "Informe e-mail ou telefone para que possamos responder."
            )
        return attrs
