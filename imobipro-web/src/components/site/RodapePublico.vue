<script setup>
import { telefone } from '@/utils/formatters'

defineProps({
  identidade: { type: Object, default: null },
})

const ano = new Date().getFullYear()
</script>

<template>
  <footer class="faixa-marca mt-16 text-white/80">
    <div
      class="mx-auto flex max-w-6xl flex-wrap items-start justify-between gap-6 px-4 py-10 text-sm"
    >
      <div class="space-y-1">
        <p class="text-base font-semibold text-white">
          {{ identidade?.nome ?? 'Imobiliária' }}
        </p>
        <p v-if="identidade?.creci">CRECI {{ identidade.creci }}</p>
        <p>© {{ ano }}. Todos os direitos reservados.</p>
      </div>

      <div class="space-y-1">
        <p class="font-medium text-white">Contato</p>
        <p v-if="identidade?.telefone" class="numerico">{{ telefone(identidade.telefone) }}</p>
        <p v-if="identidade?.email_contato">{{ identidade.email_contato }}</p>
        <p v-if="!identidade?.telefone && !identidade?.email_contato">
          Fale pelo formulário do imóvel.
        </p>
      </div>

      <p class="text-xs text-white/50">Mapa e dados de localização: OpenStreetMap</p>
    </div>
  </footer>
</template>
