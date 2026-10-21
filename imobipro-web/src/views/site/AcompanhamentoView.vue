<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import CabecalhoPublico from '@/components/site/CabecalhoPublico.vue'
import RodapePublico from '@/components/site/RodapePublico.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { siteService } from '@/services/api'
import { dataHora } from '@/utils/formatters'

const route = useRoute()
const subdominio = computed(() => route.params.subdominio)
const { identidade } = useIdentidade(() => route.params.subdominio)

const protocolo = ref(route.query.protocolo ?? '')
const contato = ref('')
const ticket = ref(null)
const erro = ref('')
const consultando = ref(false)

async function consultar() {
  consultando.value = true
  erro.value = ''
  ticket.value = null
  try {
    const { data } = await siteService.acompanharTicket(
      subdominio.value,
      protocolo.value.trim().toUpperCase(),
      contato.value.trim(),
    )
    ticket.value = data
  } catch (falha) {
    erro.value =
      falha.response?.data?.detail ??
      'Não encontramos esse protocolo com esse contato. Confira os dados.'
  } finally {
    consultando.value = false
  }
}

onMounted(() => {
  // Protocolo veio do link, mas o contato é a prova: nunca consulta sozinho.
  if (protocolo.value) document.getElementById('contato')?.focus()
})
</script>

<template>
  <div class="superficie flex min-h-screen flex-col">
    <CabecalhoPublico :identidade="identidade" :subdominio="subdominio" compacto>
      <div class="mx-auto max-w-3xl px-4 pb-8">
        <h1 class="text-3xl font-bold tracking-tight">Acompanhar pedido</h1>
        <p class="mt-1 text-sm text-white/70">
          Informe o protocolo e o telefone ou e-mail que você usou no pedido.
        </p>
      </div>
    </CabecalhoPublico>

    <main class="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-10">
      <form class="cartao space-y-4 p-6" @submit.prevent="consultar">
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="block">
            <span class="mb-1 block text-sm font-medium text-slate-700">Protocolo</span>
            <input
              v-model="protocolo"
              required
              placeholder="ATD-2026-000123"
              class="numerico w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
            />
          </label>
          <label class="block">
            <span class="mb-1 block text-sm font-medium text-slate-700">
              Telefone ou e-mail
            </span>
            <input
              id="contato"
              v-model="contato"
              required
              class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
            />
          </label>
        </div>

        <p v-if="erro" class="text-sm text-red-600" role="alert">{{ erro }}</p>

        <button
          type="submit"
          :disabled="consultando"
          class="rounded-lg bg-marca px-5 py-2.5 font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
        >
          {{ consultando ? 'Consultando…' : 'Consultar' }}
        </button>
      </form>

      <section v-if="ticket" class="cartao space-y-4 p-6">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="numerico text-sm text-slate-500">{{ ticket.protocolo }}</p>
            <h2 class="text-xl font-semibold text-slate-900">{{ ticket.tipo_display }}</h2>
            <p v-if="ticket.imovel_codigo" class="text-sm text-slate-500">
              {{ ticket.imovel_codigo }} · {{ ticket.imovel_titulo }}
            </p>
          </div>
          <span
            class="rounded-full bg-marca-suave px-3 py-1 text-sm font-medium text-marca-escura"
          >
            {{ ticket.status_display }}
          </span>
        </div>

        <dl class="grid gap-3 text-sm sm:grid-cols-2">
          <div v-if="ticket.atendido_por">
            <dt class="text-slate-500">Quem está atendendo</dt>
            <dd class="font-medium text-slate-900">{{ ticket.atendido_por }}</dd>
          </div>
          <div v-if="ticket.agendado_para">
            <dt class="text-slate-500">Visita marcada para</dt>
            <dd class="font-medium text-slate-900">{{ dataHora(ticket.agendado_para) }}</dd>
          </div>
        </dl>

        <div>
          <h3 class="mb-2 text-sm font-semibold text-slate-900">O que aconteceu</h3>
          <ol class="space-y-3 border-l-2 border-marca-borda pl-4">
            <li v-for="evento in ticket.eventos" :key="evento.id" class="text-sm">
              <p class="text-slate-800">{{ evento.descricao }}</p>
              <p class="text-xs text-slate-400">{{ dataHora(evento.criado_em) }}</p>
            </li>
          </ol>
        </div>
      </section>
    </main>

    <RodapePublico :identidade="identidade" />
  </div>
</template>
