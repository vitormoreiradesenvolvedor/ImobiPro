<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  rotulo: { type: String, default: '' },
})

// Cor por significado, não por módulo: verde = disponível/pago/ganho,
// âmbar = em andamento, vermelho = perdido/atrasado, cinza = encerrado.
const CORES = {
  DISPONIVEL: 'verde',
  ATIVO: 'verde',
  PAGA: 'verde',
  PAGO: 'verde',
  FECHADO_GANHO: 'verde',
  LIBERADA: 'verde',
  FINALIZADA: 'verde',
  ENVIADO: 'verde',
  EM_CAPTACAO: 'ambar',
  RESERVADO: 'ambar',
  ABERTA: 'ambar',
  PENDENTE: 'ambar',
  PREVISTA: 'ambar',
  RASCUNHO: 'ambar',
  NEGOCIACAO: 'ambar',
  PROPOSTA: 'ambar',
  ENVIADA: 'ambar',
  EM_ANALISE: 'ambar',
  ATRASADA: 'vermelho',
  FECHADO_PERDIDO: 'vermelho',
  RESCINDIDO: 'vermelho',
  RECUSADA: 'vermelho',
  ERRO: 'vermelho',
  CANCELADA: 'vermelho',
  CANCELADO: 'vermelho',
  VENDIDO: 'azul',
  LOCADO: 'azul',
  QUALIFICADO: 'azul',
  VISITA_AGENDADA: 'azul',
  VISITA_REALIZADA: 'azul',
  EM_CONTATO: 'azul',
  NOVO: 'azul',
}

const CLASSES = {
  verde: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  ambar: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  vermelho: 'bg-red-50 text-red-700 ring-red-600/20',
  azul: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  cinza: 'bg-slate-100 text-slate-600 ring-slate-500/20',
}

const classe = computed(() => CLASSES[CORES[props.status] ?? 'cinza'])
</script>

<template>
  <span
    class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset"
    :class="classe"
  >
    {{ rotulo || status }}
  </span>
</template>
