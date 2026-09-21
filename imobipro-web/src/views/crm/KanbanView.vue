<script setup>
import { onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import KanbanBoard from '@/components/crm/KanbanBoard.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import { useToast } from '@/composables/useToast'
import { leadsService } from '@/services/api'

const { sucesso, erroDaApi } = useToast()

const MOTIVOS = [
  { value: 'PRECO', label: 'Preço acima do esperado' },
  { value: 'LOCALIZACAO', label: 'Localização' },
  { value: 'CREDITO_NEGADO', label: 'Crédito negado' },
  { value: 'CONCORRENTE', label: 'Fechou com concorrente' },
  { value: 'DESISTIU', label: 'Desistiu' },
  { value: 'SEM_RETORNO', label: 'Não respondeu' },
  { value: 'IMOVEL_INDISPONIVEL', label: 'Imóvel ficou indisponível' },
]

const colunas = ref([])
const carregando = ref(true)
const estatisticas = ref(null)

const perda = ref(null)
const motivo = ref('PRECO')
const observacao = ref('')

const novoLead = ref(null)

async function carregar() {
  carregando.value = true
  const [funil, dados] = await Promise.all([leadsService.funil(), leadsService.estatisticas()])
  colunas.value = funil.data
  estatisticas.value = dados.data
  carregando.value = false
}

async function mover({ lead, estagio }) {
  // Perder exige motivo: o back recusa sem ele, então abrimos o diálogo antes.
  if (estagio === 'FECHADO_PERDIDO') {
    perda.value = lead
    return
  }
  await aplicarMovimento(lead, estagio)
}

async function aplicarMovimento(lead, estagio, extras = {}) {
  try {
    await leadsService.mover(lead.id, { estagio, ...extras })
    sucesso(`${lead.nome} movido.`)
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível mover o lead.')
  }
}

async function confirmarPerda() {
  await aplicarMovimento(perda.value, 'FECHADO_PERDIDO', {
    motivo_perda: motivo.value,
    observacao: observacao.value,
  })
  perda.value = null
  observacao.value = ''
}

function abrirNovoLead() {
  novoLead.value = { nome: '', email: '', telefone: '', origem: 'TELEFONE', valor_estimado: '' }
}

async function salvarLead() {
  try {
    await leadsService.criar(novoLead.value)
    sucesso('Lead cadastrado e distribuído.')
    novoLead.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível cadastrar o lead.')
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Funil de vendas</h1>
        <p v-if="estatisticas" class="text-sm text-slate-500" data-tour="metricas-funil">
          {{ estatisticas.abertos }} leads abertos · conversão
          {{ estatisticas.taxa_conversao }}% · SLA cumprido
          {{ estatisticas.sla_cumprido_percentual }}%
        </p>
      </div>
      <BaseButton data-tour="novo-lead" @click="abrirNovoLead">Novo lead</BaseButton>
    </header>

    <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando funil…</p>
    <KanbanBoard v-else :colunas="colunas" data-tour="kanban" @mover="mover" />

    <BaseModal v-if="perda" titulo="Por que perdemos este lead?" @fechar="perda = null">
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          O motivo alimenta o relatório de perdas por isso é obrigatório.
        </p>
        <BaseSelect v-model="motivo" rotulo="Motivo" :opcoes="MOTIVOS" />
        <BaseInput v-model="observacao" rotulo="Observação (opcional)" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="perda = null">Cancelar</BaseButton>
        <BaseButton variante="perigo" @click="confirmarPerda">Marcar como perdido</BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-if="novoLead" titulo="Novo lead" @fechar="novoLead = null">
      <div class="space-y-4">
        <BaseInput v-model="novoLead.nome" rotulo="Nome" obrigatorio />
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseInput v-model="novoLead.email" rotulo="E-mail" tipo="email" />
          <BaseInput v-model="novoLead.telefone" rotulo="Telefone" />
        </div>
        <BaseSelect
          v-model="novoLead.origem"
          rotulo="Origem"
          :opcoes="['TELEFONE', 'WHATSAPP', 'INDICACAO', 'PLANTAO', 'PLACA', 'REDES_SOCIAIS']"
        />
        <MoneyInput v-model="novoLead.valor_estimado" rotulo="Valor estimado" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="novoLead = null">Cancelar</BaseButton>
        <BaseButton @click="salvarLead">Cadastrar</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
