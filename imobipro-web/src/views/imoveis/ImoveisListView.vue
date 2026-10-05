<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import ImovelCard from '@/components/imoveis/ImovelCard.vue'
import MapaImoveis from '@/components/imoveis/MapaImoveis.vue'
import { useListagem } from '@/composables/useListagem'
import { imoveisService } from '@/services/api'
import { moeda } from '@/utils/formatters'

const MODOS = [
  { valor: 'grade', rotulo: 'Cards' },
  { valor: 'tabela', rotulo: 'Tabela' },
  { valor: 'mapa', rotulo: 'Mapa' },
]

const TIPOS = [
  'APARTAMENTO',
  'CASA',
  'CASA_CONDOMINIO',
  'COBERTURA',
  'KITNET',
  'TERRENO',
  'SALA_COMERCIAL',
  'GALPAO',
  'RURAL',
]

const SITUACOES = ['EM_CAPTACAO', 'DISPONIVEL', 'RESERVADO', 'VENDIDO', 'LOCADO', 'INATIVO']

const modo = ref('grade')
const doMapa = ref([])

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(imoveisService.listar, {
    filtrosIniciais: { search: '', tipo: '', finalidade: '', situacao: '', quartos_min: '' },
  })

const colunas = [
  { campo: 'codigo', rotulo: 'Código' },
  { campo: 'titulo', rotulo: 'Imóvel' },
  { campo: 'bairro', rotulo: 'Bairro' },
  { campo: 'situacao', rotulo: 'Situação' },
  { campo: 'valor', rotulo: 'Valor', alinhamento: 'direita' },
]

async function carregarMapa() {
  const { data } = await imoveisService.mapa(filtros.value)
  doMapa.value = data
}

watch(
  [modo, filtros],
  () => {
    if (modo.value === 'mapa') carregarMapa()
  },
  { deep: true },
)

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Imóveis</h1>
        <p class="text-sm text-slate-500">{{ total }} imóveis na carteira</p>
      </div>
      <div class="flex items-center gap-2">
        <fieldset data-tour="modos-visualizacao" class="flex rounded-lg bg-slate-100 p-1">
          <legend class="sr-only">Modo de exibição</legend>
          <button
            v-for="opcao in MODOS"
            :key="opcao.valor"
            type="button"
            class="rounded-md px-3 py-1.5 text-sm font-medium transition"
            :class="
              modo === opcao.valor ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'
            "
            :aria-pressed="modo === opcao.valor"
            @click="modo = opcao.valor"
          >
            {{ opcao.rotulo }}
          </button>
        </fieldset>
        <RouterLink :to="{ name: 'imovel-novo' }" data-tour="captar-imovel">
          <BaseButton>Captar imóvel</BaseButton>
        </RouterLink>
      </div>
    </header>

    <section
      data-tour="filtros-imoveis"
      class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-2 lg:grid-cols-5"
    >
      <BaseInput
        v-model="filtros.search"
        rotulo="Buscar"
        placeholder="código, título, bairro"
      />
      <BaseSelect v-model="filtros.tipo" rotulo="Tipo" :opcoes="TIPOS" placeholder="Todos" />
      <BaseSelect
        v-model="filtros.finalidade"
        rotulo="Finalidade"
        :opcoes="['VENDA', 'LOCACAO', 'VENDA_E_LOCACAO', 'TEMPORADA']"
        placeholder="Todas"
      />
      <BaseSelect
        v-model="filtros.situacao"
        rotulo="Situação"
        :opcoes="SITUACOES"
        placeholder="Todas"
      />
      <BaseSelect
        v-model="filtros.quartos_min"
        rotulo="Quartos (mín.)"
        :opcoes="['1', '2', '3', '4']"
        placeholder="Qualquer"
      />
    </section>

    <p v-if="carregando" class="py-10 text-center text-slate-400">Carregando imóveis…</p>

    <DataEmptyState
      v-else-if="vazio"
      icone="⌂"
      titulo="Nenhum imóvel encontrado"
      descricao="Ajuste os filtros ou cadastre a primeira captação da carteira."
    >
      <template #acao>
        <RouterLink :to="{ name: 'imovel-novo' }">
          <BaseButton>Captar imóvel</BaseButton>
        </RouterLink>
      </template>
    </DataEmptyState>

    <template v-else>
      <div
        v-if="modo === 'grade'"
        class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        <ImovelCard v-for="imovel in itens" :key="imovel.id" :imovel="imovel" />
      </div>

      <BaseTable
        v-else-if="modo === 'tabela'"
        :colunas="colunas"
        :linhas="itens"
        :carregando="carregando"
      >
        <template #situacao="{ linha }">
          <StatusBadge :status="linha.situacao" :rotulo="linha.situacao_display" />
        </template>
        <template #valor="{ linha }">
          {{ moeda(linha.valor_venda ?? linha.valor_locacao) }}
        </template>
      </BaseTable>

      <MapaImoveis v-else :imoveis="doMapa" />

      <PaginacaoSimples
        v-if="modo !== 'mapa'"
        v-model:pagina="pagina"
        :total-paginas="totalPaginas"
        :total="total"
      />
    </template>
  </div>
</template>
