<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import { useToast } from '@/composables/useToast'
import { decimalParaApi } from '@/utils/formatters'
import { contratosService, imoveisService, pessoasService } from '@/services/api'

const router = useRouter()
const { sucesso, erroDaApi } = useToast()

const salvando = ref(false)
const imoveis = ref([])
const pessoas = ref([])

const formulario = ref({
  tipo: 'LOCACAO',
  imovel: '',
  data_inicio: new Date().toISOString().slice(0, 10),
  data_fim: '',
  valor: '',
  dia_vencimento: 10,
  indice_reajuste: 'IGPM',
  taxa_administracao_percent: '8',
  taxa_intermediacao: '',
  garantia_tipo: 'FIADOR',
  garantia_valor: '',
  multa_rescisoria_meses: 3,
  inclui_condominio: true,
  inclui_iptu: true,
  observacoes: '',
})

const partes = ref([])
const ehLocacao = computed(() => formulario.value.tipo === 'LOCACAO')

const papeisDisponiveis = computed(() =>
  ehLocacao.value ? ['LOCADOR', 'LOCATARIO', 'FIADOR'] : ['VENDEDOR', 'COMPRADOR'],
)

function adicionarParte() {
  partes.value.push({ pessoa: '', papel: papeisDisponiveis.value[0], percentual: 100 })
}

async function salvar() {
  salvando.value = true
  try {
    const carga = Object.fromEntries(
      Object.entries(formulario.value)
        .filter(([, valor]) => valor !== '')
        // Percentuais são texto livre: "10,5" precisa virar "10.5" para a API.
        .map(([campo, valor]) =>
          campo.includes('percent') ? [campo, decimalParaApi(valor)] : [campo, valor],
        ),
    )
    const { data } = await contratosService.criar(carga)

    for (const parte of partes.value.filter((item) => item.pessoa)) {
      await contratosService.adicionarParte(data.id, parte)
    }

    sucesso(`Contrato ${data.numero} criado como rascunho.`)
    router.push({ name: 'contrato-detalhe', params: { id: data.id } })
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível criar o contrato.')
  } finally {
    salvando.value = false
  }
}

onMounted(async () => {
  const [listaImoveis, listaPessoas] = await Promise.all([
    imoveisService.listar({ page_size: 100 }),
    pessoasService.listar({ page_size: 100 }),
  ])

  imoveis.value = (listaImoveis.data.results ?? listaImoveis.data).map((imovel) => ({
    value: imovel.id,
    label: `${imovel.codigo} ${imovel.titulo} (${imovel.situacao_display})`,
  }))
  pessoas.value = (listaPessoas.data.results ?? listaPessoas.data).map((pessoa) => ({
    value: pessoa.id,
    label: `${pessoa.nome} ${pessoa.cpf_cnpj}`,
  }))

  adicionarParte()
})
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">Novo contrato</h1>
      <p class="text-sm text-slate-500">
        O contrato nasce como rascunho; a ativação é que tira o imóvel do mercado.
      </p>
    </header>

    <form class="space-y-6" @submit.prevent="salvar">
      <section class="space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 class="text-sm font-semibold text-slate-900">Dados principais</h2>

        <div class="grid gap-4 sm:grid-cols-2">
          <BaseSelect
            v-model="formulario.tipo"
            rotulo="Tipo"
            :opcoes="['LOCACAO', 'VENDA']"
            obrigatorio
          />
          <BaseSelect
            v-model="formulario.imovel"
            rotulo="Imóvel"
            :opcoes="imoveis"
            placeholder="Selecione o imóvel"
            obrigatorio
          />
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.data_inicio" rotulo="Início" tipo="date" obrigatorio />
          <BaseInput
            v-model="formulario.data_fim"
            rotulo="Término"
            tipo="date"
            :obrigatorio="ehLocacao"
          />
          <MoneyInput v-model="formulario.valor" rotulo="Valor" obrigatorio />
        </div>
      </section>

      <section v-if="ehLocacao" class="space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 class="text-sm font-semibold text-slate-900">Condições da locação</h2>

        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput
            v-model="formulario.dia_vencimento"
            rotulo="Dia de vencimento"
            tipo="number"
          />
          <BaseSelect
            v-model="formulario.indice_reajuste"
            rotulo="Índice de reajuste"
            :opcoes="['IGPM', 'IPCA', 'INPC', 'SEM_REAJUSTE']"
          />
          <BaseInput
            v-model="formulario.taxa_administracao_percent"
            rotulo="Taxa de administração (%)"
          />
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <BaseSelect
            v-model="formulario.garantia_tipo"
            rotulo="Garantia"
            :opcoes="[
              'FIADOR',
              'CAUCAO',
              'SEGURO_FIANCA',
              'TITULO_CAPITALIZACAO',
              'SEM_GARANTIA',
            ]"
          />
          <MoneyInput v-model="formulario.garantia_valor" rotulo="Valor da garantia" />
          <BaseInput
            v-model="formulario.multa_rescisoria_meses"
            rotulo="Multa (aluguéis)"
            tipo="number"
          />
        </div>

        <div class="flex flex-wrap gap-6">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input
              v-model="formulario.inclui_condominio"
              type="checkbox"
              class="size-4 rounded"
            />
            Cobrar condomínio junto
          </label>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="formulario.inclui_iptu" type="checkbox" class="size-4 rounded" />
            Cobrar IPTU junto
          </label>
        </div>
      </section>

      <section class="space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-slate-900">Partes</h2>
          <BaseButton variante="secundaria" @click="adicionarParte">Adicionar parte</BaseButton>
        </div>

        <div
          v-for="(parte, indice) in partes"
          :key="indice"
          class="grid gap-3 sm:grid-cols-[2fr_1fr_auto]"
        >
          <BaseSelect
            v-model="parte.pessoa"
            :opcoes="pessoas"
            rotulo="Pessoa"
            placeholder="Selecione"
          />
          <BaseSelect v-model="parte.papel" :opcoes="papeisDisponiveis" rotulo="Papel" />
          <button
            type="button"
            class="mt-7 h-10 rounded-lg px-3 text-sm text-red-600 hover:bg-red-50"
            @click="partes.splice(indice, 1)"
          >
            remover
          </button>
        </div>

        <p class="text-xs text-slate-500">
          Locação exige locador e locatário; venda exige vendedor e comprador.
        </p>
      </section>

      <section class="rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <BaseTextarea v-model="formulario.observacoes" rotulo="Observações" />
      </section>

      <div class="flex justify-end gap-3">
        <BaseButton variante="secundaria" @click="router.back()">Cancelar</BaseButton>
        <BaseButton tipo="submit" :carregando="salvando">Criar rascunho</BaseButton>
      </div>
    </form>
  </div>
</template>
