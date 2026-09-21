<script setup>
import { onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useListagem } from '@/composables/useListagem'
import { contratosService } from '@/services/api'
import { data as formatarData, moeda } from '@/utils/formatters'

const router = useRouter()

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(contratosService.listar, {
    filtrosIniciais: { tipo: '', status: '', vencendo_em: '' },
  })

const colunas = [
  { campo: 'numero', rotulo: 'Número' },
  { campo: 'imovel_codigo', rotulo: 'Imóvel' },
  { campo: 'tipo', rotulo: 'Tipo' },
  { campo: 'vigencia', rotulo: 'Vigência' },
  { campo: 'status', rotulo: 'Status' },
  { campo: 'valor', rotulo: 'Valor', alinhamento: 'direita' },
]

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Contratos</h1>
        <p class="text-sm text-slate-500">{{ total }} contratos cadastrados</p>
      </div>
      <RouterLink :to="{ name: 'contrato-novo' }" data-tour="novo-contrato">
        <BaseButton>Novo contrato</BaseButton>
      </RouterLink>
    </header>

    <section
      class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-3"
      data-tour="filtros-contratos"
    >
      <BaseSelect
        v-model="filtros.tipo"
        rotulo="Tipo"
        :opcoes="['VENDA', 'LOCACAO']"
        placeholder="Todos"
      />
      <BaseSelect
        v-model="filtros.status"
        rotulo="Status"
        :opcoes="['RASCUNHO', 'ATIVO', 'ENCERRADO', 'RESCINDIDO']"
        placeholder="Todos"
      />
      <BaseSelect
        v-model="filtros.vencendo_em"
        rotulo="Vencendo em"
        :opcoes="[
          { value: '30', label: '30 dias' },
          { value: '60', label: '60 dias' },
          { value: '90', label: '90 dias' },
        ]"
        placeholder="Qualquer prazo"
      />
    </section>

    <DataEmptyState
      v-if="vazio"
      icone="✎"
      titulo="Nenhum contrato encontrado"
      descricao="Contratos nascem como rascunho e só valem depois de assinados."
    >
      <template #acao>
        <RouterLink :to="{ name: 'contrato-novo' }">
          <BaseButton>Novo contrato</BaseButton>
        </RouterLink>
      </template>
    </DataEmptyState>

    <template v-else>
      <BaseTable
        :colunas="colunas"
        :linhas="itens"
        :carregando="carregando"
        @selecionar="
          (linha) => router.push({ name: 'contrato-detalhe', params: { id: linha.id } })
        "
      >
        <template #tipo="{ linha }">{{ linha.tipo_display }}</template>
        <template #vigencia="{ linha }">
          {{ formatarData(linha.data_inicio) }}
          <template v-if="linha.data_fim"> a {{ formatarData(linha.data_fim) }}</template>
          <span
            v-if="linha.dias_para_vencer !== null && linha.dias_para_vencer <= 90"
            class="ml-1 text-xs text-amber-600"
          >
            ({{ linha.dias_para_vencer }} dias)
          </span>
        </template>
        <template #status="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #valor="{ linha }">{{ moeda(linha.valor) }}</template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>
  </div>
</template>
