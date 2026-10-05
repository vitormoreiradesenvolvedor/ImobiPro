<script setup>
import { ref, watch } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'

const { pedido, aberto, responder } = useConfirmacao()
const texto = ref('')

watch(pedido, (atual) => {
  texto.value = atual?.valorInicial ?? ''
})

function cancelar() {
  responder(pedido.value?.tipo === 'texto' ? null : false)
}

function confirmar() {
  responder(pedido.value?.tipo === 'texto' ? texto.value : true)
}
</script>

<template>
  <BaseModal v-if="aberto && pedido" :titulo="pedido.titulo" @fechar="cancelar">
    <p v-if="pedido.mensagem" class="text-sm text-slate-600">{{ pedido.mensagem }}</p>

    <div v-if="pedido.tipo === 'texto'" class="mt-4">
      <BaseInput v-model="texto" :rotulo="pedido.rotulo" />
    </div>

    <template #rodape>
      <BaseButton variante="secundaria" @click="cancelar">Cancelar</BaseButton>
      <BaseButton :variante="pedido.perigo ? 'perigo' : 'primaria'" @click="confirmar">
        {{ pedido.confirmar ?? 'Confirmar' }}
      </BaseButton>
    </template>
  </BaseModal>
</template>
