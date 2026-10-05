<script setup>
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'
import { visitasService } from '@/services/api'

const { sucesso, erroDaApi } = useToast()
const { confirmar } = useConfirmacao()

const dia = ref(new Date().toISOString().slice(0, 10))
const visitas = ref([])
const carregando = ref(true)
const feedback = ref(null)

async function carregar() {
  carregando.value = true
  const { data } = await visitasService.agenda(dia.value)
  visitas.value = data
  carregando.value = false
}

function hora(iso) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

async function cancelar(visita) {
  const confirmado = await confirmar({
    titulo: 'Cancelar visita',
    mensagem: `A visita de ${visita.lead_nome} será marcada como cancelada.`,
    confirmar: 'Cancelar visita',
    perigo: true,
  })
  if (!confirmado) return
  try {
    await visitasService.cancelar(visita.id)
    sucesso('Visita cancelada.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function salvarFeedback() {
  try {
    await visitasService.feedback(feedback.value.id, {
      feedback: feedback.value.texto,
      interesse_pos_visita: feedback.value.interesse,
    })
    sucesso('Feedback registrado e lead movido no funil.')
    feedback.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

watch(dia, carregar)
onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Agenda de visitas</h1>
        <p class="text-sm text-slate-500">{{ visitas.length }} visitas no dia selecionado</p>
      </div>
      <div class="w-44">
        <BaseInput v-model="dia" rotulo="Dia" tipo="date" />
      </div>
    </header>

    <p v-if="carregando" class="py-10 text-center text-slate-400">Carregando agenda…</p>

    <DataEmptyState
      v-else-if="!visitas.length"
      icone="▤"
      titulo="Nenhuma visita neste dia"
      descricao="Agende visitas a partir da ficha do lead, no CRM."
    >
      <template #acao>
        <RouterLink :to="{ name: 'crm' }">
          <BaseButton variante="secundaria">Ir para o funil</BaseButton>
        </RouterLink>
      </template>
    </DataEmptyState>

    <ol v-else class="space-y-3">
      <li
        v-for="visita in visitas"
        :key="visita.id"
        class="flex flex-wrap items-center gap-4 rounded-xl bg-white p-4 ring-1 ring-slate-200"
      >
        <span class="numerico w-16 text-lg font-bold text-marca">
          {{ hora(visita.agendada_para) }}
        </span>

        <div class="min-w-48 flex-1">
          <p class="font-medium text-slate-900">{{ visita.lead_nome }}</p>
          <p class="text-sm text-slate-500">
            {{ visita.imovel_codigo }} {{ visita.imovel_titulo }}
          </p>
        </div>

        <span v-if="visita.realizada" class="text-sm text-emerald-600">realizada</span>
        <span v-else-if="visita.atrasada" class="text-sm text-red-600">atrasada</span>

        <div class="flex gap-2">
          <BaseButton
            v-if="!visita.realizada"
            variante="secundaria"
            @click="feedback = { id: visita.id, texto: '', interesse: 'MEDIO' }"
          >
            Registrar feedback
          </BaseButton>
          <BaseButton v-if="!visita.realizada" variante="fantasma" @click="cancelar(visita)">
            Cancelar
          </BaseButton>
        </div>
      </li>
    </ol>

    <BaseModal v-if="feedback" titulo="Feedback da visita" @fechar="feedback = null">
      <div class="space-y-4">
        <BaseTextarea v-model="feedback.texto" rotulo="Como foi a visita" :linhas="4" />
        <BaseSelect
          v-model="feedback.interesse"
          rotulo="Interesse do cliente"
          :opcoes="[
            { value: 'ALTO', label: 'Quer fazer proposta' },
            { value: 'MEDIO', label: 'Vai pensar' },
            { value: 'BAIXO', label: 'Não gostou' },
          ]"
        />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="feedback = null">Cancelar</BaseButton>
        <BaseButton @click="salvarFeedback">Salvar</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
