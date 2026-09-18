<script setup>
defineProps({
  titulo: { type: String, default: 'Nada por aqui ainda' },
  descricao: { type: String, default: '' },
  icone: { type: String, default: '◌' },
})
</script>

<template>
  <!-- Estado vazio sempre com saída: tabela vazia sem ação é beco sem saída. -->
  <div
    class="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
  >
    <span class="mb-3 text-3xl text-slate-300" aria-hidden="true">{{ icone }}</span>
    <h3 class="text-sm font-semibold text-slate-900">{{ titulo }}</h3>
    <p v-if="descricao" class="mt-1 max-w-sm text-sm text-slate-500">{{ descricao }}</p>
    <div class="mt-4"><slot name="acao" /></div>
  </div>
</template>
