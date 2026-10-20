<script setup>
import { useId } from 'vue'

defineOptions({ inheritAttrs: false })

defineProps({
  rotulo: { type: String, default: '' },
  linhas: { type: Number, default: 4 },
  erro: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  obrigatorio: { type: Boolean, default: false },
})

const modelo = defineModel({ type: String, default: '' })
const id = useId()
</script>

<template>
  <div class="space-y-1.5">
    <label v-if="rotulo" :for="id" class="block text-sm font-medium text-slate-700">
      {{ rotulo }}
      <span v-if="obrigatorio" class="text-red-600" aria-hidden="true">*</span>
    </label>
    <textarea
      :id="id"
      v-model="modelo"
      v-bind="$attrs"
      :rows="linhas"
      :placeholder="placeholder"
      :aria-invalid="Boolean(erro)"
      class="block w-full rounded-lg border-0 px-3 py-2.5 text-slate-900 ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-marca sm:text-sm"
      :class="erro ? 'ring-red-500' : ''"
    />
    <p v-if="erro" class="text-sm text-red-600">{{ erro }}</p>
  </div>
</template>
