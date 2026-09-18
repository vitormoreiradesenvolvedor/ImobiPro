<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

defineProps({ aberta: { type: Boolean, default: false } })
defineEmits(['fechar'])

const auth = useAuthStore()

const GRUPOS = [
  {
    titulo: '',
    itens: [{ chave: 'dashboard', rotulo: 'Dashboard', rota: 'dashboard', icone: '▦' }],
  },
  {
    titulo: 'Carteira',
    itens: [
      { chave: 'imoveis', rotulo: 'Imóveis', rota: 'imoveis', icone: '⌂' },
      { chave: 'pessoas', rotulo: 'Pessoas', rota: 'pessoas', icone: '☺' },
    ],
  },
  {
    titulo: 'Comercial',
    itens: [
      {
        chave: 'crm',
        rotulo: 'Funil de vendas',
        rota: 'crm',
        icone: '◈',
        permissao: 'ver_crm',
      },
      {
        chave: 'atendimento',
        rotulo: 'Atendimento',
        rota: 'atendimento',
        icone: '☎',
        permissao: 'ver_crm',
      },
      { chave: 'agenda', rotulo: 'Agenda', rota: 'agenda', icone: '▤' },
      { chave: 'candidaturas', rotulo: 'Candidaturas', rota: 'candidaturas', icone: '⎘' },
      { chave: 'contratos', rotulo: 'Contratos', rota: 'contratos', icone: '✎' },
    ],
  },
  {
    titulo: 'Administração',
    itens: [
      {
        chave: 'cobrancas',
        rotulo: 'Contas a receber',
        rota: 'cobrancas',
        icone: '₿',
        permissao: 'ver_financeiro',
      },
      {
        chave: 'repasses',
        rotulo: 'Repasses',
        rota: 'repasses',
        icone: '↗',
        permissao: 'ver_financeiro',
      },
      { chave: 'comissoes', rotulo: 'Comissões', rota: 'comissoes', icone: '%' },
      { chave: 'vistorias', rotulo: 'Vistorias', rota: 'vistorias', icone: '☑' },
      {
        chave: 'relatorios',
        rotulo: 'Relatórios',
        rota: 'relatorios',
        icone: '◔',
        permissao: 'ver_financeiro',
      },
      {
        chave: 'configuracoes',
        rotulo: 'Configurações',
        rota: 'configuracoes',
        icone: '⚙',
        permissao: 'gerenciar_usuarios',
      },
    ],
  },
]

// O menu espelha as permissões do papel devolvidas por /auth/me/.
const grupos = computed(() =>
  GRUPOS.map((grupo) => ({
    ...grupo,
    itens: grupo.itens.filter((item) => !item.permissao || auth.pode(item.permissao)),
  })).filter((grupo) => grupo.itens.length),
)
</script>

<template>
  <aside
    data-tour="menu-lateral"
    class="paleta-fixa fixed inset-y-0 left-0 z-40 w-64 -translate-x-full overflow-y-auto bg-slate-900 text-slate-300 transition-transform lg:translate-x-0"
    :class="aberta ? 'translate-x-0' : ''"
  >
    <div class="flex h-16 items-center gap-2 px-5">
      <span class="grid size-9 place-items-center rounded-lg bg-marca font-bold text-white">
        iP
      </span>
      <div class="min-w-0">
        <p class="truncate text-sm font-semibold text-white">
          {{ auth.tenant?.nome_fantasia || 'ImobiPro' }}
        </p>
        <p class="truncate text-xs text-slate-400">{{ auth.tenant?.subdominio }}</p>
      </div>
    </div>

    <nav class="mt-2 space-y-5 px-3 pb-8" aria-label="Navegação principal">
      <div v-for="grupo in grupos" :key="grupo.titulo || 'inicio'">
        <p
          v-if="grupo.titulo"
          class="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500"
        >
          {{ grupo.titulo }}
        </p>
        <RouterLink
          v-for="item in grupo.itens"
          :key="item.chave"
          :to="{ name: item.rota }"
          class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition hover:bg-slate-800 hover:text-white"
          active-class="bg-slate-800 text-white"
          @click="$emit('fechar')"
        >
          <span aria-hidden="true" class="w-5 text-center">{{ item.icone }}</span>
          <span>{{ item.rotulo }}</span>
        </RouterLink>
      </div>
    </nav>
  </aside>
</template>
