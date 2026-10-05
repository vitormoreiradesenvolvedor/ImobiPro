<script setup>
import { dataHora } from '@/utils/formatters'

defineProps({ interacoes: { type: Array, default: () => [] } })

const ICONES = {
  LIGACAO: '📞',
  EMAIL: '✉️',
  WHATSAPP: '💬',
  VISITA: '🏠',
  PROPOSTA: '📄',
  NOTA: '📝',
  SISTEMA: '⚙️',
}
</script>

<template>
  <ol class="relative space-y-4 border-l border-slate-200 pl-6">
    <li v-for="interacao in interacoes" :key="interacao.id" class="relative">
      <span
        class="absolute -left-[31px] flex size-6 items-center justify-center rounded-full bg-white text-xs ring-1 ring-slate-200"
        aria-hidden="true"
      >
        {{ ICONES[interacao.tipo] ?? '•' }}
      </span>
      <div class="flex flex-wrap items-baseline gap-x-2">
        <span class="text-sm font-medium text-slate-900">{{ interacao.tipo_display }}</span>
        <span class="text-xs text-slate-400">{{ dataHora(interacao.criado_em) }}</span>
        <span v-if="interacao.usuario_nome" class="text-xs text-slate-400">
          · {{ interacao.usuario_nome }}
        </span>
      </div>
      <p class="mt-0.5 whitespace-pre-line text-sm text-slate-600">{{ interacao.descricao }}</p>
    </li>

    <li v-if="!interacoes.length" class="text-sm text-slate-400">
      Nenhuma interação registrada. O relógio do SLA para no primeiro contato.
    </li>
  </ol>
</template>
