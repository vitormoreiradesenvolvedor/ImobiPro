<script setup>
import { computed, onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useToast } from '@/composables/useToast'
import { candidaturasService, imoveisService } from '@/services/api'
import { dataHora, moeda } from '@/utils/formatters'

const { sucesso, erro: avisar, erroDaApi } = useToast()

const painel = ref(null)
const candidaturas = ref([])
const selecionada = ref(null)
const carregando = ref(true)
const filtros = ref({ status: '', search: '' })

const novaCandidatura = ref(null)
const imoveis = ref([])
const contrato = ref(null)
const recusa = ref(null)

const colunas = [
  { campo: 'protocolo', rotulo: 'Protocolo' },
  { campo: 'pretendente_nome', rotulo: 'Pretendente' },
  { campo: 'imovel_codigo', rotulo: 'Imóvel' },
  { campo: 'renda', rotulo: 'Renda x aluguel' },
  { campo: 'status_display', rotulo: 'Etapa' },
]

const podeAprovar = computed(
  () =>
    selecionada.value?.status === 'EM_ANALISE' &&
    selecionada.value?.documentacao_completa &&
    !selecionada.value?.documentos?.some((d) => d.status !== 'APROVADO'),
)

async function carregar() {
  carregando.value = true
  try {
    const [lista, resumo] = await Promise.all([
      candidaturasService.listar({ ...filtros.value, page_size: 50 }),
      candidaturasService.painel(),
    ])
    candidaturas.value = lista.data.results ?? lista.data
    painel.value = resumo.data
  } finally {
    carregando.value = false
  }
}

async function abrir(candidatura) {
  const { data } = await candidaturasService.obter(candidatura.id)
  selecionada.value = data
}

async function abrirNova() {
  const { data } = await imoveisService.listar({ situacao: 'DISPONIVEL', page_size: 50 })
  imoveis.value = (data.results ?? data).map((imovel) => ({
    value: imovel.id,
    label: `${imovel.codigo} · ${imovel.titulo}`,
  }))
  novaCandidatura.value = {
    imovel: '',
    pretendente_nome: '',
    pretendente_cpf: '',
    pretendente_telefone: '',
    pretendente_email: '',
    renda_mensal: '',
    ocupacao: '',
  }
}

async function salvarNova() {
  try {
    const { data } = await candidaturasService.criar(novaCandidatura.value)
    novaCandidatura.value = null
    selecionada.value = data
    sucesso(`Candidatura ${data.protocolo} aberta. Mande o link ao pretendente.`)
    await carregar()
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível abrir a candidatura.')
  }
}

async function conferir(documento, aprovado) {
  if (!aprovado) {
    recusa.value = { documento, observacao: '' }
    return
  }
  try {
    const { data } = await candidaturasService.conferir(
      selecionada.value.id,
      documento.id,
      true,
    )
    selecionada.value = data
    sucesso('Documento conferido.')
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível conferir o documento.')
  }
}

async function confirmarRecusa() {
  try {
    const { data } = await candidaturasService.conferir(
      selecionada.value.id,
      recusa.value.documento.id,
      false,
      recusa.value.observacao,
    )
    selecionada.value = data
    recusa.value = null
    sucesso('Documento recusado. O cliente vê o motivo no link dele.')
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível recusar o documento.')
  }
}

async function decidir(status, observacao = '') {
  try {
    const { data } = await candidaturasService.decidir(selecionada.value.id, status, observacao)
    selecionada.value = data
    sucesso('Candidatura atualizada.')
    await carregar()
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível concluir a análise.')
  }
}

function abrirContrato() {
  const hoje = new Date()
  const fim = new Date(hoje.getFullYear() + 1, hoje.getMonth(), hoje.getDate())
  contrato.value = {
    data_inicio: hoje.toISOString().slice(0, 10),
    data_fim: fim.toISOString().slice(0, 10),
    valor: '',
    dia_vencimento: 10,
    taxa_administracao_percent: '10',
    garantia_tipo: 'CAUCAO',
    garantia_valor: '',
  }
}

async function gerarContrato() {
  try {
    const { data } = await candidaturasService.gerarContrato(
      selecionada.value.id,
      contrato.value,
    )
    selecionada.value = data
    contrato.value = null
    sucesso(`Contrato ${data.contrato_numero} criado como rascunho.`)
    await carregar()
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível gerar o contrato.')
  }
}

async function copiarLink() {
  try {
    await navigator.clipboard.writeText(selecionada.value.link_do_cliente)
    sucesso('Link copiado. Mande ao pretendente.')
  } catch {
    avisar('Copie o link manualmente pelo campo ao lado.')
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Candidaturas</h1>
        <p class="text-sm text-slate-500">
          Da documentação do pretendente até o contrato assinado
        </p>
      </div>
      <BaseButton @click="abrirNova">Nova candidatura</BaseButton>
    </header>

    <section v-if="painel" class="grid gap-3 sm:grid-cols-4">
      <BaseCard>
        <p class="text-sm text-slate-500">Aguardando documentos</p>
        <p class="numerico text-2xl font-bold">{{ painel.aguardando_documentos }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Em análise</p>
        <p class="numerico text-2xl font-bold">{{ painel.em_analise }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Pendência com o cliente</p>
        <p class="numerico text-2xl font-bold text-amber-600">{{ painel.com_pendencia }}</p>
      </BaseCard>
      <BaseCard>
        <p class="text-sm text-slate-500">Aprovadas sem contrato</p>
        <p class="numerico text-2xl font-bold text-marca">
          {{ painel.aprovadas_sem_contrato }}
        </p>
      </BaseCard>
    </section>

    <section class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-2">
      <BaseInput
        v-model="filtros.search"
        rotulo="Buscar"
        placeholder="protocolo, nome ou CPF"
        @change="carregar"
      />
      <BaseSelect
        v-model="filtros.status"
        rotulo="Etapa"
        placeholder="Todas"
        :opcoes="[
          { value: 'RASCUNHO', label: 'Aguardando documentos' },
          { value: 'EM_ANALISE', label: 'Em análise' },
          { value: 'PENDENTE', label: 'Pendência com o cliente' },
          { value: 'APROVADA', label: 'Aprovada' },
          { value: 'REPROVADA', label: 'Reprovada' },
          { value: 'DESISTIU', label: 'Cliente desistiu' },
        ]"
        @change="carregar"
      />
    </section>

    <DataEmptyState
      v-if="!carregando && !candidaturas.length"
      icone="✎"
      titulo="Nenhuma candidatura em andamento"
      descricao="Abra uma candidatura para receber os documentos do pretendente por link."
    >
      <template #acao><BaseButton @click="abrirNova">Nova candidatura</BaseButton></template>
    </DataEmptyState>

    <div v-else class="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
      <BaseTable
        :colunas="colunas"
        :linhas="candidaturas"
        :carregando="carregando"
        @selecionar="abrir"
      >
        <template #status_display="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #renda="{ linha }">
          <span v-if="linha.relacao_renda_aluguel" class="numerico">
            {{ linha.relacao_renda_aluguel }}x
          </span>
          <span v-else class="text-slate-400">sem renda</span>
        </template>
      </BaseTable>

      <BaseCard v-if="selecionada" :titulo="selecionada.protocolo">
        <div class="space-y-4">
          <div>
            <p class="font-semibold text-slate-900">{{ selecionada.pretendente_nome }}</p>
            <p class="text-sm text-slate-500">
              {{ selecionada.pretendente_telefone }}
              <span v-if="selecionada.pretendente_email">
                · {{ selecionada.pretendente_email }}
              </span>
            </p>
            <p class="text-sm text-slate-500">
              {{ selecionada.imovel_codigo }} · {{ selecionada.imovel_titulo }}
            </p>
            <p v-if="selecionada.renda_mensal" class="text-sm text-slate-500">
              Renda {{ moeda(selecionada.renda_mensal) }}
              <span v-if="selecionada.relacao_renda_aluguel">
                ({{ selecionada.relacao_renda_aluguel }}x o aluguel)
              </span>
            </p>
          </div>

          <div class="rounded-lg bg-slate-50 p-3">
            <p class="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
              Link do pretendente
            </p>
            <p class="break-all text-xs text-slate-600">{{ selecionada.link_do_cliente }}</p>
            <BaseButton variante="fantasma" @click="copiarLink">Copiar link</BaseButton>
          </div>

          <div>
            <h3 class="mb-2 text-sm font-semibold text-slate-900">Documentos</h3>
            <p v-if="!selecionada.documentos.length" class="text-sm text-slate-500">
              Nada enviado ainda.
            </p>
            <ul class="divide-y divide-slate-100">
              <li
                v-for="documento in selecionada.documentos"
                :key="documento.id"
                class="flex flex-wrap items-center justify-between gap-2 py-2"
              >
                <div class="min-w-0">
                  <a
                    :href="documento.arquivo"
                    target="_blank"
                    rel="noopener"
                    class="text-sm font-medium text-marca hover:underline"
                  >
                    {{ documento.tipo_display }}
                  </a>
                  <p class="text-xs text-slate-500">
                    {{ documento.status_display }}
                    <span v-if="documento.observacao">· {{ documento.observacao }}</span>
                  </p>
                </div>
                <div v-if="documento.status === 'ENVIADO'" class="flex gap-2">
                  <BaseButton variante="fantasma" @click="conferir(documento, true)">
                    Conferir
                  </BaseButton>
                  <BaseButton variante="fantasma" @click="conferir(documento, false)">
                    Recusar
                  </BaseButton>
                </div>
              </li>
            </ul>

            <p
              v-if="selecionada.documentos_pendentes.length"
              class="mt-2 text-xs text-amber-700"
            >
              Faltam:
              {{ selecionada.documentos_pendentes.map((d) => d.rotulo).join(', ') }}
            </p>
          </div>

          <div class="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            <BaseButton :desabilitado="!podeAprovar" @click="decidir('APROVADA')">
              Aprovar
            </BaseButton>
            <BaseButton
              variante="secundaria"
              @click="decidir('REPROVADA', 'Análise de crédito não aprovada.')"
            >
              Reprovar
            </BaseButton>
            <BaseButton
              v-if="selecionada.status === 'APROVADA' && !selecionada.contrato"
              @click="abrirContrato"
            >
              Gerar contrato
            </BaseButton>
            <p v-if="selecionada.contrato_numero" class="self-center text-sm text-slate-500">
              Contrato {{ selecionada.contrato_numero }} criado.
            </p>
          </div>

          <div class="border-t border-slate-100 pt-3">
            <h3 class="mb-2 text-sm font-semibold text-slate-900">Histórico</h3>
            <ol class="space-y-2 border-l border-slate-200 pl-3">
              <li v-for="evento in selecionada.eventos" :key="evento.id" class="text-sm">
                <p class="text-slate-800">
                  {{ evento.descricao }}
                  <span v-if="!evento.visivel_ao_cliente" class="text-xs text-amber-700">
                    (interno)
                  </span>
                </p>
                <p class="text-xs text-slate-400">{{ dataHora(evento.criado_em) }}</p>
              </li>
            </ol>
          </div>
        </div>
      </BaseCard>

      <BaseCard v-else titulo="Selecione uma candidatura">
        <p class="text-sm text-slate-500">
          Clique numa linha para conferir documentos, aprovar e gerar o contrato.
        </p>
      </BaseCard>
    </div>

    <BaseModal
      v-if="novaCandidatura"
      titulo="Nova candidatura"
      largura="max-w-2xl"
      @fechar="novaCandidatura = null"
    >
      <form class="space-y-4" @submit.prevent="salvarNova">
        <BaseSelect
          v-model="novaCandidatura.imovel"
          rotulo="Imóvel"
          :opcoes="imoveis"
          placeholder="Selecione o imóvel disponível"
          obrigatorio
        />
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseInput v-model="novaCandidatura.pretendente_nome" rotulo="Nome" obrigatorio />
          <BaseInput v-model="novaCandidatura.pretendente_cpf" rotulo="CPF" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseInput
            v-model="novaCandidatura.pretendente_telefone"
            rotulo="Telefone"
            obrigatorio
          />
          <BaseInput v-model="novaCandidatura.pretendente_email" rotulo="E-mail" tipo="email" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <MoneyInput v-model="novaCandidatura.renda_mensal" rotulo="Renda mensal" />
          <BaseInput v-model="novaCandidatura.ocupacao" rotulo="Ocupação" />
        </div>
      </form>
      <template #rodape>
        <BaseButton variante="secundaria" @click="novaCandidatura = null">Cancelar</BaseButton>
        <BaseButton @click="salvarNova">Abrir candidatura</BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-if="recusa" titulo="Recusar documento" @fechar="recusa = null">
      <p class="mb-3 text-sm text-slate-600">
        O motivo aparece para o pretendente no link dele, junto com o pedido de reenvio.
      </p>
      <BaseInput v-model="recusa.observacao" rotulo="O que está errado" obrigatorio />
      <template #rodape>
        <BaseButton variante="secundaria" @click="recusa = null">Cancelar</BaseButton>
        <BaseButton :desabilitado="!recusa.observacao.trim()" @click="confirmarRecusa">
          Recusar documento
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal
      v-if="contrato"
      titulo="Gerar contrato"
      largura="max-w-2xl"
      @fechar="contrato = null"
    >
      <form class="space-y-4" @submit.prevent="gerarContrato">
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseInput v-model="contrato.data_inicio" rotulo="Início" tipo="date" obrigatorio />
          <BaseInput v-model="contrato.data_fim" rotulo="Término" tipo="date" obrigatorio />
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <MoneyInput v-model="contrato.valor" rotulo="Valor do aluguel" />
          <BaseInput
            v-model="contrato.dia_vencimento"
            rotulo="Dia de vencimento"
            tipo="number"
          />
          <BaseInput
            v-model="contrato.taxa_administracao_percent"
            rotulo="Taxa de administração (%)"
          />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseSelect
            v-model="contrato.garantia_tipo"
            rotulo="Garantia"
            :opcoes="[
              'FIADOR',
              'CAUCAO',
              'SEGURO_FIANCA',
              'TITULO_CAPITALIZACAO',
              'SEM_GARANTIA',
            ]"
          />
          <MoneyInput v-model="contrato.garantia_valor" rotulo="Valor da garantia" />
        </div>
        <p class="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          O contrato nasce como rascunho, com locador e locatário já preenchidos. A ativação
          continua sendo um passo separado.
        </p>
      </form>
      <template #rodape>
        <BaseButton variante="secundaria" @click="contrato = null">Cancelar</BaseButton>
        <BaseButton @click="gerarContrato">Criar rascunho</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
