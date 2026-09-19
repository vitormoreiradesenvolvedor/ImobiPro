<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import BaseCard from '@/components/base/BaseCard.vue'
import BarrasHorizontais from '@/components/charts/BarrasHorizontais.vue'
import KanbanCard from '@/components/crm/KanbanCard.vue'
import {
  cobrancasService,
  imoveisService,
  financeiroService,
  leadsService,
  visitasService,
} from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { moeda } from '@/utils/formatters'

const auth = useAuthStore()

const carteira = ref(null)
const crm = ref(null)
const financeiro = ref(null)
const visitasHoje = ref([])
const semContato = ref([])
const atrasadas = ref([])
const carregando = ref(true)

async function carregarComTolerancia(chamada, padrao = null) {
  // O corretor não enxerga o financeiro: 403 aqui é resposta esperada, não erro.
  try {
    const { data } = await chamada()
    return data
  } catch {
    return padrao
  }
}

onMounted(async () => {
  const [imoveis, leads, resumo, agenda, pendentes, emAtraso] = await Promise.all([
    carregarComTolerancia(imoveisService.estatisticas),
    carregarComTolerancia(leadsService.estatisticas),
    carregarComTolerancia(financeiroService.resumo),
    carregarComTolerancia(
      () => visitasService.agenda(new Date().toISOString().slice(0, 10)),
      [],
    ),
    carregarComTolerancia(
      () => leadsService.listar({ sem_contato: true, aberto: true, page_size: 5 }),
      { results: [] },
    ),
    carregarComTolerancia(() => cobrancasService.listar({ em_atraso: true, page_size: 5 }), {
      results: [],
    }),
  ])

  carteira.value = imoveis
  crm.value = leads
  financeiro.value = resumo
  visitasHoje.value = agenda ?? []
  semContato.value = pendentes?.results ?? []
  atrasadas.value = emAtraso?.results ?? []
  carregando.value = false
})
</script>

<template>
  <div class="space-y-6">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">
        Olá, {{ auth.usuario?.nome_completo?.split(' ')[0] }}
      </h1>
      <p class="text-sm text-slate-500">
        {{ auth.tenant?.razao_social }} · {{ auth.usuario?.papel_display }}
      </p>
    </header>

    <p v-if="carregando" class="py-10 text-center text-slate-400">Carregando indicadores…</p>

    <template v-else>
      <section data-tour="kpis" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div v-if="financeiro" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">Resultado do mês</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">
            {{ moeda(financeiro.resultado_do_mes) }}
          </p>
          <p class="mt-1 text-xs text-slate-400">
            receita {{ moeda(financeiro.receita_do_mes) }}
          </p>
        </div>

        <div v-if="financeiro" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">A receber</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">
            {{ moeda(financeiro.a_receber) }}
          </p>
          <p class="mt-1 text-xs text-red-500">
            {{ moeda(financeiro.a_receber_vencido) }} vencido
          </p>
        </div>

        <div v-if="financeiro" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">Inadimplência</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">
            {{ financeiro.inadimplencia.percentual }}%
          </p>
          <p class="mt-1 text-xs text-slate-400">
            {{ financeiro.inadimplencia.atrasadas }} cobranças em atraso
          </p>
        </div>

        <div v-if="carteira" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">Carteira à venda</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">
            {{ moeda(carteira.carteira_venda) }}
          </p>
          <p class="mt-1 text-xs text-slate-400">
            {{ carteira.total_geral }} imóveis · {{ carteira.publicados }} publicados
          </p>
        </div>

        <div v-if="crm" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">Leads abertos</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">{{ crm.abertos }}</p>
          <p class="mt-1 text-xs text-slate-400">conversão {{ crm.taxa_conversao }}%</p>
        </div>

        <div v-if="crm" class="rounded-xl bg-white p-5 ring-1 ring-slate-200">
          <p class="text-sm font-medium text-slate-500">SLA cumprido</p>
          <p class="numerico mt-2 text-3xl font-bold text-slate-900">
            {{ crm.sla_cumprido_percentual }}%
          </p>
          <p class="mt-1 text-xs text-slate-400">
            1º contato em {{ crm.tempo_medio_primeiro_contato_min }} min, em média
          </p>
        </div>
      </section>

      <BaseCard
        data-tour="precisa-hoje"
        titulo="Precisa de você hoje"
        subtitulo="O que trava dinheiro se ficar parado"
      >
        <div class="grid gap-6 lg:grid-cols-3">
          <div>
            <h3 class="mb-2 text-sm font-semibold text-slate-700">
              Leads sem primeiro contato
            </h3>
            <div v-if="semContato.length" class="space-y-2">
              <KanbanCard v-for="lead in semContato" :key="lead.id" :lead="lead" />
            </div>
            <p v-else class="text-sm text-slate-400">Nenhum lead esperando. Bom trabalho.</p>
          </div>

          <div>
            <h3 class="mb-2 text-sm font-semibold text-slate-700">Visitas de hoje</h3>
            <ul v-if="visitasHoje.length" class="space-y-2 text-sm">
              <li
                v-for="visita in visitasHoje"
                :key="visita.id"
                class="rounded-lg bg-slate-50 p-3"
              >
                <span class="font-medium">{{ visita.lead_nome }}</span>
                <span class="text-slate-500"> · {{ visita.imovel_codigo }}</span>
              </li>
            </ul>
            <p v-else class="text-sm text-slate-400">Nenhuma visita agendada para hoje.</p>
          </div>

          <div>
            <h3 class="mb-2 text-sm font-semibold text-slate-700">Cobranças em atraso</h3>
            <ul v-if="atrasadas.length" class="space-y-2 text-sm">
              <li
                v-for="cobranca in atrasadas"
                :key="cobranca.id"
                class="flex justify-between rounded-lg bg-red-50 p-3"
              >
                <span>{{ cobranca.inquilino ?? cobranca.contrato_numero }}</span>
                <span class="numerico font-medium text-red-700">
                  {{ moeda(cobranca.valor_total) }}
                </span>
              </li>
            </ul>
            <p v-else class="text-sm text-slate-400">Nada em atraso.</p>
          </div>
        </div>
      </BaseCard>

      <div class="grid gap-4 lg:grid-cols-2">
        <BaseCard v-if="crm" titulo="Funil por estágio">
          <BarrasHorizontais :dados="crm.por_estagio" />
          <RouterLink
            :to="{ name: 'crm' }"
            class="mt-4 inline-block text-sm font-medium text-marca"
          >
            Abrir o kanban →
          </RouterLink>
        </BaseCard>

        <BaseCard v-if="carteira" titulo="Imóveis por bairro">
          <BarrasHorizontais :dados="carteira.por_bairro" />
        </BaseCard>
      </div>
    </template>
  </div>
</template>
