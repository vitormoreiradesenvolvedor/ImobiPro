<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { moeda } from '@/utils/formatters'

const props = defineProps({ lead: { type: Object, required: true } })

const TEMPERATURAS = { QUENTE: '🔥', MORNO: '🌤', FRIO: '❄️' }

// Vermelho pulsante quando o SLA já estourou; âmbar quando falta pouco.
const alertaSla = computed(() => {
  if (props.lead.primeiro_contato_em) return null
  const minutos = props.lead.minutos_para_sla
  if (minutos == null) return null
  if (minutos < 0) return 'estourado'
  return minutos <= 5 ? 'atencao' : null
})

const textoSla = computed(() => {
  const minutos = props.lead.minutos_para_sla
  if (minutos == null) return ''
  return minutos < 0
    ? `SLA estourado há ${Math.abs(Math.round(minutos))} min`
    : `${Math.round(minutos)} min para o 1º contato`
})
</script>

<template>
  <RouterLink
    :to="{ name: 'lead-detalhe', params: { id: lead.id } }"
    class="block rounded-lg bg-white p-3 text-sm shadow-sm ring-1 transition"
    :class="{
      'ring-slate-200 hover:ring-marca': !alertaSla,
      'ring-2 ring-red-500 animate-pulse': alertaSla === 'estourado',
      'ring-2 ring-amber-400': alertaSla === 'atencao',
    }"
  >
    <div class="flex items-start justify-between gap-2">
      <span class="font-medium text-slate-900">{{ lead.nome }}</span>
      <span :title="lead.temperatura" aria-hidden="true">
        {{ TEMPERATURAS[lead.temperatura] }}
      </span>
    </div>

    <p v-if="lead.imovel_codigo" class="mt-1 truncate text-xs text-slate-500">
      {{ lead.imovel_codigo }} · {{ lead.imovel_titulo }}
    </p>

    <div class="mt-2 flex items-center justify-between gap-2">
      <span class="numerico text-sm font-semibold text-slate-800">
        {{ moeda(lead.valor_estimado) }}
      </span>
      <span class="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
        {{ lead.origem_display }}
      </span>
    </div>

    <p
      v-if="alertaSla"
      class="mt-2 text-xs font-medium"
      :class="alertaSla === 'estourado' ? 'text-red-600' : 'text-amber-600'"
    >
      {{ textoSla }}
    </p>
    <p v-else-if="lead.corretor_nome" class="mt-2 truncate text-xs text-slate-400">
      {{ lead.corretor_nome }}
    </p>
  </RouterLink>
</template>
