"""Serializers da candidatura. O link do cliente mostra menos que a análise."""

from rest_framework import serializers

from apps.candidaturas.models import (
    Candidatura,
    DocumentoCandidatura,
    EventoCandidatura,
    StatusCandidatura,
    TipoDocumento,
)


class DocumentoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    conferido_por_nome = serializers.CharField(
        source="conferido_por.nome_completo", read_only=True
    )

    class Meta:
        model = DocumentoCandidatura
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "arquivo",
            "nome_original",
            "status",
            "status_display",
            "observacao",
            "conferido_por_nome",
            "conferido_em",
            "criado_em",
        ]
        read_only_fields = ["id", "status", "observacao", "conferido_em"]


class EventoCandidaturaSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = EventoCandidatura
        fields = ["id", "descricao", "usuario_nome", "visivel_ao_cliente", "criado_em"]


class CandidaturaListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    analista_nome = serializers.CharField(source="analista.nome_completo", read_only=True)
    documentacao_completa = serializers.BooleanField(read_only=True)
    relacao_renda_aluguel = serializers.FloatField(read_only=True)

    class Meta:
        model = Candidatura
        fields = [
            "id",
            "protocolo",
            "status",
            "status_display",
            "imovel",
            "imovel_codigo",
            "imovel_titulo",
            "pretendente_nome",
            "pretendente_telefone",
            "pretendente_email",
            "renda_mensal",
            "relacao_renda_aluguel",
            "analista",
            "analista_nome",
            "documentacao_completa",
            "criado_em",
        ]


class CandidaturaDetailSerializer(CandidaturaListSerializer):
    documentos = DocumentoSerializer(many=True, read_only=True)
    eventos = EventoCandidaturaSerializer(many=True, read_only=True)
    documentos_pendentes = serializers.SerializerMethodField()
    link_do_cliente = serializers.SerializerMethodField()
    contrato_numero = serializers.CharField(source="contrato.numero", read_only=True)

    class Meta(CandidaturaListSerializer.Meta):
        fields = CandidaturaListSerializer.Meta.fields + [
            "pretendente_cpf",
            "ocupacao",
            "observacoes",
            "documentos",
            "documentos_pendentes",
            "eventos",
            "link_do_cliente",
            "contrato",
            "contrato_numero",
            "motivo_decisao",
            "decidido_em",
        ]

    def get_documentos_pendentes(self, candidatura) -> list[dict]:
        return [
            {"valor": tipo.value, "rotulo": tipo.label}
            for tipo in candidatura.documentos_pendentes
        ]

    def get_link_do_cliente(self, candidatura) -> str:
        """URL que o corretor manda no WhatsApp para o pretendente."""

        requisicao = self.context.get("request")
        caminho = f"/candidatura/{candidatura.tenant.subdominio}/{candidatura.token}"
        return requisicao.build_absolute_uri(caminho) if requisicao else caminho


class AberturaCandidaturaSerializer(serializers.Serializer):
    imovel = serializers.UUIDField()
    ticket = serializers.UUIDField(required=False, allow_null=True)
    pretendente_nome = serializers.CharField(max_length=160)
    pretendente_cpf = serializers.CharField(max_length=14, required=False, allow_blank=True)
    pretendente_email = serializers.EmailField(required=False, allow_blank=True)
    pretendente_telefone = serializers.CharField(max_length=20)
    renda_mensal = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    ocupacao = serializers.CharField(max_length=120, required=False, allow_blank=True)
    observacoes = serializers.CharField(required=False, allow_blank=True)


class ConferenciaSerializer(serializers.Serializer):
    aprovado = serializers.BooleanField()
    observacao = serializers.CharField(required=False, allow_blank=True)


class DecisaoSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StatusCandidatura.choices)
    observacao = serializers.CharField(required=False, allow_blank=True)


class GeracaoContratoSerializer(serializers.Serializer):
    data_inicio = serializers.DateField()
    data_fim = serializers.DateField()
    valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    dia_vencimento = serializers.IntegerField(default=10, min_value=1, max_value=28)
    taxa_administracao_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, default=10
    )
    garantia_tipo = serializers.CharField(default="CAUCAO")
    garantia_valor = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class EnvioDocumentoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TipoDocumento.choices)
    arquivo = serializers.FileField()


class PortalCandidaturaSerializer(serializers.ModelSerializer):
    """O que o pretendente vê no link. Sem nota interna, sem dado de terceiro."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    imovel_codigo = serializers.CharField(source="imovel.codigo", read_only=True)
    imovel_titulo = serializers.CharField(source="imovel.titulo", read_only=True)
    imovel_valor = serializers.DecimalField(
        source="imovel.valor_locacao", max_digits=12, decimal_places=2, read_only=True
    )
    documentos = serializers.SerializerMethodField()
    documentos_pendentes = serializers.SerializerMethodField()
    eventos = serializers.SerializerMethodField()

    class Meta:
        model = Candidatura
        fields = [
            "protocolo",
            "status",
            "status_display",
            "imovel_codigo",
            "imovel_titulo",
            "imovel_valor",
            "pretendente_nome",
            "documentos",
            "documentos_pendentes",
            "eventos",
            "criado_em",
        ]

    def get_documentos(self, candidatura) -> list[dict]:
        return [
            {
                "id": str(documento.id),
                "tipo": documento.tipo,
                "tipo_display": documento.get_tipo_display(),
                "status": documento.status,
                "status_display": documento.get_status_display(),
                "observacao": documento.observacao,
                "criado_em": documento.criado_em,
            }
            for documento in candidatura.documentos.all()
        ]

    def get_documentos_pendentes(self, candidatura) -> list[dict]:
        return [
            {"valor": tipo.value, "rotulo": tipo.label}
            for tipo in candidatura.documentos_pendentes
        ]

    def get_eventos(self, candidatura) -> list[dict]:
        return EventoCandidaturaSerializer(
            [e for e in candidatura.eventos.all() if e.visivel_ao_cliente], many=True
        ).data
