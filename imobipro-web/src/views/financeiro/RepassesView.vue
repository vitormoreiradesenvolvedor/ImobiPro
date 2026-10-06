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
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'
import { repassesService } from '@/services/api'
import { data as formatarData, moeda } from '@/utils/formatters'

const { sucesso, erroDaApi } = useToast()
const { confirmar } = useConfirmacao()

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(repassesService.listar, { filtrosIniciais: { status: '' } })

const retencao = ref(null)

const colunas = [
  { campo: 'contrato_numero', rotulo: 'Contrato' },
  { campo: 'proprietario', rotulo: 'Proprietário' },
  { campo: 'competencia', rotulo: 'Competência' },
  { campo: 'valor_bruto', rotulo: 'Aluguel', alinhamento: 'direita' },
  { campo: 'taxa_administracao', rotulo: 'Taxa', alinhamento: 'direita' },
  { campo: 'valor_liquido', rotulo: 'Líquido', alinhamento: 'direita' },
  { campo: 'status', rotulo: 'Status' },
  { campo: 'acoes', rotulo: '', alinhamento: 'direita' },
]

async function liquidar(repasse) {
  const confirmado = await confirmar({
    titulo: 'Liquidar repasse',
    mensagem: `Confirma o pagamento de ${moeda(repasse.valor_liquido)} ao proprietário?`,
    confirmar: 'Liquidar',
  })
  if (!confirmado) return
  try {
    await repassesService.liquidar(repasse.id)
    sucesso('Repasse liquidado e lançado no financeiro.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível liquidar o repasse.')
  }
}

async function salvarRetencao() {
  try {
    await repassesService.adicionarRetencao(retencao.value.id, {
      descricao: retencao.value.descricao,
      valor: retencao.value.valor,
    })
    sucesso('Retenção aplicada ao repasse.')
    retencao.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Repasses aos proprietários</h1>
        <p class="text-sm text-slate-500">
          Aluguel recebido menos taxa de administração e retenções
        </p>
      </div>
      <div class="w-48">
        <BaseSelect
          v-model="filtros.status"
          rotulo="Status"
          :opcoes="['PENDENTE', 'PAGO', 'CANCELADO']"
          placeholder="Todos"
        />
      </div>
    </header>

    <DataEmptyState
      v-if="vazio"
      icone="↗"
      titulo="Nenhum repasse ainda"
      descricao="O repasse nasce automaticamente quando a cobrança do inquilino recebe baixa."
    />

    <template v-else>
      <BaseTable :colunas="colunas" :linhas="itens" :carregando="carregando">
        data-tour="tabela-repasses"
        <template #competencia="{ linha }">{{ formatarData(linha.competencia) }}</template>
        <template #valor_bruto="{ linha }">{{ moeda(linha.valor_bruto) }}</template>
        <template #taxa_administracao="{ linha }">
          − {{ moeda(linha.taxa_administracao) }}
        </template>
        <template #valor_liquido="{ linha }">
          <strong>{{ moeda(linha.valor_liquido) }}</strong>
        </template>
        <template #status="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #acoes="{ linha }">
          <div class="flex justify-end gap-2">
            <a :href="repassesService.urlExtrato(linha.id)" target="_blank" rel="noopener">
              <BaseButton variante="fantasma">Extrato</BaseButton>
            </a>
            <template v-if="linha.status === 'PENDENTE'">
              <BaseButton
                variante="secundaria"
                @click.stop="retencao = { id: linha.id, descricao: '', valor: '' }"
              >
                Reter
              </BaseButton>
              <BaseButton @click.stop="liquidar(linha)">Liquidar</BaseButton>
            </template>
          </div>
        </template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>

    <BaseModal v-if="retencao" titulo="Reter do repasse" @fechar="retencao = null">
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          Manutenção paga pela imobiliária sai do valor devido ao proprietário.
        </p>
        <BaseInput v-model="retencao.descricao" rotulo="Descrição" obrigatorio />
        <MoneyInput v-model="retencao.valor" rotulo="Valor" />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="retencao = null">Cancelar</BaseButton>
        <BaseButton @click="salvarRetencao">Aplicar retenção</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
