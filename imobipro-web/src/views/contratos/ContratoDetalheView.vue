<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useToast } from '@/composables/useToast'
import { contratosService, vistoriasService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { data as formatarData, moeda, decimalParaApi } from '@/utils/formatters'

const route = useRoute()
const auth = useAuthStore()
const { sucesso, erroDaApi } = useToast()

const contrato = ref(null)
const carregando = ref(true)
const rescisao = ref(null)
const reajuste = ref(null)
const previa = ref(null)
const acessoCriado = ref(null)

const ehRascunho = computed(() => contrato.value?.status === 'RASCUNHO')
const ehAtivo = computed(() => contrato.value?.status === 'ATIVO')

async function carregar() {
  carregando.value = true
  const { data } = await contratosService.obter(route.params.id)
  contrato.value = data
  carregando.value = false
}

async function ativar() {
  try {
    const { data } = await contratosService.ativar(contrato.value.id)
    contrato.value = data
    sucesso('Contrato ativado. Imóvel e cobranças atualizados.')
  } catch (erro) {
    erroDaApi(erro, 'Há pendências que impedem a ativação.')
  }
}

/**
 * Libera o portal do cliente depois da assinatura.
 *
 * A senha provisória volta uma vez só e fica na tela para a imobiliária
 * entregar ao inquilino; não é guardada em lugar nenhum do front.
 */
async function criarAcesso() {
  try {
    const { data } = await contratosService.criarAcessoDoInquilino(contrato.value.id)
    acessoCriado.value = data
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível criar o acesso do inquilino.')
  }
}

function fecharReajuste() {
  reajuste.value = null
  previa.value = null
}

async function calcularPrevia() {
  try {
    const { data } = await contratosService.previaReajuste(
      contrato.value.id,
      decimalParaApi(reajuste.value.percentual),
    )
    previa.value = data
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function aplicarReajuste() {
  try {
    await contratosService.aplicarReajuste(
      contrato.value.id,
      decimalParaApi(reajuste.value.percentual),
    )
    sucesso('Reajuste aplicado e registrado no histórico.')
    reajuste.value = null
    previa.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function confirmarRescisao() {
  try {
    const { data } = await contratosService.rescindir(
      contrato.value.id,
      rescisao.value.motivo,
      rescisao.value.data || undefined,
    )
    contrato.value = data
    rescisao.value = null
    sucesso(`Rescindido. Multa calculada: ${moeda(data.multa_rescisao_calculada)}.`)
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function criarVistoria(tipo) {
  try {
    const { data } = await vistoriasService.criar({ contrato: contrato.value.id, tipo })
    sucesso(`Vistoria de ${tipo.toLowerCase()} criada com checklist.`)
    window.location.assign(`/vistorias/${data.id}`)
  } catch (erro) {
    erroDaApi(erro)
  }
}

onMounted(carregar)
</script>

<template>
  <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando contrato…</p>

  <div v-else-if="contrato" class="space-y-6">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-slate-900">{{ contrato.numero }}</h1>
          <StatusBadge :status="contrato.status" :rotulo="contrato.status_display" />
        </div>
        <p class="mt-1 text-sm text-slate-500">
          {{ contrato.tipo_display }} · {{ contrato.imovel_codigo }}
          {{ contrato.imovel_titulo }}
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <a :href="contratosService.urlPdf(contrato.id)" target="_blank" rel="noopener">
          <BaseButton variante="secundaria">PDF</BaseButton>
        </a>
        <BaseButton v-if="ehRascunho" @click="ativar">Ativar contrato</BaseButton>
        <BaseButton
          v-if="ehAtivo && contrato.tipo === 'LOCACAO'"
          variante="secundaria"
          @click="reajuste = { percentual: '5' }"
        >
          Reajustar
        </BaseButton>
        <BaseButton v-if="ehAtivo" variante="secundaria" @click="criarAcesso">
          Acesso do inquilino
        </BaseButton>
        <BaseButton
          v-if="ehAtivo"
          variante="perigo"
          @click="rescisao = { motivo: '', data: '' }"
        >
          Rescindir
        </BaseButton>
      </div>
    </header>

    <div
      v-if="ehRascunho && contrato.pendencias_ativacao.length"
      class="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200"
    >
      <p class="font-semibold">Pendências para ativar</p>
      <ul class="mt-1 list-inside list-disc">
        <li v-for="pendencia in contrato.pendencias_ativacao" :key="pendencia">
          {{ pendencia }}
        </li>
      </ul>
    </div>

    <div class="grid gap-4 lg:grid-cols-3">
      <BaseCard titulo="Condições">
        <dl class="space-y-2 text-sm">
          <div class="flex justify-between">
            <dt class="text-slate-500">Valor</dt>
            <dd class="numerico font-semibold">{{ moeda(contrato.valor) }}</dd>
          </div>
          <div class="flex justify-between">
            <dt class="text-slate-500">Vigência</dt>
            <dd>
              {{ formatarData(contrato.data_inicio) }}
              {{ formatarData(contrato.data_fim) }}
            </dd>
          </div>
          <div v-if="contrato.tipo === 'LOCACAO'" class="flex justify-between">
            <dt class="text-slate-500">Vencimento</dt>
            <dd>Todo dia {{ contrato.dia_vencimento }}</dd>
          </div>
          <div v-if="contrato.tipo === 'LOCACAO'" class="flex justify-between">
            <dt class="text-slate-500">Taxa de adm.</dt>
            <dd class="numerico">{{ contrato.taxa_administracao_percent }}%</dd>
          </div>
          <div v-if="contrato.proximo_reajuste_em" class="flex justify-between">
            <dt class="text-slate-500">Próximo reajuste</dt>
            <dd>{{ formatarData(contrato.proximo_reajuste_em) }}</dd>
          </div>
          <div v-if="contrato.multa_rescisao_calculada" class="flex justify-between">
            <dt class="text-slate-500">Multa da rescisão</dt>
            <dd class="numerico text-red-600">
              {{ moeda(contrato.multa_rescisao_calculada) }}
            </dd>
          </div>
        </dl>
      </BaseCard>

      <BaseCard titulo="Partes">
        <ul class="space-y-2 text-sm">
          <li
            v-for="parte in contrato.partes"
            :key="parte.id"
            class="flex justify-between gap-3"
          >
            <span class="text-slate-500">{{ parte.papel_display }}</span>
            <span class="text-right">{{ parte.pessoa_detalhe.nome }}</span>
          </li>
          <li v-if="!contrato.partes.length" class="text-slate-400">
            Nenhuma parte cadastrada.
          </li>
        </ul>
      </BaseCard>

      <BaseCard v-if="auth.pode('ver_financeiro')" titulo="Comissões">
        <ul class="space-y-2 text-sm">
          <li
            v-for="comissao in contrato.comissoes"
            :key="comissao.id"
            class="flex items-center justify-between gap-2"
          >
            <span class="text-slate-500">{{ comissao.papel_display }}</span>
            <span class="numerico">{{ moeda(comissao.valor) }}</span>
            <StatusBadge :status="comissao.status" :rotulo="comissao.status_display" />
          </li>
          <li v-if="!contrato.comissoes.length" class="text-slate-400">
            Geradas na ativação do contrato.
          </li>
        </ul>
      </BaseCard>
    </div>

    <BaseCard v-if="contrato.reajustes.length" titulo="Reajustes aplicados">
      <ul class="space-y-2 text-sm">
        <li v-for="item in contrato.reajustes" :key="item.id" class="flex justify-between">
          <span>{{ formatarData(item.data_aplicacao) }} · {{ item.indice }}</span>
          <span class="numerico">
            {{ moeda(item.valor_anterior) }} → {{ moeda(item.valor_novo) }} ({{
              item.percentual
            }}%)
          </span>
        </li>
      </ul>
    </BaseCard>

    <BaseCard v-if="ehAtivo && contrato.tipo === 'LOCACAO'" titulo="Vistorias">
      <div class="flex flex-wrap gap-2">
        <BaseButton variante="secundaria" @click="criarVistoria('ENTRADA')">
          Vistoria de entrada
        </BaseButton>
        <BaseButton variante="secundaria" @click="criarVistoria('PERIODICA')">
          Vistoria periódica
        </BaseButton>
        <BaseButton variante="secundaria" @click="criarVistoria('SAIDA')">
          Vistoria de saída
        </BaseButton>
      </div>
    </BaseCard>

    <BaseModal v-if="reajuste" titulo="Reajuste anual" @fechar="fecharReajuste">
      <div class="space-y-4">
        <BaseInput v-model="reajuste.percentual" rotulo="Percentual do índice (%)" />
        <BaseButton variante="secundaria" @click="calcularPrevia">Calcular prévia</BaseButton>

        <dl v-if="previa" class="rounded-lg bg-slate-50 p-4 text-sm">
          <div class="flex justify-between">
            <dt>Valor atual</dt>
            <dd class="numerico">{{ moeda(previa.valor_anterior) }}</dd>
          </div>
          <div class="flex justify-between font-semibold">
            <dt>Novo valor</dt>
            <dd class="numerico">{{ moeda(previa.valor_novo) }}</dd>
          </div>
          <div class="flex justify-between text-slate-500">
            <dt>Diferença</dt>
            <dd class="numerico">{{ moeda(previa.diferenca) }}</dd>
          </div>
        </dl>
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="fecharReajuste"> Cancelar </BaseButton>
        <BaseButton :desabilitado="!previa" @click="aplicarReajuste">
          Aplicar reajuste
        </BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-if="rescisao" titulo="Rescindir contrato" @fechar="rescisao = null">
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          A multa é proporcional ao prazo restante e o imóvel volta para o mercado.
        </p>
        <BaseTextarea v-model="rescisao.motivo" rotulo="Motivo" :linhas="3" obrigatorio />
        <BaseInput v-model="rescisao.data" rotulo="Data da rescisão" tipo="date" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="rescisao = null">Cancelar</BaseButton>
        <BaseButton variante="perigo" @click="confirmarRescisao">Confirmar rescisão</BaseButton>
      </template>
    </BaseModal>

    <BaseModal v-if="acessoCriado" titulo="Acesso do inquilino" @fechar="acessoCriado = null">
      <div class="space-y-2 text-sm">
        <p class="text-slate-600">{{ acessoCriado.detail }}</p>
        <p><strong>E-mail:</strong> {{ acessoCriado.email }}</p>
        <p v-if="acessoCriado.senha_provisoria">
          <strong>Senha provisória:</strong>
          <span class="numerico">{{ acessoCriado.senha_provisoria }}</span>
        </p>
        <p class="rounded-lg bg-amber-50 p-3 text-xs text-amber-800">
          A senha aparece uma vez só. Entregue ao inquilino e peça que troque no primeiro
          acesso.
        </p>
      </div>
      <template #rodape>
        <BaseButton @click="acessoCriado = null">Fechar</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
