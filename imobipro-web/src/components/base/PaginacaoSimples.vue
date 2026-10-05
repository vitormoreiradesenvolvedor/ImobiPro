<script setup>
defineProps({
  pagina: { type: Number, required: true },
  totalPaginas: { type: Number, required: true },
  total: { type: Number, default: 0 },
})

const modelo = defineModel('pagina', { type: Number, required: true })
</script>

<template>
  <nav
    v-if="totalPaginas > 1"
    class="flex items-center justify-between gap-4 py-3"
    aria-label="Paginação"
  >
    <p class="text-sm text-slate-500">
      Página {{ modelo }} de {{ totalPaginas }} · {{ total }} registros
    </p>
    <div class="flex gap-2">
      <button
        type="button"
        class="rounded-lg px-3 py-1.5 text-sm ring-1 ring-slate-300 disabled:opacity-40"
        :disabled="modelo <= 1"
        @click="modelo -= 1"
      >
        Anterior
      </button>
      <button
        type="button"
        class="rounded-lg px-3 py-1.5 text-sm ring-1 ring-slate-300 disabled:opacity-40"
        :disabled="modelo >= totalPaginas"
        @click="modelo += 1"
      >
        Próxima
      </button>
    </div>
  </nav>
</template>
