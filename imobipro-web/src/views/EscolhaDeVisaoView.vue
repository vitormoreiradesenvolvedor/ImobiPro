<script setup>
import { computed } from 'vue'

import AlternadorTema from '@/components/base/AlternadorTema.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { useAuthStore } from '@/stores/auth'

/**
 * Porta de entrada do sistema.
 *
 * O mesmo endereço serve dois públicos com expectativas opostas: quem procura
 * imóvel quer a vitrine, quem trabalha na imobiliária quer o painel. Em vez de
 * adivinhar, a escolha é explícita.
 */
const auth = useAuthStore()

// Mesma regra do login: subdomínio do host ou, em instalação de uma
// imobiliária só, a variável de ambiente.
const subdominio =
  import.meta.env.VITE_IMOBILIARIA ||
  (window.location.hostname.split('.').length > 2 ? window.location.hostname.split('.')[0] : '')

const { identidade } = useIdentidade(() => subdominio)

const marca = computed(() => identidade.value?.nome ?? 'ImobiPro')
const temSite = computed(() => Boolean(subdominio))
const destinoDaEquipe = computed(() => (auth.autenticado ? '/' : '/login'))
</script>

<template>
  <div class="superficie flex min-h-screen flex-col">
    <header class="faixa-marca text-white">
      <div class="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-5">
        <div class="flex items-center gap-3">
          <img
            v-if="identidade?.logo"
            :src="identidade.logo"
            :alt="marca"
            class="size-11 rounded-xl bg-white/95 object-contain p-1"
          />
          <span
            v-else
            aria-hidden="true"
            class="grid size-11 place-items-center rounded-xl bg-white/15 font-bold ring-1 ring-white/25"
          >
            iP
          </span>
          <div>
            <p class="text-base font-semibold tracking-tight">{{ marca }}</p>
            <p class="text-xs text-white/60">Gestão imobiliária com ImobiPro</p>
          </div>
        </div>

        <AlternadorTema claro />
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-14">
      <h1 class="text-3xl font-bold tracking-tight text-slate-900">Por onde você entra?</h1>
      <p class="mt-2 text-slate-500">
        Duas portas para a mesma base: a vitrine aberta de quem procura imóvel e o painel de
        quem administra a carteira.
      </p>

      <div class="mt-10 grid gap-5 md:grid-cols-2">
        <a
          v-if="temSite"
          :href="`/site/${subdominio}`"
          data-teste="visao-cliente"
          class="cartao group flex flex-col gap-3 p-7 transition hover:-translate-y-1"
        >
          <span
            aria-hidden="true"
            class="grid size-12 place-items-center rounded-xl bg-marca-suave text-xl text-marca-escura"
          >
            ⌂
          </span>
          <h2 class="text-xl font-semibold text-slate-900 group-hover:text-marca">
            Quero ver imóveis
          </h2>
          <p class="text-sm text-slate-500">
            Catálogo por finalidade, tipo, bairro e faixa de aluguel, ficha com mapa e pedido de
            visita sem cadastro.
          </p>
          <span class="mt-auto pt-2 text-sm font-semibold text-marca">
            Abrir a vitrine
            <span aria-hidden="true">→</span>
          </span>
        </a>

        <RouterLink
          :to="destinoDaEquipe"
          data-teste="visao-equipe"
          class="cartao group flex flex-col gap-3 p-7 transition hover:-translate-y-1"
        >
          <span
            aria-hidden="true"
            class="grid size-12 place-items-center rounded-xl bg-marca-suave text-xl text-marca-escura"
          >
            ▤
          </span>
          <h2 class="text-xl font-semibold text-slate-900 group-hover:text-marca">
            Sou da imobiliária
          </h2>
          <p class="text-sm text-slate-500">
            Carteira, funil com prazo de atendimento, contratos, financeiro, vistorias e
            relatórios. O inquilino com acesso cai no portal dele.
          </p>
          <span class="mt-auto pt-2 text-sm font-semibold text-marca">
            {{ auth.autenticado ? 'Abrir o painel' : 'Entrar no painel' }}
            <span aria-hidden="true">→</span>
          </span>
        </RouterLink>
      </div>

      <p v-if="temSite" class="mt-8 text-sm text-slate-500">
        Também dá para acompanhar um pedido de visita já aberto pelo
        <a
          :href="`/site/${subdominio}/acompanhar`"
          class="font-medium text-marca hover:underline"
        >
          protocolo
        </a>
        .
      </p>
    </main>
  </div>
</template>
