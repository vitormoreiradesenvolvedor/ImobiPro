from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import TenantQuerySetMixin
from apps.pessoas.models import Pessoa
from apps.pessoas.serializers import ConsultaCepSerializer, PessoaSerializer
from apps.pessoas.services import CepNaoEncontrado, consultar_cep


class PessoaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Proprietários, inquilinos, compradores e fiadores da imobiliária."""

    queryset = Pessoa.objects.select_related("endereco").filter(deletado_em__isnull=True)
    serializer_class = PessoaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tipo"]
    search_fields = ["nome", "cpf_cnpj", "email", "telefone"]
    ordering_fields = ["nome", "criado_em"]

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {"foto": {"type": "string", "format": "binary"}},
            }
        },
        responses={200: PessoaSerializer},
    )
    @action(
        detail=True,
        methods=["post", "delete"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def foto(self, request, pk=None):
        """Envia ou remove a foto do cadastro. Sempre opcional.

        Fica fora do PUT do cadastro de propósito: o formulário manda JSON com
        endereço aninhado, e misturar arquivo nesse corpo obrigaria a serializar
        o endereço à mão em toda gravação.
        """

        pessoa = self.get_object()

        if request.method == "DELETE":
            pessoa.foto.delete(save=True)
            return Response(self.get_serializer(pessoa).data)

        arquivo = request.FILES.get("foto")
        if not arquivo:
            raise ValidationError({"foto": "Envie um arquivo de imagem."})

        pessoa.foto = arquivo
        pessoa.save(update_fields=["foto", "atualizado_em"])
        return Response(self.get_serializer(pessoa).data)

    @extend_schema(responses={200: PessoaSerializer(many=True)})
    @action(detail=False, methods=["get"])
    def proprietarios(self, request):
        """Atalho da tela de captação: quem já tem imóvel cadastrado."""
        pessoas = (
            self.filter_queryset(self.get_queryset())
            .filter(imoveis__isnull=False)
            .distinct()
        )
        pagina = self.paginate_queryset(pessoas)
        serializer = self.get_serializer(pagina or pessoas, many=True)
        return (
            self.get_paginated_response(serializer.data)
            if pagina
            else Response(serializer.data)
        )


@extend_schema(
    parameters=[OpenApiParameter("cep", str, OpenApiParameter.PATH)],
    responses={200: ConsultaCepSerializer, 404: ConsultaCepSerializer},
)
class ConsultaCepView(APIView):
    """GET /api/v1/pessoas/cep/{cep}/ preenche o formulário de endereço."""

    serializer_class = ConsultaCepSerializer

    def get(self, request, cep):
        try:
            return Response(consultar_cep(cep))
        except CepNaoEncontrado as erro:
            return Response(
                {"detail": str(erro), "code": "cep_nao_encontrado", "campos": {}},
                status=status.HTTP_404_NOT_FOUND,
            )
