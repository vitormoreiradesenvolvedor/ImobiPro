<script setup>
defineProps({
  colunas: { type: Array, required: true },
  linhas: { type: Array, required: true },
  carregando: { type: Boolean, default: false },
  chave: { type: String, default: 'id' },
})

defineEmits(['selecionar'])
</script>

<template>
  <!-- Tabela larga rola dentro do próprio container; a página nunca rola lateral. -->
  <div class="overflow-x-auto rounded-xl bg-white ring-1 ring-slate-200">
    <table class="min-w-full divide-y divide-slate-200 text-sm">
      <thead class="bg-slate-50">
        <tr>
          <th
            v-for="coluna in colunas"
            :key="coluna.campo"
            scope="col"
            class="px-4 py-3 text-left font-semibold text-slate-600"
            :class="coluna.alinhamento === 'direita' ? 'text-right' : ''"
          >
            {{ coluna.rotulo }}
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-if="carregando">
          <td :colspan="colunas.length" class="px-4 py-8 text-center text-slate-400">
            Carregando…
          </td>
        </tr>
        <tr
          v-for="linha in linhas"
          v-else
          :key="linha[chave]"
          class="cursor-pointer hover:bg-slate-50"
          @click="$emit('selecionar', linha)"
        >
          <td
            v-for="coluna in colunas"
            :key="coluna.campo"
            class="px-4 py-3 text-slate-700"
            :class="coluna.alinhamento === 'direita' ? 'numerico text-right' : ''"
          >
            <slot :name="coluna.campo" :linha="linha">{{ linha[coluna.campo] ?? '' }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
