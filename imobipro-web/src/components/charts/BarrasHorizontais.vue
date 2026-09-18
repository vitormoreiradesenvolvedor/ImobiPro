<script setup>
import { computed } from 'vue'

const props = defineProps({
  dados: { type: Object, required: true },
  formatador: { type: Function, default: (valor) => valor },
  limite: { type: Number, default: 8 },
})

// Gráfico em SVG/CSS puro: sem biblioteca externa, sem JS de terceiros e sem
// custo de bundle para mostrar meia dúzia de barras.
const linhas = computed(() => {
  const entradas = Object.entries(props.dados ?? {})
    .map(([rotulo, valor]) => ({ rotulo, valor: Number(valor) }))
    .sort((a, b) => b.valor - a.valor)
    .slice(0, props.limite)

  const maximo = Math.max(1, ...entradas.map((linha) => linha.valor))
  return entradas.map((linha) => ({
    ...linha,
    percentual: Math.round((linha.valor / maximo) * 100),
  }))
})
</script>

<template>
  <ul v-if="linhas.length" class="space-y-2.5">
    <li v-for="linha in linhas" :key="linha.rotulo" class="text-sm">
      <div class="flex items-baseline justify-between gap-3">
        <span class="truncate text-slate-600">{{ linha.rotulo }}</span>
        <span class="numerico font-medium text-slate-900">{{ formatador(linha.valor) }}</span>
      </div>
      <div class="mt-1 h-2 rounded-full bg-slate-100">
        <div class="h-2 rounded-full bg-marca" :style="{ width: `${linha.percentual}%` }" />
      </div>
    </li>
  </ul>
  <p v-else class="py-6 text-center text-sm text-slate-400">Sem dados no período.</p>
</template>
