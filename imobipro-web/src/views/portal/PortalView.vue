<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AlternadorTema from '@/components/base/AlternadorTema.vue'
import { useToast } from '@/composables/useToast'
import { portalService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { data as formatarData, dataHora, moeda } from '@/utils/formatters'

const auth = useAuthStore()
const router = useRouter()
const { sucesso, erroDaApi } = useToast()

const ABAS = [
  { chave: 'contrato', rotulo: 'Meu contrato' },
  { chave: 'cobrancas', rotulo: 'Boletos' },
  { chave: 'chamados', rotulo: 'Chamados' },
  { chave: 'vistorias', rotulo: 'Vistorias' },
]

const aba = ref('contrato')
const resumo = ref(null)
const cobrancas = ref([])
const chamados = ref([])
const vistorias = ref([])
const carregando = ref(true)
const novoChamado = ref('')
const enviando = ref(false)

const contrato = computed(() => resumo.value?.contrato_atual)
const emAberto = computed(() =>
  cobrancas.value.filter((c) => ['ABERTA', 'ATRASADA'].includes(c.status)),
)

async function carregar() {
  carregando.value = true
  try {
    const [dados, listaCobrancas, listaChamados, listaVistorias] = await Promise.all([
      portalService.resumo(),
      portalService.cobrancas({ page_size: 24 }),
      portalService.chamados(),
      portalService.vistorias(),
    ])
    resumo.value = dados.data
    cobrancas.value = listaCobrancas.data.results ?? listaCobrancas.data
    chamados.value = listaChamados.data.results ?? listaChamados.data
    vistorias.value = listaVistorias.data.results ?? listaVistorias.data
  } finally {
    carregando.value = false
  }
}

async function abrirChamado() {
  enviando.value = true
  try {
    await portalService.abrirChamado(novoChamado.value)
    novoChamado.value = ''
    sucesso('Chamado aberto. A imobiliária já foi avisada.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível abrir o chamado.')
  } finally {
    enviando.value = false
  }
}

async function assinar(vistoria) {
  try {
    await portalService.assinarVistoria(vistoria.id)
    sucesso('Laudo assinado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível assinar o laudo.')
  }
}

async function copiar(texto, rotulo) {
  try {
    await navigator.clipboard.writeText(texto)
    sucesso(`${rotulo} copiado.`)
  } catch {
    erroDaApi(null, 'Copie manualmente pelo texto na tela.')
  }
}

async function sair() {
  await auth.logout()
  router.push({ name: 'login' })
}

onMounted(carregar)
</script>

<template>
  <div class="superficie min-h-screen">
    <header class="faixa-marca text-white">
      <div
        class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-5"
      >
        <div>
          <p class="text-sm text-white/60">{{ auth.tenant?.nome_fantasia }}</p>
          <h1 class="text-2xl font-bold tracking-tight">
            Olá, {{ resumo?.nome?.split(' ')[0] ?? auth.usuario?.nome_completo }}
          </h1>
        </div>
        <div class="flex items-center gap-2">
          <AlternadorTema claro />
          <button
            type="button"
            class="rounded-lg px-3 py-1.5 text-sm font-medium ring-1 ring-white/25 transition hover:bg-white/10"
            @click="sair"
          >
            Sair
          </button>
        </div>
      </div>

      <nav class="mx-auto max-w-5xl px-4" aria-label="Seções do portal">
        <ul class="flex gap-1 overflow-x-auto">
          <li v-for="item in ABAS" :key="item.chave">
            <button
              type="button"
              class="border-b-2 px-4 py-3 text-sm font-medium transition"
              :class="
                aba === item.chave
                  ? 'border-white text-white'
                  : 'border-transparent text-white/60 hover:text-white'
              "
              :aria-current="aba === item.chave ? 'page' : undefined"
              @click="aba = item.chave"
            >
              {{ item.rotulo }}
            </button>
          </li>
        </ul>
      </nav>
    </header>

    <main class="mx-auto max-w-5xl space-y-6 px-4 py-8">
      <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando…</p>

      <template v-else>
        <section class="grid gap-3 sm:grid-cols-3">
          <div class="cartao p-5">
            <p class="text-sm text-slate-500">Boletos em aberto</p>
            <p class="numerico text-2xl font-bold">{{ resumo.cobrancas_em_aberto }}</p>
          </div>
          <div class="cartao p-5">
            <p class="text-sm text-slate-500">Chamados abertos</p>
            <p class="numerico text-2xl font-bold">{{ resumo.chamados_abertos }}</p>
          </div>
          <div class="cartao p-5">
            <p class="text-sm text-slate-500">Laudos a assinar</p>
            <p class="numerico text-2xl font-bold">{{ resumo.vistorias_a_assinar }}</p>
          </div>
        </section>

        <!-- ---------------------------------------------------------- contrato -->
        <section v-if="aba === 'contrato'" class="space-y-4">
          <div v-if="contrato" class="cartao space-y-3 p-6">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="numerico text-sm text-slate-500">{{ contrato.numero }}</p>
                <h2 class="text-lg font-semibold text-slate-900">
                  {{ contrato.imovel_titulo }}
                </h2>
                <p class="text-sm text-slate-500">{{ contrato.imovel_endereco }}</p>
              </div>
              <span
                class="rounded-full bg-marca-suave px-3 py-1 text-sm font-medium text-marca-escura"
              >
                {{ contrato.status_display }}
              </span>
            </div>

            <dl class="grid gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt class="text-slate-500">Aluguel</dt>
                <dd class="numerico font-semibold">{{ moeda(contrato.valor) }}</dd>
              </div>
              <div>
                <dt class="text-slate-500">Vence todo dia</dt>
                <dd class="numerico font-semibold">{{ contrato.dia_vencimento }}</dd>
              </div>
              <div>
                <dt class="text-slate-500">Vigência</dt>
                <dd class="font-semibold">
                  {{ formatarData(contrato.data_inicio) }} a
                  {{ formatarData(contrato.data_fim) }}
                </dd>
              </div>
              <div>
                <dt class="text-slate-500">Próximo reajuste</dt>
                <dd class="font-semibold">
                  {{ formatarData(contrato.proximo_reajuste_em) }}
                </dd>
              </div>
            </dl>

            <a
              :href="portalService.urlContratoPdf(contrato.id)"
              target="_blank"
              rel="noopener"
              class="inline-block rounded-lg bg-marca px-4 py-2 text-sm font-semibold text-white hover:brightness-110"
            >
              Baixar contrato em PDF
            </a>
          </div>

          <p v-else class="cartao p-8 text-center text-slate-500">
            Você não tem contrato ativo no momento.
          </p>
        </section>

        <!-- --------------------------------------------------------- cobranças -->
        <section v-else-if="aba === 'cobrancas'" class="space-y-4">
          <div v-if="emAberto.length" class="cartao space-y-3 p-6">
            <h2 class="text-lg font-semibold text-slate-900">A pagar</h2>
            <article
              v-for="cobranca in emAberto"
              :key="cobranca.id"
              class="space-y-2 rounded-lg bg-slate-50 p-4"
            >
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p class="font-semibold text-slate-900">
                    {{ moeda(cobranca.valor_total) }}
                  </p>
                  <p class="text-sm text-slate-500">
                    Competência {{ formatarData(cobranca.competencia) }} · vence
                    {{ formatarData(cobranca.vencimento) }}
                    <span v-if="cobranca.dias_de_atraso > 0" class="font-medium text-red-600">
                      · {{ cobranca.dias_de_atraso }} dias em atraso
                    </span>
                  </p>
                </div>
                <div class="flex gap-2">
                  <button
                    v-if="cobranca.pix_copia_cola"
                    type="button"
                    class="rounded-lg bg-marca px-3 py-1.5 text-sm font-semibold text-white hover:brightness-110"
                    @click="copiar(cobranca.pix_copia_cola, 'Código Pix')"
                  >
                    Copiar Pix
                  </button>
                  <button
                    v-if="cobranca.linha_digitavel"
                    type="button"
                    class="rounded-lg px-3 py-1.5 text-sm ring-1 ring-slate-300 hover:bg-white"
                    @click="copiar(cobranca.linha_digitavel, 'Código de barras')"
                  >
                    Copiar boleto
                  </button>
                </div>
              </div>
              <p v-if="cobranca.valor_multa > 0" class="text-xs text-slate-500">
                Inclui {{ moeda(cobranca.valor_multa) }} de multa e
                {{ moeda(cobranca.valor_juros) }} de juros.
              </p>
            </article>
          </div>

          <div class="cartao p-6">
            <h2 class="mb-3 text-lg font-semibold text-slate-900">Histórico</h2>
            <table class="w-full text-sm">
              <thead class="text-left text-slate-500">
                <tr>
                  <th class="pb-2 font-medium">Competência</th>
                  <th class="pb-2 font-medium">Vencimento</th>
                  <th class="pb-2 font-medium">Valor</th>
                  <th class="pb-2 font-medium">Situação</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="cobranca in cobrancas" :key="cobranca.id">
                  <td class="py-2">{{ formatarData(cobranca.competencia) }}</td>
                  <td class="py-2">{{ formatarData(cobranca.vencimento) }}</td>
                  <td class="numerico py-2">{{ moeda(cobranca.valor_total) }}</td>
                  <td class="py-2">{{ cobranca.status_display }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ---------------------------------------------------------- chamados -->
        <section v-else-if="aba === 'chamados'" class="space-y-4">
          <form class="cartao space-y-3 p-6" @submit.prevent="abrirChamado">
            <h2 class="text-lg font-semibold text-slate-900">Abrir chamado</h2>
            <label class="block">
              <span class="mb-1 block text-sm font-medium text-slate-700">
                O que está acontecendo no imóvel?
              </span>
              <textarea
                v-model="novoChamado"
                rows="3"
                required
                placeholder="Ex.: infiltração no teto do banheiro"
                class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
              />
            </label>
            <button
              type="submit"
              :disabled="enviando || !novoChamado.trim()"
              class="rounded-lg bg-marca px-4 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
            >
              {{ enviando ? 'Enviando…' : 'Abrir chamado' }}
            </button>
          </form>

          <div v-for="chamado in chamados" :key="chamado.id" class="cartao space-y-2 p-6">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <p class="numerico text-sm text-slate-500">{{ chamado.protocolo }}</p>
              <span
                class="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700"
              >
                {{ chamado.status_display }}
              </span>
            </div>
            <p class="text-slate-800">{{ chamado.mensagem }}</p>
            <ol class="space-y-1 border-l border-slate-200 pl-3">
              <li v-for="(evento, indice) in chamado.eventos" :key="indice" class="text-sm">
                <p class="text-slate-700">{{ evento.descricao }}</p>
                <p class="text-xs text-slate-400">{{ dataHora(evento.criado_em) }}</p>
              </li>
            </ol>
          </div>

          <p v-if="!chamados.length" class="cartao p-8 text-center text-slate-500">
            Nenhum chamado aberto até agora.
          </p>
        </section>

        <!-- --------------------------------------------------------- vistorias -->
        <section v-else class="space-y-3">
          <article
            v-for="vistoria in vistorias"
            :key="vistoria.id"
            class="cartao flex flex-wrap items-center justify-between gap-3 p-6"
          >
            <div>
              <p class="font-semibold text-slate-900">{{ vistoria.tipo_display }}</p>
              <p class="text-sm text-slate-500">
                {{ formatarData(vistoria.realizada_em) }} · {{ vistoria.total_itens }} itens ·
                {{ vistoria.itens_com_problema }} com apontamento
              </p>
            </div>
            <button
              v-if="vistoria.status === 'FINALIZADA' && !vistoria.assinatura_locatario"
              type="button"
              class="rounded-lg bg-marca px-4 py-2 text-sm font-semibold text-white hover:brightness-110"
              @click="assinar(vistoria)"
            >
              Assinar laudo
            </button>
            <span v-else-if="vistoria.assinatura_locatario" class="text-sm text-emerald-700">
              Assinado por você
            </span>
            <span v-else class="text-sm text-slate-500">{{ vistoria.status_display }}</span>
          </article>

          <p v-if="!vistorias.length" class="cartao p-8 text-center text-slate-500">
            Nenhuma vistoria registrada no seu contrato.
          </p>
        </section>
      </template>
    </main>
  </div>
</template>
