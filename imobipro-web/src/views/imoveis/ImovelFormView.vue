<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTextarea from '@/components/base/BaseTextarea.vue'
import MoneyInput from '@/components/base/MoneyInput.vue'
import { useToast } from '@/composables/useToast'
import { imoveisService, pessoasService } from '@/services/api'

const route = useRoute()
const router = useRouter()
const { sucesso, erroDaApi, erro: avisarErro } = useToast()

const PASSOS = ['Identificação', 'Endereço', 'Características', 'Valores', 'Documentação']

const passo = ref(0)
const salvando = ref(false)
const proprietarios = ref([])
const caracteristicas = ref([])
const edicao = computed(() => Boolean(route.params.id))

/**
 * Volta um passo do assistente e, no primeiro passo, sai da captação.
 *
 * Botão que não faz nada é pior do que botão ausente: no primeiro passo ele
 * ficava desabilitado e quem queria desistir do cadastro não tinha saída.
 */
function voltar() {
  if (passo.value > 0) {
    passo.value -= 1
    return
  }
  router.push({ name: 'imoveis' })
}

const formulario = ref({
  titulo: '',
  descricao: '',
  tipo: 'APARTAMENTO',
  finalidade: 'LOCACAO',
  proprietario: '',
  quartos: 0,
  suites: 0,
  banheiros: 0,
  vagas: 0,
  area_total: '',
  area_util: '',
  ano_construcao: '',
  mobiliado: false,
  aceita_pet: false,
  valor_venda: '',
  valor_locacao: '',
  valor_condominio: '',
  valor_iptu_anual: '',
  parcelas_iptu: 10,
  matricula: '',
  inscricao_municipal: '',
  exclusividade_ate: '',
  autorizacao_assinada: false,
  caracteristicas: [],
  endereco: {
    cep: '',
    logradouro: '',
    numero: '',
    complemento: '',
    bairro: '',
    cidade: '',
    uf: 'MG',
    latitude: '',
    longitude: '',
  },
})

const vende = computed(() => ['VENDA', 'VENDA_E_LOCACAO'].includes(formulario.value.finalidade))
const aluga = computed(() =>
  ['LOCACAO', 'VENDA_E_LOCACAO', 'TEMPORADA'].includes(formulario.value.finalidade),
)

async function buscarCep() {
  const cep = formulario.value.endereco.cep
  if (!cep || cep.replace(/\D/g, '').length !== 8) return

  try {
    const { data } = await pessoasService.consultarCep(cep)
    Object.assign(formulario.value.endereco, {
      logradouro: data.logradouro || formulario.value.endereco.logradouro,
      bairro: data.bairro || formulario.value.endereco.bairro,
      cidade: data.cidade,
      uf: data.uf,
    })
    sucesso('Endereço preenchido pelo CEP.')
  } catch {
    avisarErro('CEP não encontrado. Preencha o endereço manualmente.')
  }
}

function limpar(objeto) {
  return Object.fromEntries(
    Object.entries(objeto).filter(([, valor]) => valor !== '' && valor !== null),
  )
}

async function salvar() {
  salvando.value = true
  try {
    const carga = {
      ...limpar(formulario.value),
      endereco: limpar(formulario.value.endereco),
      caracteristicas: formulario.value.caracteristicas,
    }

    const { data } = edicao.value
      ? await imoveisService.atualizar(route.params.id, carga)
      : await imoveisService.criar(carga)

    sucesso(`Imóvel ${data.codigo} salvo.`)
    router.push({ name: 'imovel-detalhe', params: { id: data.id } })
  } catch (falha) {
    erroDaApi(falha, 'Não foi possível salvar o imóvel.')
  } finally {
    salvando.value = false
  }
}

onMounted(async () => {
  const [listaPessoas, listaCaracteristicas] = await Promise.all([
    pessoasService.listar({ page_size: 100 }),
    imoveisService.caracteristicas(),
  ])
  proprietarios.value = (listaPessoas.data.results ?? listaPessoas.data).map((pessoa) => ({
    value: pessoa.id,
    label: `${pessoa.nome} ${pessoa.cpf_cnpj}`,
  }))
  caracteristicas.value = listaCaracteristicas.data

  if (edicao.value) {
    const { data } = await imoveisService.obter(route.params.id)
    Object.assign(formulario.value, {
      ...data,
      proprietario: data.proprietario,
      caracteristicas: data.caracteristicas ?? [],
      endereco: { ...formulario.value.endereco, ...data.endereco },
    })
  }
})
</script>

<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">
        {{ edicao ? 'Editar imóvel' : 'Captar imóvel' }}
      </h1>
      <p class="text-sm text-slate-500">
        Passo {{ passo + 1 }} de {{ PASSOS.length }} {{ PASSOS[passo] }}
      </p>
    </header>

    <ol class="flex gap-1" data-tour="progresso-wizard" aria-label="Progresso do cadastro">
      <li
        v-for="(nome, indice) in PASSOS"
        :key="nome"
        class="h-1.5 flex-1 rounded-full"
        :class="indice <= passo ? 'bg-marca' : 'bg-slate-200'"
        :aria-current="indice === passo ? 'step' : undefined"
      />
    </ol>

    <form
      class="space-y-5 rounded-xl bg-white p-6 ring-1 ring-slate-200"
      @submit.prevent="salvar"
    >
      <template v-if="passo === 0">
        <BaseInput v-model="formulario.titulo" rotulo="Título do anúncio" obrigatorio />
        <BaseTextarea v-model="formulario.descricao" rotulo="Descrição" :linhas="5" />
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseSelect
            v-model="formulario.tipo"
            rotulo="Tipo"
            :opcoes="[
              'APARTAMENTO',
              'CASA',
              'CASA_CONDOMINIO',
              'COBERTURA',
              'KITNET',
              'TERRENO',
              'SALA_COMERCIAL',
              'GALPAO',
              'RURAL',
            ]"
            obrigatorio
          />
          <BaseSelect
            v-model="formulario.finalidade"
            rotulo="Finalidade"
            :opcoes="['VENDA', 'LOCACAO', 'VENDA_E_LOCACAO', 'TEMPORADA']"
            obrigatorio
          />
        </div>
        <BaseSelect
          v-model="formulario.proprietario"
          rotulo="Proprietário"
          :opcoes="proprietarios"
          placeholder="Selecione o proprietário"
          obrigatorio
        />
      </template>

      <template v-else-if="passo === 1">
        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.endereco.cep" rotulo="CEP" @blur="buscarCep" />
          <div class="sm:col-span-2">
            <BaseInput
              v-model="formulario.endereco.logradouro"
              rotulo="Logradouro"
              obrigatorio
            />
          </div>
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.endereco.numero" rotulo="Número" />
          <BaseInput v-model="formulario.endereco.complemento" rotulo="Complemento" />
          <BaseInput v-model="formulario.endereco.bairro" rotulo="Bairro" />
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.endereco.cidade" rotulo="Cidade" obrigatorio />
          <BaseInput v-model="formulario.endereco.uf" rotulo="UF" obrigatorio />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseInput v-model="formulario.endereco.latitude" rotulo="Latitude" />
          <BaseInput v-model="formulario.endereco.longitude" rotulo="Longitude" />
        </div>
        <p class="text-xs text-slate-500">
          Latitude e longitude são obrigatórias para publicar o imóvel no site e no mapa.
        </p>
      </template>

      <template v-else-if="passo === 2">
        <div class="grid gap-4 sm:grid-cols-4">
          <BaseInput v-model="formulario.quartos" rotulo="Quartos" tipo="number" />
          <BaseInput v-model="formulario.suites" rotulo="Suítes" tipo="number" />
          <BaseInput v-model="formulario.banheiros" rotulo="Banheiros" tipo="number" />
          <BaseInput v-model="formulario.vagas" rotulo="Vagas" tipo="number" />
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.area_total" rotulo="Área total (m²)" />
          <BaseInput v-model="formulario.area_util" rotulo="Área útil (m²)" />
          <BaseInput
            v-model="formulario.ano_construcao"
            rotulo="Ano de construção"
            tipo="number"
          />
        </div>
        <div class="flex flex-wrap gap-6">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="formulario.mobiliado" type="checkbox" class="size-4 rounded" />
            Mobiliado
          </label>
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="formulario.aceita_pet" type="checkbox" class="size-4 rounded" />
            Aceita pet
          </label>
        </div>
        <fieldset>
          <legend class="mb-2 text-sm font-medium text-slate-700">Características</legend>
          <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
            <label
              v-for="item in caracteristicas"
              :key="item.id"
              class="flex items-center gap-2 text-sm text-slate-600"
            >
              <input
                v-model="formulario.caracteristicas"
                type="checkbox"
                :value="item.id"
                class="size-4 rounded"
              />
              {{ item.nome }}
            </label>
          </div>
        </fieldset>
      </template>

      <template v-else-if="passo === 3">
        <div class="grid gap-4 sm:grid-cols-2">
          <MoneyInput v-if="vende" v-model="formulario.valor_venda" rotulo="Valor de venda" />
          <MoneyInput
            v-if="aluga"
            v-model="formulario.valor_locacao"
            rotulo="Valor de locação"
          />
          <MoneyInput v-model="formulario.valor_condominio" rotulo="Condomínio mensal" />
          <MoneyInput v-model="formulario.valor_iptu_anual" rotulo="IPTU anual" />
          <BaseInput
            v-model="formulario.parcelas_iptu"
            rotulo="Parcelas do IPTU"
            tipo="number"
          />
        </div>
      </template>

      <template v-else>
        <BaseInput v-model="formulario.matricula" rotulo="Matrícula" />
        <BaseInput v-model="formulario.inscricao_municipal" rotulo="Inscrição municipal" />
        <BaseInput
          v-model="formulario.exclusividade_ate"
          rotulo="Exclusividade até"
          tipo="date"
        />
        <label class="flex items-center gap-2 text-sm text-slate-700">
          <input
            v-model="formulario.autorizacao_assinada"
            type="checkbox"
            class="size-4 rounded"
          />
          Autorização de venda assinada
        </label>
        <p class="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          Após salvar, envie ao menos 5 fotos na ficha do imóvel para liberar a publicação.
        </p>
      </template>

      <footer class="flex justify-between gap-3 border-t border-slate-200 pt-4">
        <BaseButton variante="secundaria" @click="voltar">Voltar</BaseButton>

        <BaseButton v-if="passo < PASSOS.length - 1" @click="passo += 1">Continuar</BaseButton>
        <BaseButton v-else tipo="submit" :carregando="salvando">Salvar imóvel</BaseButton>
      </footer>
    </form>
  </div>
</template>
