<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { useAuthStore } from '@/stores/auth'
import { iniciais } from '@/utils/formatters'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

/**
 * Marca na porta de entrada.
 *
 * Antes de autenticar não existe sessão, então o nome e a cor vêm do endereço:
 * o subdomínio do host (`horizonte.exemplo.com.br`) ou, em instalação de uma
 * imobiliária só, a variável de ambiente. Sem pista, fica a marca do produto.
 */
const subdominio =
  import.meta.env.VITE_IMOBILIARIA ||
  (window.location.hostname.split('.').length > 2 ? window.location.hostname.split('.')[0] : '')

const { identidade } = useIdentidade(() => subdominio)

const marca = computed(() => identidade.value?.nome ?? 'ImobiPro')
const assinatura = computed(() =>
  identidade.value ? 'Gestão imobiliária com ImobiPro' : 'Gestão imobiliária',
)
const sigla = computed(() => (identidade.value ? iniciais(marca.value) : 'iP'))

const email = ref('')
const senha = ref('')

async function entrar() {
  if (await auth.login(email.value, senha.value)) {
    router.push(route.query.proximo || { name: 'dashboard' })
  }
}
</script>

<template>
  <div class="grid min-h-screen lg:grid-cols-2">
    <div class="flex items-center justify-center px-6 py-12">
      <div class="w-full max-w-sm">
        <div class="mb-8 flex items-center gap-3">
          <img
            v-if="identidade?.logo"
            :src="identidade.logo"
            :alt="marca"
            class="size-11 rounded-xl object-contain"
          />
          <span
            v-else
            class="grid size-11 place-items-center rounded-xl bg-marca font-bold text-white"
          >
            {{ sigla }}
          </span>
          <div>
            <h1 class="text-xl font-bold text-slate-900">{{ marca }}</h1>
            <p class="text-sm text-slate-500">{{ assinatura }}</p>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-slate-900">Entrar na sua conta</h2>
        <p class="mt-1 text-sm text-slate-500">Use o e-mail cadastrado pela sua imobiliária.</p>

        <form class="mt-8 space-y-5" @submit.prevent="entrar">
          <BaseInput
            v-model="email"
            rotulo="E-mail"
            tipo="email"
            autocomplete="email"
            obrigatorio
          />
          <BaseInput
            v-model="senha"
            rotulo="Senha"
            tipo="password"
            autocomplete="current-password"
            obrigatorio
          />

          <p
            v-if="auth.erro"
            role="alert"
            class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {{ auth.erro }}
          </p>

          <BaseButton tipo="submit" :carregando="auth.carregando" bloco-completo>
            Entrar
          </BaseButton>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          Sua imobiliária ainda não usa o ImobiPro?
          <RouterLink
            :to="{ name: 'cadastro' }"
            class="font-semibold text-marca hover:underline"
          >
            Cadastre-se
          </RouterLink>
        </p>
      </div>
    </div>

    <div class="faixa-marca hidden lg:flex lg:items-center lg:justify-center lg:p-12">
      <blockquote class="max-w-md text-white/70">
        <p class="text-2xl font-semibold leading-snug text-white">
          Captação, funil, contrato, repasse e comissão no mesmo lugar.
        </p>
        <p class="mt-4 text-sm">Da visita ao repasse do aluguel, sem planilha paralela.</p>
      </blockquote>
    </div>
  </div>
</template>
