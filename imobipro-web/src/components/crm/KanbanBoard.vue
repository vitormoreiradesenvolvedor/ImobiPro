<script setup>
import { ref } from 'vue'

import KanbanCard from '@/components/crm/KanbanCard.vue'
import { moeda } from '@/utils/formatters'

defineProps({ colunas: { type: Array, required: true } })
const emit = defineEmits(['mover'])

const arrastado = ref(null)
const colunaAlvo = ref(null)

function aoSoltar(estagio) {
  colunaAlvo.value = null
  if (!arrastado.value || arrastado.value.estagio === estagio) return

  emit('mover', { lead: arrastado.value, estagio })
  arrastado.value = null
}
</script>

<template>
  <!-- Drag-and-drop nativo do HTML: sem dependência extra para o kanban. -->
  <div class="flex gap-4 overflow-x-auto pb-4">
    <section
      v-for="coluna in colunas"
      :key="coluna.estagio"
      class="flex w-72 shrink-0 flex-col rounded-xl bg-slate-100 p-3 transition"
      :class="colunaAlvo === coluna.estagio ? 'ring-2 ring-marca' : ''"
      @dragover.prevent="colunaAlvo = coluna.estagio"
      @dragleave="colunaAlvo = null"
      @drop="aoSoltar(coluna.estagio)"
    >
      <header class="mb-3 flex items-baseline justify-between gap-2">
        <h3 class="text-sm font-semibold text-slate-700">{{ coluna.rotulo }}</h3>
        <span class="rounded-full bg-white px-2 py-0.5 text-xs text-slate-600">
          {{ coluna.total }}
        </span>
      </header>

      <p class="numerico mb-3 text-xs text-slate-500">{{ moeda(coluna.valor_total) }}</p>

      <div class="flex flex-col gap-2">
        <div
          v-for="lead in coluna.leads"
          :key="lead.id"
          draggable="true"
          @dragstart="arrastado = lead"
          @dragend="arrastado = null"
        >
          <KanbanCard :lead="lead" />
        </div>

        <p
          v-if="!coluna.leads.length"
          class="rounded-lg border border-dashed border-slate-300 py-6 text-center text-xs text-slate-400"
        >
          Arraste um lead para cá
        </p>
      </div>
    </section>
  </div>
</template>
