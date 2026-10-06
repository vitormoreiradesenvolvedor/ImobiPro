<script setup>
import { onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import BarrasHorizontais from '@/components/charts/BarrasHorizontais.vue'
import ColunasMensais from '@/components/charts/ColunasMensais.vue'
import { useToast } from '@/composables/useToast'
import { financeiroService, leadsService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { moeda } from '@/utils/formatters'

const { erroDaApi } = useToast()
const auth = useAuthStore()

const hoje = new Date().toISOString().slice(0, 10)
const inicio = ref(hoje.slice(0, 8) + '01')
const fim = ref(hoje)

const dre = ref(null)
const fluxo = ref([])
const desempenho = ref([])
const crm = ref(null)
const carregando = ref(true)

const colunasDesempenho = [
  { campo: 'corretor', rotulo: 'Corretor' },
  { campo: 'leads', rotulo: 'Leads', alinhamento: 'direita' },
  { campo: 'ganhos', rotulo: 'Ganhos', alinhamento: 'direita' },
  { campo: 'conversao', rotulo: 'Conversão', alinhamento: 'direita' },
  { campo: 'imoveis_captados', rotulo: 'Captados', alinhamento: 'direita' },
  { campo: 'comissao_prevista', rotulo: 'Comissão prevista', alinhamento: 'direita' },
]

async function carregar() {
  carregando.value = true
  try {
    const [resultado, serie, corretores, funil] = await Promise.all([
      financeiroService.relatorio('dre', { inicio: inicio.value, fim: fim.value }),
      financeiroService.relatorio('fluxo'),
      financeiroService.relatorio('desempenho-corretores'),
      auth.pode('ver_crm') ? leadsService.estatisticas() : Promise.resolve({ data: null }),
    ])
    dre.value = resultado.data
    fluxo.value = serie.data
    desempenho.value = corretores.data
    crm.value = funil.data
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível carregar os relatórios.')
  } finally {
    carregando.value = false
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-6">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Relatórios</h1>
        <p class="text-sm text-slate-500">DRE, fluxo de caixa, funil e desempenho da equipe</p>
      </div>
      <div class="flex items-end gap-3">
        <div class="w-40"><BaseInput v-model="inicio" rotulo="De" tipo="date" /></div>
        <div class="w-40"><BaseInput v-model="fim" rotulo="Até" tipo="date" /></div>
        <BaseButton @click="carregar">Atualizar</BaseButton>
      </div>
    </header>

    <p v-if="carregando" class="py-10 text-center text-slate-400">Calculando…</p>

    <template v-else>
      <section v-if="dre" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm text-slate-500">Receita operacional</p>
          <p class="numerico mt-1 text-2xl font-bold text-slate-900">
            {{ moeda(dre.receita_operacional) }}
          </p>
        </div>
        <div class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm text-slate-500">Despesa operacional</p>
          <p class="numerico mt-1 text-2xl font-bold text-slate-900">
            {{ moeda(dre.despesa_operacional) }}
          </p>
        </div>
        <div class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm text-slate-500">Resultado</p>
          <p
            class="numerico mt-1 text-2xl font-bold"
            :class="Number(dre.resultado) >= 0 ? 'text-emerald-600' : 'text-red-600'"
          >
            {{ moeda(dre.resultado) }}
          </p>
          <p class="text-xs text-slate-400">margem {{ dre.margem_percentual }}%</p>
        </div>
        <div class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm text-slate-500">Volume movimentado</p>
          <p class="numerico mt-1 text-2xl font-bold text-slate-900">
            {{ moeda(dre.volume_movimentado) }}
          </p>
          <p class="text-xs text-slate-400">inclui dinheiro de terceiros</p>
        </div>
      </section>

      <div class="grid gap-4 lg:grid-cols-2">
        <BaseCard
          titulo="Receita x despesa"
          subtitulo="Últimos 12 meses, sem valores de passagem"
        >
          <ColunasMensais :serie="fluxo" />
        </BaseCard>

        <BaseCard titulo="Receitas por categoria">
          <BarrasHorizontais :dados="dre?.por_categoria?.RECEITA ?? {}" :formatador="moeda" />
        </BaseCard>

        <BaseCard v-if="crm" titulo="Origem dos leads">
          <BarrasHorizontais :dados="crm.por_origem" />
        </BaseCard>

        <BaseCard v-if="crm" titulo="Motivos de perda">
          <BarrasHorizontais :dados="crm.por_motivo_perda" />
        </BaseCard>
      </div>

      <BaseCard titulo="Desempenho por corretor">
        <BaseTable :colunas="colunasDesempenho" :linhas="desempenho" chave="corretor">
          <template #conversao="{ linha }">{{ linha.conversao }}%</template>
          <template #comissao_prevista="{ linha }">
            {{ moeda(linha.comissao_prevista) }}
          </template>
        </BaseTable>
      </BaseCard>
    </template>
  </div>
</template>
