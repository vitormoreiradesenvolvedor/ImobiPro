"""Filtros da busca de imóveis o que o corretor usa o dia inteiro."""

from django.db.models import F, FloatField, Q
from django.db.models.functions import ACos, Cos, Least, Radians, Sin
from django_filters import rest_framework as filters

from apps.imoveis.models import Imovel

RAIO_DA_TERRA_KM = 6371


class ImovelFilter(filters.FilterSet):
    quartos_min = filters.NumberFilter(field_name="quartos", lookup_expr="gte")
    suites_min = filters.NumberFilter(field_name="suites", lookup_expr="gte")
    banheiros_min = filters.NumberFilter(field_name="banheiros", lookup_expr="gte")
    vagas_min = filters.NumberFilter(field_name="vagas", lookup_expr="gte")
    area_min = filters.NumberFilter(field_name="area_util", lookup_expr="gte")
    area_max = filters.NumberFilter(field_name="area_util", lookup_expr="lte")

    valor_min = filters.NumberFilter(method="filtrar_valor_min")
    valor_max = filters.NumberFilter(method="filtrar_valor_max")

    cidade = filters.CharFilter(field_name="endereco__cidade", lookup_expr="iexact")
    bairro = filters.CharFilter(field_name="endereco__bairro", lookup_expr="icontains")

    caracteristicas = filters.CharFilter(method="filtrar_caracteristicas")
    captador = filters.CharFilter(method="filtrar_captador")

    raio_km = filters.NumberFilter(method="filtrar_raio")
    lat = filters.NumberFilter(method="sem_efeito")
    lng = filters.NumberFilter(method="sem_efeito")

    class Meta:
        model = Imovel
        fields = [
            "tipo",
            "finalidade",
            "situacao",
            "mobiliado",
            "aceita_pet",
            "publicado_site",
            "destaque",
        ]

    def sem_efeito(self, queryset, nome, valor):
        """lat/lng só fazem sentido junto com raio_km ver `filtrar_raio`."""
        return queryset

    def _campo_de_valor(self):
        """Filtra pelo valor certo conforme a finalidade pedida na busca."""
        finalidade = self.data.get("finalidade", "")
        if finalidade in {"LOCACAO", "TEMPORADA"}:
            return "valor_locacao"
        if finalidade == "VENDA":
            return "valor_venda"
        return None

    def filtrar_valor_min(self, queryset, nome, valor):
        campo = self._campo_de_valor()
        if campo:
            return queryset.filter(**{f"{campo}__gte": valor})
        return queryset.filter(Q(valor_venda__gte=valor) | Q(valor_locacao__gte=valor))

    def filtrar_valor_max(self, queryset, nome, valor):
        campo = self._campo_de_valor()
        if campo:
            return queryset.filter(**{f"{campo}__lte": valor})
        return queryset.filter(Q(valor_venda__lte=valor) | Q(valor_locacao__lte=valor))

    def filtrar_caracteristicas(self, queryset, nome, valor):
        """`?caracteristicas=piscina,elevador` exige TODAS as informadas."""
        for slug in [s.strip() for s in valor.split(",") if s.strip()]:
            queryset = queryset.filter(caracteristicas__slug=slug)
        return queryset.distinct()

    def filtrar_captador(self, queryset, nome, valor):
        if valor == "me":
            return queryset.filter(captador=self.request.user)
        return queryset.filter(captador_id=valor)

    def filtrar_raio(self, queryset, nome, valor):
        """Busca por raio usando a fórmula do grande círculo, direto no banco.

        Evita trazer a carteira inteira para a memória só para calcular distância.
        """

        try:
            lat = float(self.data.get("lat"))
            lng = float(self.data.get("lng"))
            raio = float(valor)
        except (TypeError, ValueError):
            return queryset

        cosseno = Sin(Radians(lat)) * Sin(Radians(F("endereco__latitude"))) + Cos(
            Radians(lat)
        ) * Cos(Radians(F("endereco__latitude"))) * Cos(
            Radians(F("endereco__longitude")) - Radians(lng)
        )

        return (
            queryset.exclude(endereco__latitude__isnull=True)
            .annotate(
                distancia_km=ACos(Least(cosseno, 1.0, output_field=FloatField()))
                * RAIO_DA_TERRA_KM
            )
            .filter(distancia_km__lte=raio)
            .order_by("distancia_km")
        )
