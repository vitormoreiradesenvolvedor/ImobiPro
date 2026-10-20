<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AlternadorTema from '@/components/base/AlternadorTema.vue'
import BotaoTutorial from '@/components/onboarding/BotaoTutorial.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificacoesStore } from '@/stores/notificacoes'
import { dataHora, iniciais } from '@/utils/formatters'

defineEmits(['alternar-menu'])

const auth = useAuthStore()
const notificacoes = useNotificacoesStore()
const router = useRouter()

const menuAberto = ref(false)
const sinoAberto = ref(false)
const cabecalho = ref(null)

/**
 * Menus suspensos fecham como o usuário espera: clique fora ou Esc.
 *
 * Sem isto, o painel de notificações ficava aberto por cima da tela seguinte
 * até alguém clicar de novo no sino.
 */
function fecharSuspensos() {
  menuAberto.value = false
  sinoAberto.value = false
}

function aoClicarNaPagina(evento) {
  if (!cabecalho.value?.contains(evento.target)) fecharSuspensos()
}

function aoTeclar(evento) {
  if (evento.key === 'Escape') fecharSuspensos()
}

onMounted(() => {
  document.addEventListener('click', aoClicarNaPagina)
  document.addEventListener('keydown', aoTeclar)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', aoClicarNaPagina)
  document.removeEventListener('keydown', aoTeclar)
})

async function sair() {
  notificacoes.desconectar()
  await auth.logout()
  router.push({ name: 'login' })
}

function abrirNotificacao(notificacao) {
  notificacoes.marcarLida(notificacao.id)
  sinoAberto.value = false

  const leadId = notificacao.dados?.lead_id
  if (leadId) router.push({ name: 'lead-detalhe', params: { id: leadId } })
}
</script>

<template>
  <header
    ref="cabecalho"
    class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-6"
  >
    <button
      type="button"
      class="rounded-lg p-2 text-slate-600 hover:bg-slate-100 lg:hidden"
      aria-label="Abrir menu"
      @click="$emit('alternar-menu')"
    >
      ☰
    </button>

    <div class="flex-1"><slot name="titulo" /></div>

    <a
      v-if="auth.tenant?.subdominio"
      :href="`/site/${auth.tenant.subdominio}`"
      target="_blank"
      rel="noopener"
      data-tour="ver-site"
      class="hidden items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-marca-escura ring-1 ring-marca-borda transition hover:bg-marca-suave sm:flex"
    >
      Ver o site
      <span aria-hidden="true">↗</span>
    </a>

    <AlternadorTema />

    <BotaoTutorial />

    <div class="relative">
      <button
        type="button"
        class="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100"
        :aria-expanded="sinoAberto"
        aria-label="Notificações"
        @click="sinoAberto = !sinoAberto"
      >
        🔔
        <span
          v-if="notificacoes.naoLidas"
          class="absolute -right-0.5 -top-0.5 grid size-5 place-items-center rounded-full bg-red-600 text-[10px] font-bold text-white"
        >
          {{ notificacoes.naoLidas > 9 ? '9+' : notificacoes.naoLidas }}
        </span>
      </button>

      <div
        v-if="sinoAberto"
        class="absolute right-0 mt-2 w-80 overflow-hidden rounded-lg bg-white shadow-lg ring-1 ring-slate-200"
      >
        <div class="flex items-center justify-between border-b border-slate-100 px-4 py-2">
          <span class="text-sm font-semibold text-slate-900">Notificações</span>
          <button
            type="button"
            class="text-xs text-marca hover:underline"
            @click="notificacoes.marcarTodasLidas()"
          >
            marcar todas como lidas
          </button>
        </div>

        <ul class="max-h-80 divide-y divide-slate-100 overflow-y-auto">
          <li v-for="item in notificacoes.recentes" :key="item.id">
            <button
              type="button"
              class="w-full px-4 py-3 text-left hover:bg-slate-50"
              :class="item.lida ? 'opacity-60' : ''"
              @click="abrirNotificacao(item)"
            >
              <p class="text-sm font-medium text-slate-900">{{ item.titulo }}</p>
              <p class="text-xs text-slate-500">{{ item.descricao }}</p>
              <p class="mt-0.5 text-[11px] text-slate-400">{{ dataHora(item.criado_em) }}</p>
            </button>
          </li>
          <li
            v-if="!notificacoes.recentes.length"
            class="px-4 py-6 text-center text-sm text-slate-400"
          >
            Nenhuma notificação.
          </li>
        </ul>

        <p class="border-t border-slate-100 px-4 py-2 text-[11px] text-slate-400">
          {{ notificacoes.conectado ? 'Tempo real conectado' : 'Reconectando…' }}
        </p>
      </div>
    </div>

    <div class="relative">
      <button
        type="button"
        class="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-100"
        :aria-expanded="menuAberto"
        aria-haspopup="menu"
        @click="menuAberto = !menuAberto"
      >
        <span
          class="grid size-9 place-items-center rounded-full bg-marca text-sm font-semibold text-white"
        >
          {{ iniciais(auth.usuario?.nome_completo) }}
        </span>
        <span class="hidden text-left sm:block">
          <span class="block text-sm font-medium text-slate-900">
            {{ auth.usuario?.nome_completo }}
          </span>
          <span class="block text-xs text-slate-500">{{ auth.usuario?.papel_display }}</span>
        </span>
      </button>

      <div
        v-if="menuAberto"
        role="menu"
        class="absolute right-0 mt-2 w-52 rounded-lg bg-white py-1 shadow-lg ring-1 ring-slate-200"
      >
        <p class="truncate px-4 py-2 text-xs text-slate-500">{{ auth.usuario?.email }}</p>
        <button
          type="button"
          role="menuitem"
          class="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-slate-50"
          @click="sair"
        >
          Sair
        </button>
      </div>
    </div>
  </header>
</template>
