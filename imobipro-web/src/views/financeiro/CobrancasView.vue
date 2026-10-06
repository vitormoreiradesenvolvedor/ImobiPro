<script setup>
import { onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useListagem } from '@/composables/useListagem'
import { useToast } from '@/composables/useToast'
import { cobrancasService } from '@/services/api'
import { data as formatarData, moeda } from '@/utils/formatters'

const { sucesso, erroDaApi } = useToast()

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(cobrancasService.listar, {
    filtrosIniciais: { status: '', competencia: '', em_atraso: '' },
  })

const inadimplencia = ref(null)
const baixa = ref(null)
const conciliando = ref(false)

const colunas = [
  { campo: 'contrato_numero', rotulo: 'Contrato' },
  { campo: 'inquilino', rotulo: 'Inquilino' },
  { campo: 'competencia', rotulo: 'Competência' },
  { campo: 'vencimento', rotulo: 'Vencimento' },
  { campo: 'status', rotulo: 'Status' },
  { campo: 'valor_total', rotulo: 'Valor', alinhamento: 'direita' },
  { campo: 'acoes', rotulo: '', alinhamento: 'direita' },
]

async function carregarIndicadores() {
  const { data } = await cobrancasService.inadimplencia()
  inadimplencia.value = data
}

function abrirBaixa(cobranca) {
  baixa.value = {
    id: cobranca.id,
    valor_pago: cobranca.valor_total,
    data: new Date().toISOString().slice(0, 10),
    forma: 'PIX',
  }
}

async function confirmarBaixa() {
  try {
    await cobrancasService.baixar(baixa.value.id, {
      valor_pago: baixa.value.valor_pago,
      data: baixa.value.data,
      forma: baixa.value.forma,
    })
    sucesso('Baixa registrada. Repasse gerado para o proprietário.')
    baixa.value = null
    await Promise.all([carregar(), carregarIndicadores()])
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível dar baixa.')
  }
}

async function conciliar(evento) {
  const arquivo = evento.target.files[0]
  if (!arquivo) return

  conciliando.value = true
  try {
    const { data } = await cobrancasService.conciliar(arquivo)
    sucesso(
      `${data.total_conciliado} cobrança(s) baixada(s). ` +
        `${data.nao_encontradas.length} linha(s) sem correspondência.`,
    )
    await Promise.all([carregar(), carregarIndicadores()])
  } catch (erro) {
    erroDaApi(erro, 'Falha ao processar o arquivo de retorno.')
  } finally {
    conciliando.value = false
    evento.target.value = ''
  }
}

onMounted(async () => {
  await Promise.all([carregar(), carregarIndicadores()])
})
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Contas a receber</h1>
        <p v-if="inadimplencia" class="text-sm text-slate-500" data-tour="inadimplencia">
          Inadimplência do mês: {{ inadimplencia.percentual }}% ({{
            inadimplencia.atrasadas
          }}
          de {{ inadimplencia.total_cobrancas }})
        </p>
      </div>

      <label
        data-tour="conciliar"
        class="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-marca px-4 py-2.5 text-sm font-semibold text-white hover:brightness-110"
      >
        {{ conciliando ? 'Processando…' : 'Conciliar retorno bancário' }}
        <input type="file" accept=".ret,.txt" class="sr-only" @change="conciliar" />
      </label>
    </header>

    <section class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-3">
      <BaseSelect
        v-model="filtros.status"
        rotulo="Status"
        :opcoes="['ABERTA', 'PAGA', 'ATRASADA', 'CANCELADA']"
        placeholder="Todos"
      />
      <BaseInput
        v-model="filtros.competencia"
        rotulo="Competência (AAAA-MM)"
        placeholder="2026-08"
      />
      <BaseSelect
        v-model="filtros.em_atraso"
        rotulo="Situação"
        :opcoes="[
          { value: 'true', label: 'Somente em atraso' },
          { value: 'false', label: 'Somente em dia' },
        ]"
        placeholder="Todas"
      />
    </section>

    <DataEmptyState
      v-if="vazio"
      icone="₿"
      titulo="Nenhuma cobrança encontrada"
      descricao="Cobranças são geradas automaticamente na ativação do contrato e todo mês, com 10 dias de antecedência."
    />

    <template v-else>
      <BaseTable :colunas="colunas" :linhas="itens" :carregando="carregando">
        <template #competencia="{ linha }">{{ formatarData(linha.competencia) }}</template>
        <template #vencimento="{ linha }">
          {{ formatarData(linha.vencimento) }}
          <span v-if="linha.dias_de_atraso" class="ml-1 text-xs text-red-600">
            ({{ linha.dias_de_atraso }}d)
          </span>
        </template>
        <template #status="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #valor_total="{ linha }">{{ moeda(linha.valor_total) }}</template>
        <template #acoes="{ linha }">
          <BaseButton
            v-if="linha.status !== 'PAGA' && linha.status !== 'CANCELADA'"
            variante="secundaria"
            @click.stop="abrirBaixa(linha)"
          >
            Dar baixa
          </BaseButton>
        </template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>

    <BaseModal v-if="baixa" titulo="Registrar recebimento" @fechar="baixa = null">
      <div class="space-y-4">
        <MoneyInput v-model="baixa.valor_pago" rotulo="Valor recebido" />
        <BaseInput v-model="baixa.data" rotulo="Data do pagamento" tipo="date" />
        <BaseSelect
          v-model="baixa.forma"
          rotulo="Forma"
          :opcoes="['PIX', 'BOLETO', 'TRANSFERENCIA', 'DINHEIRO', 'CARTAO']"
        />
        <p class="text-xs text-slate-500">
          Multa e juros por atraso são calculados pelo sistema no momento da baixa.
        </p>
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="baixa = null">Cancelar</BaseButton>
        <BaseButton @click="confirmarBaixa">Confirmar baixa</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
