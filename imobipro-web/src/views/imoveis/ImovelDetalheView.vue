<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import GaleriaFotos from '@/components/imoveis/GaleriaFotos.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'
import { imoveisService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { data as formatarData, dataHora, moeda } from '@/utils/formatters'

const route = useRoute()
const auth = useAuthStore()
const { sucesso, erroDaApi } = useToast()
const { perguntar } = useConfirmacao()

const ABAS = [
  { chave: 'dados', rotulo: 'Dados' },
  { chave: 'fotos', rotulo: 'Fotos e mídia' },
  { chave: 'proprietario', rotulo: 'Proprietário' },
  { chave: 'historico', rotulo: 'Histórico' },
]

const aba = ref('dados')
const imovel = ref(null)
const historico = ref([])
const carregando = ref(true)

const podeEditar = computed(() => auth.papel !== 'FINANCEIRO')

async function carregar() {
  carregando.value = true
  const { data } = await imoveisService.obter(route.params.id)
  imovel.value = data
  carregando.value = false
}

async function carregarHistorico() {
  const { data } = await imoveisService.historico(route.params.id)
  historico.value = data
}

async function publicar() {
  try {
    const { data } = await imoveisService.publicar(imovel.value.id)
    imovel.value = data
    sucesso('Imóvel publicado no site.')
  } catch (erro) {
    erroDaApi(erro, 'Ainda há pendências para publicar.')
  }
}

async function despublicar() {
  const motivo = await perguntar({
    titulo: 'Despublicar imóvel',
    mensagem: 'O imóvel sai do site e dos portais.',
    rotulo: 'Motivo',
  })
  if (motivo === null) return
  try {
    const { data } = await imoveisService.despublicar(imovel.value.id, motivo)
    imovel.value = data
    sucesso('Imóvel retirado do site.')
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function mudarSituacao(situacao) {
  try {
    const { data } = await imoveisService.mudarSituacao(imovel.value.id, situacao)
    imovel.value = data
    sucesso(`Situação alterada para ${data.situacao_display}.`)
  } catch (erro) {
    erroDaApi(erro, 'Transição de situação não permitida.')
  }
}

onMounted(async () => {
  await carregar()
  await carregarHistorico()
})
</script>

<template>
  <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando ficha…</p>

  <div v-else-if="imovel" class="space-y-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="text-sm font-medium text-slate-400">{{ imovel.codigo }}</span>
          <StatusBadge :status="imovel.situacao" :rotulo="imovel.situacao_display" />
          <span v-if="imovel.publicado_site" class="text-xs text-emerald-600">publicado</span>
        </div>
        <h1 class="mt-1 text-2xl font-bold text-slate-900">{{ imovel.titulo }}</h1>
        <p class="text-sm text-slate-500">
          {{ imovel.endereco.logradouro }}, {{ imovel.endereco.numero }}
          {{ imovel.endereco.bairro }}, {{ imovel.endereco.cidade }}/{{ imovel.endereco.uf }}
        </p>
      </div>

      <div v-if="podeEditar" class="flex flex-wrap gap-2">
        <RouterLink :to="{ name: 'imovel-editar', params: { id: imovel.id } }">
          <BaseButton variante="secundaria">Editar</BaseButton>
        </RouterLink>
        <BaseButton v-if="!imovel.publicado_site" @click="publicar">Publicar</BaseButton>
        <BaseButton v-else variante="secundaria" @click="despublicar">Despublicar</BaseButton>
        <BaseButton
          v-if="imovel.situacao === 'DISPONIVEL'"
          variante="secundaria"
          @click="mudarSituacao('RESERVADO')"
        >
          Reservar
        </BaseButton>
      </div>
    </header>

    <div
      v-if="imovel.pendencias_publicacao.length"
      class="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200"
    >
      <p class="font-semibold">Pendências para publicar</p>
      <ul class="mt-1 list-inside list-disc">
        <li v-for="pendencia in imovel.pendencias_publicacao" :key="pendencia">
          {{ pendencia }}
        </li>
      </ul>
    </div>

    <nav class="flex gap-1 border-b border-slate-200" aria-label="Seções do imóvel">
      <button
        v-for="item in ABAS"
        :key="item.chave"
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium transition"
        :class="
          aba === item.chave
            ? 'border-marca text-marca'
            : 'border-transparent text-slate-500 hover:text-slate-700'
        "
        :aria-current="aba === item.chave ? 'page' : undefined"
        @click="aba = item.chave"
      >
        {{ item.rotulo }}
      </button>
    </nav>

    <section v-if="aba === 'dados'" class="grid gap-4 lg:grid-cols-3">
      <BaseCard titulo="Valores" class="lg:col-span-1">
        <dl class="space-y-2 text-sm">
          <div v-if="imovel.valor_venda" class="flex justify-between">
            <dt class="text-slate-500">Venda</dt>
            <dd class="numerico font-semibold">{{ moeda(imovel.valor_venda) }}</dd>
          </div>
          <div v-if="imovel.valor_locacao" class="flex justify-between">
            <dt class="text-slate-500">Locação</dt>
            <dd class="numerico font-semibold">{{ moeda(imovel.valor_locacao) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Condomínio</dt>
            <dd class="numerico">{{ moeda(imovel.valor_condominio) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">IPTU mensal</dt>
            <dd class="numerico">{{ moeda(imovel.valor_iptu_mensal) }}</dd>
          </div>
        </dl>
      </BaseCard>

      <BaseCard titulo="Características" class="lg:col-span-2">
        <dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt class="text-slate-500">Quartos</dt>
            <dd>{{ imovel.quartos }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Suítes</dt>
            <dd>{{ imovel.suites }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Banheiros</dt>
            <dd>{{ imovel.banheiros }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Vagas</dt>
            <dd>{{ imovel.vagas }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Área útil</dt>
            <dd>{{ imovel.area_util ?? '' }} m²</dd>
          </div>
          <div>
            <dt class="text-slate-500">Mobiliado</dt>
            <dd>{{ imovel.mobiliado ? 'Sim' : 'Não' }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Aceita pet</dt>
            <dd>{{ imovel.aceita_pet ? 'Sim' : 'Não' }}</dd>
          </div>
          <div>
            <dt class="text-slate-500">Matrícula</dt>
            <dd>{{ imovel.matricula || '' }}</dd>
          </div>
        </dl>

        <ul v-if="imovel.caracteristicas_detalhe.length" class="mt-4 flex flex-wrap gap-2">
          <li
            v-for="item in imovel.caracteristicas_detalhe"
            :key="item.id"
            class="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700"
          >
            {{ item.nome }}
          </li>
        </ul>

        <p v-if="imovel.descricao" class="mt-4 whitespace-pre-line text-sm text-slate-600">
          {{ imovel.descricao }}
        </p>
      </BaseCard>
    </section>

    <section v-else-if="aba === 'fotos'">
      <GaleriaFotos
        :imovel-id="imovel.id"
        :fotos="imovel.fotos"
        :editavel="podeEditar"
        @atualizado="carregar"
      />
    </section>

    <section v-else-if="aba === 'proprietario'">
      <BaseCard titulo="Proprietário">
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between">
            <dt class="text-slate-500">Nome</dt>
            <dd>{{ imovel.proprietario_detalhe.nome }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">CPF/CNPJ</dt>
            <dd>{{ imovel.proprietario_detalhe.cpf_cnpj }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Telefone</dt>
            <dd>{{ imovel.proprietario_detalhe.telefone || '' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Captador</dt>
            <dd>{{ imovel.captador_nome || '' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Exclusividade até</dt>
            <dd>{{ formatarData(imovel.exclusividade_ate) }}</dd>
          </div>
        </dl>
      </BaseCard>
    </section>

    <section v-else>
      <BaseCard titulo="Histórico" subtitulo="Toda mudança de valor, situação e publicação">
        <ol class="space-y-3">
          <li
            v-for="evento in historico"
            :key="evento.id"
            class="flex flex-wrap items-baseline gap-2 border-b border-slate-100 pb-2 text-sm"
          >
            <span class="font-medium text-slate-800">{{ evento.tipo_display }}</span>
            <span class="text-slate-600">{{ evento.descricao }}</span>
            <span v-if="evento.valor_novo" class="numerico text-slate-500">
              {{ moeda(evento.valor_anterior) }} → {{ moeda(evento.valor_novo) }}
            </span>
            <span class="ml-auto text-xs text-slate-400">
              {{ dataHora(evento.criado_em) }}
              <template v-if="evento.usuario_nome"> · {{ evento.usuario_nome }}</template>
            </span>
          </li>
        </ol>
      </BaseCard>
    </section>
  </div>
</template>
