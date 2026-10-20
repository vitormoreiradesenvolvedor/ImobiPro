<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import TimelineLead from '@/components/crm/TimelineLead.vue'
import { useToast } from '@/composables/useToast'
import { imoveisService, leadsService, propostasService, visitasService } from '@/services/api'
import { dataHora, moeda, telefone as formatarTelefone } from '@/utils/formatters'

const route = useRoute()
const { sucesso, erroDaApi } = useToast()

const lead = ref(null)
const carregando = ref(true)
const imoveis = ref([])

const interacao = ref({ tipo: 'LIGACAO', descricao: '' })
const visita = ref(null)
const proposta = ref(null)

async function carregar() {
  carregando.value = true
  const { data } = await leadsService.obter(route.params.id)
  lead.value = data
  carregando.value = false
}

async function registrarInteracao() {
  if (!interacao.value.descricao.trim()) return
  try {
    // Cópia: o formulário é limpo logo em seguida e não pode alterar o
    // que já foi enviado.
    await leadsService.registrarInteracao(lead.value.id, { ...interacao.value })
    interacao.value.descricao = ''
    sucesso('Interação registrada. Cronômetro do SLA parado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function abrirVisita() {
  const { data } = await imoveisService.listar({ situacao: 'DISPONIVEL', page_size: 50 })
  imoveis.value = (data.results ?? data).map((imovel) => ({
    value: imovel.id,
    label: `${imovel.codigo} ${imovel.titulo}`,
  }))
  visita.value = { imovel: lead.value.imovel_interesse ?? '', agendada_para: '' }
}

async function salvarVisita() {
  try {
    await visitasService.criar({
      lead: lead.value.id,
      imovel: visita.value.imovel,
      agendada_para: new Date(visita.value.agendada_para).toISOString(),
    })
    sucesso('Visita agendada.')
    visita.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível agendar a visita.')
  }
}

async function abrirProposta() {
  await abrirVisita()
  visita.value = null
  proposta.value = {
    imovel: lead.value.imovel_interesse ?? '',
    valor_ofertado: '',
    condicoes_pagamento: '',
    validade: '',
  }
}

async function salvarProposta() {
  try {
    await propostasService.criar({ lead: lead.value.id, ...proposta.value })
    sucesso('Proposta registrada.')
    proposta.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível registrar a proposta.')
  }
}

onMounted(carregar)
</script>

<template>
  <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando lead…</p>

  <div v-else-if="lead" class="grid gap-6 lg:grid-cols-3">
    <div class="space-y-6 lg:col-span-2">
      <header>
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="text-2xl font-bold text-slate-900">{{ lead.nome }}</h1>
          <StatusBadge :status="lead.estagio" :rotulo="lead.estagio_display" />
          <span
            v-if="lead.sla_estourado"
            class="rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700"
          >
            SLA estourado
          </span>
        </div>
        <p class="mt-1 text-sm text-slate-500">
          {{ lead.origem_display }} · {{ formatarTelefone(lead.telefone) }} ·
          {{ lead.email || 'sem e-mail' }}
        </p>
      </header>

      <BaseCard titulo="Registrar interação">
        <form class="space-y-3" @submit.prevent="registrarInteracao">
          <BaseSelect
            v-model="interacao.tipo"
            rotulo="Tipo"
            :opcoes="['LIGACAO', 'WHATSAPP', 'EMAIL', 'NOTA']"
          />
          <BaseTextarea
            v-model="interacao.descricao"
            rotulo="O que aconteceu"
            placeholder="Cliente atendeu, quer visitar no sábado de manhã."
            :linhas="3"
          />
          <div class="flex flex-wrap gap-2">
            <BaseButton tipo="submit">Registrar</BaseButton>
            <BaseButton variante="secundaria" @click="abrirVisita">Agendar visita</BaseButton>
            <BaseButton variante="secundaria" @click="abrirProposta">Nova proposta</BaseButton>
          </div>
        </form>
      </BaseCard>

      <BaseCard titulo="Linha do tempo" subtitulo="Nada é apagado tudo vira histórico">
        <TimelineLead :interacoes="lead.interacoes" />
      </BaseCard>
    </div>

    <aside class="space-y-4">
      <BaseCard titulo="Resumo">
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between">
            <dt class="text-slate-500">Corretor</dt>
            <dd>{{ lead.corretor_nome || 'não atribuído' }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Valor estimado</dt>
            <dd class="numerico">{{ moeda(lead.valor_estimado) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Temperatura</dt>
            <dd>{{ lead.temperatura }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">1º contato</dt>
            <dd>{{ dataHora(lead.primeiro_contato_em) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">SLA</dt>
            <dd>
              <span v-if="lead.sla_cumprido === true" class="text-emerald-600">cumprido</span>
              <span v-else-if="lead.sla_cumprido === false" class="text-red-600"
                >descumprido</span
              >
              <span v-else class="text-slate-400">aguardando</span>
            </dd>
          </div>
        </dl>
      </BaseCard>

      <BaseCard v-if="lead.imovel_detalhe" titulo="Imóvel de interesse">
        <p class="text-sm font-medium text-slate-900">{{ lead.imovel_detalhe.codigo }}</p>
        <p class="text-sm text-slate-600">{{ lead.imovel_detalhe.titulo }}</p>
        <p class="numerico mt-2 text-sm">
          {{ moeda(lead.imovel_detalhe.valor_venda ?? lead.imovel_detalhe.valor_locacao) }}
        </p>
      </BaseCard>

      <BaseCard v-if="lead.mensagem" titulo="Mensagem do cliente">
        <p class="whitespace-pre-line text-sm text-slate-600">{{ lead.mensagem }}</p>
      </BaseCard>
    </aside>

    <BaseModal v-if="visita" titulo="Agendar visita" @fechar="visita = null">
      <div class="space-y-4">
        <BaseSelect
          v-model="visita.imovel"
          rotulo="Imóvel"
          :opcoes="imoveis"
          placeholder="Selecione o imóvel"
        />
        <BaseInput v-model="visita.agendada_para" rotulo="Data e hora" tipo="datetime-local" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="visita = null">Cancelar</BaseButton>
        <BaseButton @click="salvarVisita">Agendar</BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-if="proposta" titulo="Nova proposta" @fechar="proposta = null">
      <div class="space-y-4">
        <BaseSelect
          v-model="proposta.imovel"
          rotulo="Imóvel"
          :opcoes="imoveis"
          placeholder="Selecione o imóvel"
        />
        <MoneyInput v-model="proposta.valor_ofertado" rotulo="Valor ofertado" />
        <BaseTextarea v-model="proposta.condicoes_pagamento" rotulo="Condições de pagamento" />
        <BaseInput v-model="proposta.validade" rotulo="Validade" tipo="date" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="proposta = null">Cancelar</BaseButton>
        <BaseButton @click="salvarProposta">Registrar proposta</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
