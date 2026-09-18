<script setup>
import { useId } from 'vue'

defineOptions({ inheritAttrs: false })

defineProps({
  rotulo: { type: String, default: '' },
  opcoes: { type: Array, required: true },
  chaveValor: { type: String, default: 'value' },
  chaveRotulo: { type: String, default: 'label' },
  placeholder: { type: String, default: '' },
  erro: { type: String, default: '' },
  obrigatorio: { type: Boolean, default: false },
})

const modelo = defineModel({ type: [String, Number, null], default: '' })
const id = useId()
</script>

<template>
  <div class="space-y-1.5">
    <label v-if="rotulo" :for="id" class="block text-sm font-medium text-slate-700">
      {{ rotulo }}
      <span v-if="obrigatorio" class="text-red-600" aria-hidden="true">*</span>
    </label>
    <select
      :id="id"
      v-model="modelo"
      v-bind="$attrs"
      :aria-invalid="Boolean(erro)"
      class="block w-full rounded-lg border-0 py-2.5 pl-3 pr-9 text-slate-900 ring-1 ring-inset ring-slate-300 focus:ring-2 focus:ring-inset focus:ring-marca sm:text-sm"
      :class="erro ? 'ring-red-500' : ''"
    >
      <option v-if="placeholder" value="">{{ placeholder }}</option>
      <option
        v-for="opcao in opcoes"
        :key="opcao[chaveValor] ?? opcao"
        :value="opcao[chaveValor] ?? opcao"
      >
        {{ opcao[chaveRotulo] ?? opcao }}
      </option>
    </select>
    <p v-if="erro" class="text-sm text-red-600">{{ erro }}</p>
  </div>
</template>
