<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useListagem } from '@/composables/useListagem'
import { vistoriasService } from '@/services/api'
import { data as formatarData } from '@/utils/formatters'

const router = useRouter()

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(vistoriasService.listar, { filtrosIniciais: { tipo: '', status: '' } })

const colunas = [
  { campo: 'contrato_numero', rotulo: 'Contrato' },
  { campo: 'imovel_codigo', rotulo: 'Imóvel' },
  { campo: 'tipo_display', rotulo: 'Tipo' },
  { campo: 'realizada_em', rotulo: 'Data' },
  { campo: 'itens', rotulo: 'Itens', alinhamento: 'direita' },
  { campo: 'status', rotulo: 'Status' },
]

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Vistorias</h1>
        <p class="text-sm text-slate-500">
          Entrada, periódica e saída o comparativo resolve disputa de caução
        </p>
      </div>
      <div class="flex gap-3">
        <div class="w-40">
          <BaseSelect
            v-model="filtros.tipo"
            rotulo="Tipo"
            :opcoes="['ENTRADA', 'PERIODICA', 'SAIDA']"
            placeholder="Todos"
          />
        </div>
        <div class="w-40">
          <BaseSelect
            v-model="filtros.status"
            rotulo="Status"
            :opcoes="['RASCUNHO', 'FINALIZADA']"
            placeholder="Todos"
          />
        </div>
      </div>
    </header>

    <DataEmptyState
      v-if="vazio"
      icone="☑"
      titulo="Nenhuma vistoria"
      descricao="Crie a vistoria a partir da ficha do contrato de locação."
    />

    <template v-else>
      <BaseTable
        :colunas="colunas"
        :linhas="itens"
        :carregando="carregando"
        @selecionar="(linha) => router.push({ name: 'vistoria', params: { id: linha.id } })"
      >
        <template #realizada_em="{ linha }">{{ formatarData(linha.realizada_em) }}</template>
        <template #itens="{ linha }">
          {{ linha.total_itens }}
          <span v-if="linha.itens_com_problema" class="text-red-600">
            ({{ linha.itens_com_problema }} com avaria)
          </span>
        </template>
        <template #status="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>
  </div>
</template>
