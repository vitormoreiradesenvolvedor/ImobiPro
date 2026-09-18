<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'

import MissaoCumprida from '@/components/onboarding/MissaoCumprida.vue'
import PainelMissoes from '@/components/onboarding/PainelMissoes.vue'
import TourOverlay from '@/components/onboarding/TourOverlay.vue'
import { obterAccessToken } from '@/services/http'
import { useNotificacoesStore } from '@/stores/notificacoes'
import { useOnboardingStore } from '@/stores/onboarding'

import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'

const menuAberto = ref(false)
const notificacoes = useNotificacoesStore()
const onboarding = useOnboardingStore()
const router = useRouter()

/**
 * Notificações e guia são acessórios: se a sessão acabar no meio (logout, troca
 * de usuário), a falha não pode virar erro solto no console nem quebrar a tela.
 */
const semRuido = (promessa) => promessa.catch(() => undefined)

onMounted(async () => {
  await semRuido(notificacoes.carregar())
  notificacoes.conectar(obterAccessToken())

  await semRuido(onboarding.carregar())
  await semRuido(onboarding.sugerirPrimeiroTour(router))
})

// Missão é conferida no servidor: a cada tela nova, reavalia o progresso.
router.afterEach(() => semRuido(onboarding.carregar()))

onUnmounted(() => notificacoes.desconectar())
</script>

<template>
  <div class="superficie min-h-screen">
    <AppSidebar :aberta="menuAberto" @fechar="menuAberto = false" />

    <div
      v-if="menuAberto"
      class="fixed inset-0 z-30 bg-slate-900/50 lg:hidden"
      @click="menuAberto = false"
    />

    <div class="lg:pl-64">
      <AppHeader @alternar-menu="menuAberto = !menuAberto" />
      <main class="p-4 lg:p-6">
        <RouterView />
      </main>
    </div>

    <PainelMissoes />
    <TourOverlay />
    <MissaoCumprida />
  </div>
</template>
