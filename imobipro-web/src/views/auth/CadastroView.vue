<script setup>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({
  razao_social: '',
  nome_fantasia: '',
  cnpj: '',
  subdominio: '',
  nome_completo: '',
  email: '',
  telefone: '',
  senha: '',
  confirmacao: '',
})

// O endereço do site nasce do nome fantasia até a pessoa editá-lo à mão.
const subdominioEditado = ref(false)
watch(
  () => form.nome_fantasia || form.razao_social,
  (nome) => {
    if (subdominioEditado.value) return
    form.subdominio = nome
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 63)
  },
)

function erroDe(campo) {
  const mensagens = auth.errosCampos?.[campo]
  return Array.isArray(mensagens) ? mensagens.join(' ') : (mensagens ?? '')
}

const erroConfirmacao = () =>
  form.confirmacao && form.confirmacao !== form.senha ? 'As senhas não conferem.' : ''

async function cadastrar() {
  if (erroConfirmacao()) return
  const dados = { ...form }
  delete dados.confirmacao
  if (await auth.cadastrar(dados)) {
    router.push({ name: 'dashboard' })
  }
}
</script>

<template>
  <div class="grid min-h-screen lg:grid-cols-2">
    <div class="flex items-center justify-center px-6 py-12">
      <div class="w-full max-w-lg">
        <div class="mb-8 flex items-center gap-3">
          <span
            class="grid size-11 place-items-center rounded-xl bg-marca font-bold text-white"
          >
            iP
          </span>
          <div>
            <h1 class="text-xl font-bold text-slate-900">ImobiPro</h1>
            <p class="text-sm text-slate-500">Gestão imobiliária</p>
          </div>
        </div>

        <h2 class="text-2xl font-bold text-slate-900">Cadastre sua imobiliária</h2>
        <p class="mt-1 text-sm text-slate-500">
          Você entra como administrador e convida a equipe depois, pelo painel.
        </p>

        <form class="mt-8 space-y-6" @submit.prevent="cadastrar">
          <fieldset class="space-y-4">
            <legend class="text-sm font-semibold text-slate-900">Imobiliária</legend>
            <BaseInput
              v-model="form.razao_social"
              rotulo="Razão social"
              :erro="erroDe('razao_social')"
              obrigatorio
            />
            <div class="grid gap-4 sm:grid-cols-2">
              <BaseInput
                v-model="form.nome_fantasia"
                rotulo="Nome fantasia"
                :erro="erroDe('nome_fantasia')"
              />
              <BaseInput
                v-model="form.cnpj"
                rotulo="CNPJ"
                inputmode="numeric"
                placeholder="00.000.000/0000-00"
                :erro="erroDe('cnpj')"
                obrigatorio
              />
            </div>
            <BaseInput
              v-model="form.subdominio"
              rotulo="Endereço do site"
              placeholder="minha-imobiliaria"
              :erro="erroDe('subdominio')"
              obrigatorio
              @input="subdominioEditado = true"
            />
          </fieldset>

          <fieldset class="space-y-4">
            <legend class="text-sm font-semibold text-slate-900">Administrador</legend>
            <BaseInput
              v-model="form.nome_completo"
              rotulo="Nome completo"
              autocomplete="name"
              :erro="erroDe('nome_completo')"
              obrigatorio
            />
            <div class="grid gap-4 sm:grid-cols-2">
              <BaseInput
                v-model="form.email"
                rotulo="E-mail"
                tipo="email"
                autocomplete="email"
                :erro="erroDe('email')"
                obrigatorio
              />
              <BaseInput
                v-model="form.telefone"
                rotulo="Telefone"
                tipo="tel"
                autocomplete="tel"
                :erro="erroDe('telefone')"
              />
            </div>
            <div class="grid gap-4 sm:grid-cols-2">
              <BaseInput
                v-model="form.senha"
                rotulo="Senha"
                tipo="password"
                autocomplete="new-password"
                minlength="10"
                :erro="erroDe('senha')"
                obrigatorio
              />
              <BaseInput
                v-model="form.confirmacao"
                rotulo="Confirme a senha"
                tipo="password"
                autocomplete="new-password"
                :erro="erroConfirmacao()"
                obrigatorio
              />
            </div>
          </fieldset>

          <p
            v-if="auth.erro"
            role="alert"
            class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {{ auth.erro }}
          </p>

          <BaseButton tipo="submit" :carregando="auth.carregando" bloco-completo>
            Criar conta
          </BaseButton>
        </form>

        <p class="mt-6 text-center text-sm text-slate-500">
          Já tem conta?
          <RouterLink :to="{ name: 'login' }" class="font-semibold text-marca hover:underline">
            Entrar
          </RouterLink>
        </p>
      </div>
    </div>

    <div class="faixa-marca hidden lg:flex lg:items-center lg:justify-center lg:p-12">
      <blockquote class="max-w-md text-white/70">
        <p class="text-2xl font-semibold leading-snug text-white">
          Sua carteira, seu funil e seus contratos prontos em minutos.
        </p>
        <p class="mt-4 text-sm">Cadastre a imobiliária e comece pelo guia de uso.</p>
      </blockquote>
    </div>
  </div>
</template>
