<script setup>
import { computed } from 'vue'

const props = defineProps({
  variante: { type: String, default: 'primaria' },
  tipo: { type: String, default: 'button' },
  carregando: { type: Boolean, default: false },
  desabilitado: { type: Boolean, default: false },
  blocoCompleto: { type: Boolean, default: false },
})

const variantes = {
  primaria: 'bg-marca text-white hover:brightness-110 focus-visible:outline-marca',
  secundaria:
    'bg-white text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 focus-visible:outline-slate-400',
  perigo: 'bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600',
  fantasma: 'text-slate-600 hover:bg-slate-100 focus-visible:outline-slate-400',
}

const classes = computed(() => [
  'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold',
  'transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2',
  'disabled:cursor-not-allowed disabled:opacity-60',
  variantes[props.variante] ?? variantes.primaria,
  props.blocoCompleto ? 'w-full' : '',
])
</script>

<template>
  <button :type="tipo" :class="classes" :disabled="desabilitado || carregando">
    <svg
      v-if="carregando"
      class="size-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        class="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        stroke-width="4"
      />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
    <slot />
  </button>
</template>
