<script setup>
import { computed } from 'vue'

import { moeda } from '@/utils/formatters'

const props = defineProps({
  serie: { type: Array, default: () => [] },
})

const colunas = computed(() => {
  const maximo = Math.max(
    1,
    ...props.serie.flatMap((mes) => [Number(mes.receita ?? 0), Number(mes.despesa ?? 0)]),
  )

  return props.serie.map((mes) => ({
    rotulo: mes.mes?.slice(5) ?? '',
    receita: Number(mes.receita ?? 0),
    despesa: Number(mes.despesa ?? 0),
    alturaReceita: Math.round((Number(mes.receita ?? 0) / maximo) * 100),
    alturaDespesa: Math.round((Number(mes.despesa ?? 0) / maximo) * 100),
  }))
})
</script>

<template>
  <div v-if="colunas.length" class="space-y-3">
    <div class="flex h-48 items-end gap-2 overflow-x-auto">
      <div
        v-for="mes in colunas"
        :key="mes.rotulo"
        class="flex min-w-10 flex-1 flex-col items-center"
      >
        <div class="flex h-40 w-full items-end justify-center gap-1">
          <div
            class="w-1/2 rounded-t bg-marca"
            :style="{ height: `${mes.alturaReceita}%` }"
            :title="`Receita: ${moeda(mes.receita)}`"
          />
          <div
            class="w-1/2 rounded-t bg-slate-300"
            :style="{ height: `${mes.alturaDespesa}%` }"
            :title="`Despesa: ${moeda(mes.despesa)}`"
          />
        </div>
        <span class="mt-1 text-[10px] text-slate-500">{{ mes.rotulo }}</span>
      </div>
    </div>
    <div class="flex gap-4 text-xs text-slate-600">
      <span class="flex items-center gap-1.5">
        <span class="size-2.5 rounded-sm bg-marca" aria-hidden="true" /> Receita
      </span>
      <span class="flex items-center gap-1.5">
        <span class="size-2.5 rounded-sm bg-slate-300" aria-hidden="true" /> Despesa
      </span>
    </div>
  </div>
  <p v-else class="py-6 text-center text-sm text-slate-400">Sem movimento registrado.</p>
</template>
