<script setup>
import { computed } from 'vue'

import AlternadorTema from '@/components/base/AlternadorTema.vue'

const props = defineProps({
  identidade: { type: Object, default: null },
  subdominio: { type: String, required: true },
  compacto: { type: Boolean, default: false },
})

const nome = computed(() => props.identidade?.nome ?? 'Imóveis disponíveis')

/** Sem logo cadastrada, as iniciais do nome já dão identidade à barra. */
const iniciais = computed(() =>
  nome.value
    .split(/\s+/)
    .filter((parte) => parte.length > 2)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join(''),
)
</script>

<template>
  <header class="faixa-marca text-white">
    <div
      class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4"
      :class="compacto ? 'py-4' : 'py-5'"
    >
      <RouterLink
        :to="{ name: 'site-vitrine', params: { subdominio } }"
        class="flex items-center gap-3"
      >
        <img
          v-if="identidade?.logo"
          :src="identidade.logo"
          :alt="nome"
          class="h-11 w-11 rounded-xl bg-white/95 object-contain p-1"
        />
        <span
          v-else
          aria-hidden="true"
          class="grid h-11 w-11 place-items-center rounded-xl bg-white/15 text-base font-bold ring-1 ring-white/25"
        >
          {{ iniciais || 'iP' }}
        </span>
        <span>
          <span class="block text-base font-semibold tracking-tight">{{ nome }}</span>
          <span v-if="identidade?.creci" class="block text-xs text-white/60">
            CRECI {{ identidade.creci }}
          </span>
        </span>
      </RouterLink>

      <nav class="flex items-center gap-2 text-sm" aria-label="Site">
        <RouterLink
          :to="{ name: 'site-vitrine', params: { subdominio } }"
          class="rounded-lg px-3 py-2 text-white/80 transition hover:bg-white/10 hover:text-white"
        >
          Imóveis
        </RouterLink>
        <RouterLink
          :to="{ name: 'site-acompanhar', params: { subdominio } }"
          class="rounded-lg px-3 py-2 font-medium ring-1 ring-white/25 transition hover:bg-white/10"
        >
          Acompanhar pedido
        </RouterLink>
        <AlternadorTema claro />

        <a
          v-if="identidade?.telefone"
          :href="`tel:${identidade.telefone.replace(/\D/g, '')}`"
          class="hidden rounded-lg bg-white px-3 py-2 font-semibold text-marca-profunda transition hover:bg-white/90 sm:block"
        >
          Falar agora
        </a>
      </nav>
    </div>

    <slot />
  </header>
</template>
