<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/base/StatusBadge.vue'
import { moeda } from '@/utils/formatters'

const props = defineProps({ imovel: { type: Object, required: true } })

const valor = computed(() =>
  props.imovel.finalidade === 'VENDA'
    ? moeda(props.imovel.valor_venda)
    : moeda(props.imovel.valor_locacao),
)

const sufixo = computed(() => (props.imovel.finalidade === 'VENDA' ? '' : '/mês'))
</script>

<template>
  <RouterLink
    :to="{ name: 'imovel-detalhe', params: { id: imovel.id } }"
    class="group flex flex-col overflow-hidden rounded-xl bg-white ring-1 ring-slate-200 transition hover:ring-marca"
  >
    <div class="relative aspect-[4/3] bg-slate-100">
      <img
        v-if="imovel.foto_capa"
        :src="imovel.foto_capa"
        :alt="imovel.titulo"
        loading="lazy"
        class="size-full object-cover"
      />
      <div v-else class="flex size-full items-center justify-center text-3xl text-slate-300">
        ⌂
      </div>
      <div class="absolute left-2 top-2 flex gap-1">
        <StatusBadge :status="imovel.situacao" :rotulo="imovel.situacao_display" />
        <span
          v-if="imovel.publicado_site"
          class="rounded-md bg-white/90 px-2 py-1 text-xs font-medium text-slate-700"
        >
          no site
        </span>
      </div>
    </div>

    <div class="flex flex-1 flex-col p-4">
      <p class="text-xs font-medium text-slate-400">{{ imovel.codigo }}</p>
      <h3 class="mt-0.5 line-clamp-2 text-sm font-semibold text-slate-900">
        {{ imovel.titulo }}
      </h3>
      <p class="mt-1 text-xs text-slate-500">{{ imovel.bairro }}, {{ imovel.cidade }}</p>

      <div class="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-600">
        <span v-if="imovel.quartos">{{ imovel.quartos }} quartos</span>
        <span v-if="imovel.banheiros">{{ imovel.banheiros }} banh.</span>
        <span v-if="imovel.vagas">{{ imovel.vagas }} vagas</span>
        <span v-if="imovel.area_util">{{ imovel.area_util }} m²</span>
      </div>

      <p class="numerico mt-auto pt-3 text-lg font-bold text-slate-900">
        {{ valor }}<span class="text-sm font-normal text-slate-500">{{ sufixo }}</span>
      </p>
      <p v-if="imovel.valor_condominio" class="numerico text-xs text-slate-500">
        + {{ moeda(imovel.valor_condominio) }} de condomínio
      </p>
    </div>
  </RouterLink>
</template>
