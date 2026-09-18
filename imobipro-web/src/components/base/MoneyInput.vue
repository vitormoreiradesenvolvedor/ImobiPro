<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  rotulo: { type: String, default: '' },
  erro: { type: String, default: '' },
  obrigatorio: { type: Boolean, default: false },
})

// O modelo guarda o número puro ("2500.00"); a máscara é só apresentação
// enviar string formatada para a API é fonte garantida de erro de arredondamento.
const modelo = defineModel({ type: [String, Number, null], default: '' })
const id = useId()

const exibido = computed({
  get() {
    if (modelo.value === '' || modelo.value == null) return ''
    return Number(modelo.value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
  },
  set(bruto) {
    const digitos = String(bruto).replace(/\D/g, '')
    modelo.value = digitos ? (Number(digitos) / 100).toFixed(2) : ''
  },
})
</script>

<template>
  <div class="space-y-1.5">
    <label v-if="rotulo" :for="id" class="block text-sm font-medium text-slate-700">
      {{ rotulo }}
      <span v-if="props.obrigatorio" class="text-red-600" aria-hidden="true">*</span>
    </label>
    <div class="relative">
      <span class="absolute inset-y-0 left-3 flex items-center text-sm text-slate-500">R$</span>
      <input
        :id="id"
        v-model="exibido"
        inputmode="numeric"
        class="numerico block w-full rounded-lg border-0 py-2.5 pl-10 pr-3 text-right text-slate-900 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-inset focus:ring-marca sm:text-sm"
        :class="erro ? 'ring-red-500' : ''"
        placeholder="0,00"
      />
    </div>
    <p v-if="erro" class="text-sm text-red-600">{{ erro }}</p>
  </div>
</template>
