<script setup>
import { computed, onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useToast } from '@/composables/useToast'
import { ticketsService, usuariosService } from '@/services/api'
import { dataHora } from '@/utils/formatters'

const { sucesso, erroDaApi } = useToast()

const painel = ref(null)
const tickets = ref([])
const selecionado = ref(null)
const equipe = ref([])
const carregando = ref(true)
const filtros = ref({ status: '', search: '' })

const resposta = ref('')
const notaInterna = ref(false)
const agendamento = ref('')

const colunas = [
  { campo: 'protocolo', rotulo: 'Protocolo' },
  { campo: 'solicitante_nome', rotulo: 'Interessado' },
  { campo: 'imovel_codigo', rotulo: 'Imóvel' },
  { campo: 'analista_nome', rotulo: 'Analista' },
  { campo: 'status_display', rotulo: 'Situação' },
  { campo: 'prazo', rotulo: 'Prazo' },
]

const eventosVisiveis = computed(() => selecionado.value?.eventos ?? [])

async function carregar() {
  carregando.value = true
  try {
    const [lista, resumo] = await Promise.all([
      ticketsService.listar({ ...filtros.value, page_size: 50 }),
      ticketsService.painel(),
    ])
    tickets.value = lista.data.results ?? lista.data
    painel.value = resumo.data
  } finally {
    carregando.value = false
  }
}

async function abrir(ticket) {
  const { data } = await ticketsService.obter(ticket.id)
  selecionado.value = data
  resposta.value = ''
  agendamento.value = ''
}

async function enviarResposta() {
  try {
    const { data } = await ticketsService.responder(
      selecionado.value.id,
      resposta.value,
      !notaInterna.value,
    )
    selecionado.value = data
    resposta.value = ''
    sucesso(notaInterna.value ? 'Nota registrada.' : 'Resposta enviada ao interessado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível registrar a resposta.')
  }
}

async function mudarSituacao(status) {
  try {
    const { data } = await ticketsService.mudarSituacao(selecionado.value.id, {
      status,
      agendado_para: status === 'AGENDADO' ? agendamento.value : undefined,
    })
    selecionado.value = data
    sucesso('Atendimento atualizado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível mudar a situação.')
  }
}

async function reatribuir(analista) {
  try {
    const { data } = await ticketsService.reatribuir(selecionado.value.id, analista)
    selecionado.value = data
    sucesso('Atendimento repassado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível repassar o atendimento.')
  }
}

function prazo(ticket) {
  if (ticket.status === 'CONCLUIDO' || ticket.status === 'CANCELADO') return 'encerrado'
  if (ticket.minutos_para_resposta === null) return 'respondido'
  if (ticket.minutos_para_resposta < 0) {
    return `atrasado ${Math.abs(ticket.minutos_para_resposta)} min`
  }
  return `${ticket.minutos_para_resposta} min`
}

onMounted(async () => {
  await carregar()
  const { data } = await usuariosService.listar({ page_size: 50 })
  equipe.value = (data.results ?? data).map((pessoa) => ({
    value: pessoa.id,
    label: pessoa.nome_completo,
  }))
})
</script>

<template>
  <div class="space-y-5">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">Atendimento</h1>
      <p class="text-sm text-slate-500">
        Pedidos que chegaram pelo site, com prazo de primeira resposta
      </p>
    </header>

    <section v-if="painel" class="grid gap-3 sm:grid-cols-4" data-tour="painel-atendimento">
      <BaseCard>
        <p class="text-sm text-slate-500">Em aberto</p>
        <p class="numerico text-2xl font-bold">{{ painel.abertos }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Sem primeira resposta</p>
        <p class="numerico text-2xl font-bold">{{ painel.sem_resposta }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Prazo estourado</p>
        <p class="numerico text-2xl font-bold text-red-600">{{ painel.sla_estourado }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Visitas hoje</p>
        <p class="numerico text-2xl font-bold">{{ painel.agendados_hoje }}</p>
      </BaseCard>
    </section>

    <section class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-2">
      <BaseInput
        v-model="filtros.search"
        rotulo="Buscar"
        placeholder="protocolo, nome ou telefone"
        @change="carregar"
      />
      <BaseSelect
        v-model="filtros.status"
        rotulo="Situação"
        placeholder="Todas"
        :opcoes="[
          { value: 'ABERTO', label: 'Aberto' },
          { value: 'EM_ATENDIMENTO', label: 'Em atendimento' },
          { value: 'AGENDADO', label: 'Visita agendada' },
          { value: 'CONCLUIDO', label: 'Concluído' },
          { value: 'CANCELADO', label: 'Cancelado' },
        ]"
        @change="carregar"
      />
    </section>

    <DataEmptyState
      v-if="!carregando && !tickets.length"
      icone="☎"
      titulo="Nenhum pedido por aqui"
      descricao="Pedidos de visita feitos no site aparecem nesta fila, já com responsável."
    />

    <div v-else class="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
      <BaseTable
        :colunas="colunas"
        :linhas="tickets"
        :carregando="carregando"
        @selecionar="abrir"
      >
        <template #status_display="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #prazo="{ linha }">
          <span :class="linha.sla_estourado ? 'font-medium text-red-600' : 'text-slate-500'">
            {{ prazo(linha) }}
          </span>
        </template>
      </BaseTable>

      <BaseCard v-if="selecionado" :titulo="selecionado.protocolo">
        <div class="space-y-4">
          <div>
            <p class="font-semibold text-slate-900">{{ selecionado.solicitante_nome }}</p>
            <p class="text-sm text-slate-500">
              {{ selecionado.solicitante_telefone }}
              <span v-if="selecionado.solicitante_email">
                · {{ selecionado.solicitante_email }}
              </span>
            </p>
            <p v-if="selecionado.imovel_codigo" class="text-sm text-slate-500">
              {{ selecionado.imovel_codigo }} · {{ selecionado.imovel_titulo }}
            </p>
            <p v-if="selecionado.mensagem" class="mt-2 rounded-lg bg-slate-50 p-3 text-sm">
              {{ selecionado.mensagem }}
            </p>
            <p v-if="selecionado.preferencia_data" class="mt-1 text-sm text-slate-500">
              Prefere {{ selecionado.preferencia_data }} ·
              {{ selecionado.preferencia_periodo?.toLowerCase() }}
            </p>
          </div>

          <div class="space-y-2">
            <label class="block text-sm font-medium text-slate-700" for="resposta">
              Responder
            </label>
            <textarea
              id="resposta"
              v-model="resposta"
              rows="3"
              placeholder="Escreva o retorno ao interessado"
              class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
            />
            <label class="flex items-center gap-2 text-sm text-slate-600">
              <input v-model="notaInterna" type="checkbox" class="size-4 rounded" />
              nota interna (não aparece para o cliente)
            </label>
            <BaseButton :desabilitado="!resposta.trim()" @click="enviarResposta">
              Registrar
            </BaseButton>
          </div>

          <div class="space-y-2 border-t border-slate-100 pt-3">
            <label class="block text-sm font-medium text-slate-700" for="agendamento">
              Agendar visita
            </label>
            <input
              id="agendamento"
              v-model="agendamento"
              type="datetime-local"
              class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
            />
            <div class="flex flex-wrap gap-2">
              <BaseButton
                variante="secundaria"
                :desabilitado="!agendamento"
                @click="mudarSituacao('AGENDADO')"
              >
                Confirmar visita
              </BaseButton>
              <BaseButton variante="secundaria" @click="mudarSituacao('CONCLUIDO')">
                Concluir
              </BaseButton>
              <BaseButton variante="secundaria" @click="mudarSituacao('CANCELADO')">
                Cancelar
              </BaseButton>
            </div>
          </div>

          <div class="space-y-2 border-t border-slate-100 pt-3">
            <BaseSelect
              :model-value="selecionado.analista"
              rotulo="Analista responsável"
              :opcoes="equipe"
              @update:model-value="reatribuir"
            />
          </div>

          <div class="border-t border-slate-100 pt-3">
            <h3 class="mb-2 text-sm font-semibold text-slate-900">Linha do tempo</h3>
            <ol class="space-y-2 border-l border-slate-200 pl-3">
              <li v-for="evento in eventosVisiveis" :key="evento.id" class="text-sm">
                <p class="text-slate-800">
                  {{ evento.descricao }}
                  <span v-if="!evento.visivel_ao_cliente" class="text-xs text-amber-700">
                    (interno)
                  </span>
                </p>
                <p class="text-xs text-slate-400">
                  {{ dataHora(evento.criado_em) }}
                  <span v-if="evento.usuario_nome">· {{ evento.usuario_nome }}</span>
                </p>
              </li>
            </ol>
          </div>
        </div>
      </BaseCard>

      <BaseCard v-else titulo="Selecione um atendimento">
        <p class="text-sm text-slate-500">
          Clique em uma linha da fila para ver o histórico, responder e agendar a visita.
        </p>
      </BaseCard>
    </div>
  </div>
</template>
