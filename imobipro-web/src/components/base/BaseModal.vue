<script setup>
import { onMounted, onUnmounted } from 'vue'

defineProps({
  titulo: { type: String, default: '' },
  largura: { type: String, default: 'max-w-lg' },
})

const emit = defineEmits(['fechar'])

function aoTeclar(evento) {
  if (evento.key === 'Escape') emit('fechar')
}

onMounted(() => document.addEventListener('keydown', aoTeclar))
onUnmounted(() => document.removeEventListener('keydown', aoTeclar))
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
    <div class="paleta-fixa fixed inset-0 bg-slate-900/50" @click="emit('fechar')" />
    <dialog
      open
      aria-modal="true"
      class="relative w-full rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      :class="largura"
    >
      <header
        class="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4"
      >
        <h2 class="text-base font-semibold text-slate-900">{{ titulo }}</h2>
        <button
          type="button"
          class="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          aria-label="Fechar"
          @click="emit('fechar')"
        >
          ✕
        </button>
      </header>
      <div class="max-h-[70vh] overflow-y-auto px-5 py-4"><slot /></div>
      <footer
        v-if="$slots.rodape"
        class="flex justify-end gap-2 border-t border-slate-200 px-5 py-4"
      >
        <slot name="rodape" />
      </footer>
    </dialog>
  </div>
</template>
