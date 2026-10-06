<script setup>
import { onMounted } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useListagem } from '@/composables/useListagem'
import { useToast } from '@/composables/useToast'
import { comissoesService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { moeda } from '@/utils/formatters'

const auth = useAuthStore()
const { sucesso, erroDaApi } = useToast()

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(comissoesService.listar, { filtrosIniciais: { status: '', papel: '' } })

const colunas = [
  { campo: 'contrato_numero', rotulo: 'Contrato' },
  { campo: 'usuario_nome', rotulo: 'Beneficiário' },
  { campo: 'papel_display', rotulo: 'Papel' },
  { campo: 'percentual_snapshot', rotulo: '%', alinhamento: 'direita' },
  { campo: 'valor', rotulo: 'Valor', alinhamento: 'direita' },
  { campo: 'status', rotulo: 'Status' },
  { campo: 'acoes', rotulo: '', alinhamento: 'direita' },
]

async function executar(acao, comissao) {
  try {
    await comissoesService[acao](comissao.id)
    sucesso(acao === 'liberar' ? 'Comissão liberada.' : 'Pagamento registrado.')
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
        <h1 class="text-2xl font-bold text-slate-900">Comissões</h1>
        <p class="text-sm text-slate-500">
          Percentual congelado no fechamento alterar a tabela não muda o passado
        </p>
      </div>
      <div class="flex gap-3">
        <div class="w-40">
          <BaseSelect
            v-model="filtros.status"
            rotulo="Status"
            :opcoes="['PREVISTA', 'LIBERADA', 'PAGA', 'CANCELADA']"
            placeholder="Todos"
          />
        </div>
        <div class="w-40">
          <BaseSelect
            v-model="filtros.papel"
            rotulo="Papel"
            :opcoes="['CAPTADOR', 'VENDEDOR', 'IMOBILIARIA']"
            placeholder="Todos"
          />
        </div>
      </div>
    </header>

    <DataEmptyState
      v-if="vazio"
      icone="%"
      titulo="Nenhuma comissão"
      descricao="Comissões são geradas quando o contrato é ativado."
    />

    <template v-else>
      <BaseTable :colunas="colunas" :linhas="itens" :carregando="carregando">
        <template #valor="{ linha }">{{ moeda(linha.valor) }}</template>
        <template #status="{ linha }">
          <StatusBadge :status="linha.status" :rotulo="linha.status_display" />
        </template>
        <template #acoes="{ linha }">
          <div v-if="auth.pode('ver_financeiro')" class="flex justify-end gap-2">
            <BaseButton
              v-if="linha.status === 'PREVISTA'"
              variante="secundaria"
              @click.stop="executar('liberar', linha)"
            >
              Liberar
            </BaseButton>
            <BaseButton
              v-if="linha.status === 'LIBERADA'"
              @click.stop="executar('pagar', linha)"
            >
              Pagar
            </BaseButton>
          </div>
        </template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>
  </div>
</template>
