"""Serializers do atendimento. O que o cliente vê é menos do que o time vê."""

from rest_framework import serializers

from apps.atendimento.models import EventoTicket, StatusTicket, Ticket, TipoTicket


class EventoTicketSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = EventoTicket
        fields = ["id", "descricao", "usuario_nome", "visivel_ao_cliente", "criado_em"]


class TicketListSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    analista_nome = serializers.CharField(source="analista.nome_completo", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    sla_estourado = serializers.BooleanField(read_only=True)
    minutos_para_resposta = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id",
            "protocolo",
            "tipo",
            "tipo_display",
            "status",
            "status_display",
            "solicitante_nome",
            "solicitante_telefone",
            "solicitante_email",
            "imovel",
            "imovel_codigo",
            "imovel_titulo",
            "analista",
            "analista_nome",
            "preferencia_data",
            "preferencia_periodo",
            "agendado_para",
            "sla_estourado",
            "minutos_para_resposta",
            "criado_em",
        ]


class TicketDetailSerializer(TicketListSerializer):
    eventos = EventoTicketSerializer(many=True, read_only=True)
    lead_id = serializers.UUIDField(source="lead.id", read_only=True)

    class Meta(TicketListSerializer.Meta):
        fields = TicketListSerializer.Meta.fields + [
            "mensagem",
            "eventos",
            "lead_id",
            "primeira_resposta_em",
            "encerrado_em",
        ]


class AberturaTicketSerializer(serializers.Serializer):
    """Formulário do site. Pede o mínimo: nome, um contato e o que quer."""

    tipo = serializers.ChoiceField(choices=TipoTicket.choices, default=TipoTicket.VISITA)
    imovel_codigo = serializers.CharField(required=False, allow_blank=True)
    solicitante_nome = serializers.CharField(max_length=160)
    solicitante_email = serializers.EmailField(required=False, allow_blank=True)
    solicitante_telefone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    mensagem = serializers.CharField(required=False, allow_blank=True)
    preferencia_data = serializers.DateField(required=False, allow_null=True)
    preferencia_periodo = serializers.ChoiceField(
        choices=[("MANHA", "Manhã"), ("TARDE", "Tarde"), ("NOITE", "Noite")],
        required=False,
        allow_blank=True,
    )

    def validate(self, dados):
        if not dados.get("solicitante_email") and not dados.get("solicitante_telefone"):
            raise serializers.ValidationError(
                {"solicitante_telefone": "Informe um telefone ou um e-mail para retorno."}
            )
        return dados


class AcompanhamentoSerializer(serializers.ModelSerializer):
    """Consulta por protocolo: sem dado interno, sem contato de terceiros."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    atendido_por = serializers.CharField(source="analista.nome_completo", read_only=True)
    eventos = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "protocolo",
            "tipo_display",
            "status",
            "status_display",
            "imovel_codigo",
            "imovel_titulo",
            "atendido_por",
            "agendado_para",
            "criado_em",
            "eventos",
        ]

    def get_eventos(self, ticket):
        publicos = [e for e in ticket.eventos.all() if e.visivel_ao_cliente]
        return EventoTicketSerializer(publicos, many=True).data


class RespostaSerializer(serializers.Serializer):
    mensagem = serializers.CharField()
    visivel_ao_cliente = serializers.BooleanField(default=True)


class MudancaStatusTicketSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StatusTicket.choices)
    observacao = serializers.CharField(required=False, allow_blank=True)
    agendado_para = serializers.DateTimeField(required=False, allow_null=True)


class ReatribuicaoSerializer(serializers.Serializer):
    analista = serializers.UUIDField()
    motivo = serializers.CharField(required=False, allow_blank=True)
