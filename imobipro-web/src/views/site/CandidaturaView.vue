<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import CabecalhoPublico from '@/components/site/CabecalhoPublico.vue'
import RodapePublico from '@/components/site/RodapePublico.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { siteService } from '@/services/api'
import { dataHora, moeda } from '@/utils/formatters'

const route = useRoute()
const subdominio = computed(() => route.params.subdominio)
const token = computed(() => route.params.token)
const { identidade } = useIdentidade(() => route.params.subdominio)

const candidatura = ref(null)
const carregando = ref(true)
const enviando = ref('')
const erro = ref('')

const ROTULOS = {
  RASCUNHO: 'Estamos aguardando seus documentos.',
  EM_ANALISE: 'Documentos recebidos. Nossa equipe está analisando.',
  PENDENTE: 'Há um documento para reenviar. Veja abaixo.',
  APROVADA: 'Cadastro aprovado. Em breve entramos em contato para o contrato.',
  REPROVADA: 'Não foi possível seguir com esta locação.',
  DESISTIU: 'Este processo foi encerrado.',
}

const recusados = computed(
  () => candidatura.value?.documentos?.filter((d) => d.status === 'RECUSADO') ?? [],
)

const encerrada = computed(() =>
  ['APROVADA', 'REPROVADA', 'DESISTIU'].includes(candidatura.value?.status),
)

async function carregar() {
  try {
    const { data } = await siteService.candidatura(subdominio.value, token.value)
    candidatura.value = data
  } catch {
    erro.value = 'Link inválido ou expirado. Peça um novo à imobiliária.'
  } finally {
    carregando.value = false
  }
}

async function enviar(tipo, evento) {
  const arquivo = evento.target.files?.[0]
  if (!arquivo) return

  enviando.value = tipo
  erro.value = ''
  try {
    await siteService.enviarDocumento(subdominio.value, token.value, tipo, arquivo)
    await carregar()
  } catch (falha) {
    const campos = falha.response?.data?.campos ?? {}
    erro.value = Object.values(campos).flat()[0] ?? 'Não foi possível enviar o arquivo.'
  } finally {
    enviando.value = ''
    evento.target.value = ''
  }
}
onMounted(carregar)
</script>

<template>
  <div class="superficie flex min-h-screen flex-col">
    <CabecalhoPublico :identidade="identidade" :subdominio="subdominio" compacto>
      <div class="mx-auto max-w-3xl px-4 pb-8">
        <h1 class="text-3xl font-bold tracking-tight">Sua candidatura</h1>
        <p class="mt-1 text-sm text-white/70">
          Envie os documentos por aqui. Não precisa criar conta.
        </p>
      </div>
    </CabecalhoPublico>

    <main class="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-10">
      <p v-if="carregando" class="py-12 text-center text-slate-400">Carregando…</p>

      <p v-else-if="!candidatura" class="cartao p-8 text-center text-slate-500" role="alert">
        {{ erro }}
      </p>

      <template v-else>
        <section class="cartao p-6">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="numerico text-sm text-slate-500">{{ candidatura.protocolo }}</p>
              <p class="text-lg font-semibold text-slate-900">
                {{ candidatura.imovel_codigo }} · {{ candidatura.imovel_titulo }}
              </p>
              <p v-if="candidatura.imovel_valor" class="text-sm text-slate-500">
                Aluguel de {{ moeda(candidatura.imovel_valor) }}
              </p>
            </div>
            <span
              class="rounded-full bg-marca-suave px-3 py-1 text-sm font-medium text-marca-escura"
            >
              {{ candidatura.status_display }}
            </span>
          </div>
          <p class="mt-3 rounded-lg bg-marca-suave p-3 text-sm text-marca-escura">
            {{ ROTULOS[candidatura.status] }}
          </p>
        </section>

        <section
          v-if="recusados.length"
          class="rounded-xl bg-amber-50 p-5 ring-1 ring-amber-200"
        >
          <h2 class="font-semibold text-amber-900">Precisa reenviar</h2>
          <ul class="mt-2 space-y-1 text-sm text-amber-900">
            <li v-for="documento in recusados" :key="documento.id">
              <strong>{{ documento.tipo_display }}:</strong> {{ documento.observacao }}
            </li>
          </ul>
        </section>

        <section v-if="!encerrada" class="cartao space-y-3 p-6">
          <h2 class="text-lg font-semibold text-slate-900">Documentos a enviar</h2>
          <p v-if="!candidatura.documentos_pendentes.length" class="text-sm text-slate-500">
            Tudo recebido. Não precisa enviar mais nada.
          </p>

          <ul class="space-y-2">
            <li
              v-for="pendente in candidatura.documentos_pendentes"
              :key="pendente.valor"
              class="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-50 p-3 ring-1 ring-slate-100"
            >
              <span class="text-sm font-medium text-slate-800">{{ pendente.rotulo }}</span>
              <label
                class="cursor-pointer rounded-lg bg-marca px-3 py-1.5 text-sm font-semibold text-white hover:brightness-110"
              >
                {{ enviando === pendente.valor ? 'Enviando…' : 'Escolher arquivo' }}
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  class="sr-only"
                  :disabled="enviando === pendente.valor"
                  @change="enviar(pendente.valor, $event)"
                />
              </label>
            </li>
          </ul>

          <p v-if="erro" class="text-sm text-red-600" role="alert">{{ erro }}</p>
        </section>

        <section v-if="candidatura.documentos.length" class="cartao p-6">
          <h2 class="mb-3 text-lg font-semibold text-slate-900">Já enviados</h2>
          <ul class="divide-y divide-slate-100">
            <li
              v-for="documento in candidatura.documentos"
              :key="documento.id"
              class="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
            >
              <span class="text-slate-800">{{ documento.tipo_display }}</span>
              <span
                class="rounded-full px-2.5 py-0.5 text-xs font-medium"
                :class="
                  {
                    APROVADO: 'bg-emerald-100 text-emerald-800',
                    RECUSADO: 'bg-red-100 text-red-700',
                    ENVIADO: 'bg-slate-100 text-slate-600',
                  }[documento.status]
                "
              >
                {{ documento.status_display }}
              </span>
            </li>
          </ul>
        </section>

        <section class="cartao p-6">
          <h2 class="mb-3 text-lg font-semibold text-slate-900">Andamento</h2>
          <ol class="space-y-3 border-l-2 border-marca-borda pl-4">
            <li v-for="evento in candidatura.eventos" :key="evento.id" class="text-sm">
              <p class="text-slate-800">{{ evento.descricao }}</p>
              <p class="text-xs text-slate-400">{{ dataHora(evento.criado_em) }}</p>
            </li>
          </ol>
        </section>
      </template>
    </main>

    <RodapePublico :identidade="identidade" />
  </div>
</template>
