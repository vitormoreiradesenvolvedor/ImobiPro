from django_filters import rest_framework as filters

from apps.crm.models import ESTAGIOS_FECHADOS, Lead, Visita


class LeadFilter(filters.FilterSet):
    corretor = filters.CharFilter(method="filtrar_corretor")
    aberto = filters.BooleanFilter(method="filtrar_aberto")
    criado_de = filters.DateFilter(field_name="criado_em", lookup_expr="date__gte")
    criado_ate = filters.DateFilter(field_name="criado_em", lookup_expr="date__lte")
    sem_contato = filters.BooleanFilter(
        field_name="primeiro_contato_em", lookup_expr="isnull"
    )

    class Meta:
        model = Lead
        fields = ["estagio", "origem", "temperatura", "imovel_interesse", "motivo_perda"]

    def filtrar_corretor(self, queryset, nome, valor):
        if valor == "me":
            return queryset.filter(corretor=self.request.user)
        if valor in {"nenhum", "sem"}:
            return queryset.filter(corretor__isnull=True)
        return queryset.filter(corretor_id=valor)

    def filtrar_aberto(self, queryset, nome, valor):
        if valor:
            return queryset.exclude(estagio__in=ESTAGIOS_FECHADOS)
        return queryset.filter(estagio__in=ESTAGIOS_FECHADOS)


class VisitaFilter(filters.FilterSet):
    data = filters.DateFilter(field_name="agendada_para", lookup_expr="date")
    de = filters.DateFilter(field_name="agendada_para", lookup_expr="date__gte")
    ate = filters.DateFilter(field_name="agendada_para", lookup_expr="date__lte")
    corretor = filters.CharFilter(method="filtrar_corretor")

    class Meta:
        model = Visita
        fields = ["realizada", "cancelada", "imovel", "lead"]

    def filtrar_corretor(self, queryset, nome, valor):
        if valor == "me":
            return queryset.filter(corretor=self.request.user)
        return queryset.filter(corretor_id=valor)
