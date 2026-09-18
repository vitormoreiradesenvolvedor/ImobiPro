<script setup>
import { useId } from 'vue'

// Sem isto, @blur e demais listeners cairiam no <div> externo e blur não
// borbulha, então a busca por CEP nunca era disparada.
defineOptions({ inheritAttrs: false })

defineProps({
  rotulo: { type: String, required: true },
  tipo: { type: String, default: 'text' },
  erro: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  obrigatorio: { type: Boolean, default: false },
})

const modelo = defineModel({ type: String, default: '' })
const id = useId()
</script>

<template>
  <div class="space-y-1.5">
    <label :for="id" class="block text-sm font-medium text-slate-700">
      {{ rotulo }}
      <span v-if="obrigatorio" class="text-red-600" aria-hidden="true">*</span>
    </label>
    <input
      :id="id"
      v-model="modelo"
      v-bind="$attrs"
      :type="tipo"
      :autocomplete="autocomplete"
      :required="obrigatorio"
      :aria-invalid="Boolean(erro)"
      :aria-describedby="erro ? `${id}-erro` : undefined"
      class="block w-full rounded-lg border-0 px-3 py-2.5 text-slate-900 ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-marca sm:text-sm"
      :class="erro ? 'ring-red-500 focus:ring-red-500' : ''"
    />
    <p v-if="erro" :id="`${id}-erro`" class="text-sm text-red-600">{{ erro }}</p>
  </div>
</template>
