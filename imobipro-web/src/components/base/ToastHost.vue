<script setup>
import { useToast } from '@/composables/useToast'

const { avisos, remover } = useToast()

const CORES = {
  sucesso: 'bg-emerald-600',
  erro: 'bg-red-600',
  info: 'bg-slate-800',
}
</script>

<template>
  <div class="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
    <output
      v-for="aviso in avisos"
      :key="aviso.id"
      class="paleta-fixa pointer-events-auto flex items-start gap-3 rounded-lg px-4 py-3 text-sm text-white shadow-lg"
      :class="CORES[aviso.tipo]"
    >
      <span class="flex-1">{{ aviso.mensagem }}</span>
      <button
        type="button"
        class="opacity-70 hover:opacity-100"
        aria-label="Fechar"
        @click="remover(aviso.id)"
      >
        ✕
      </button>
    </output>
  </div>
</template>
