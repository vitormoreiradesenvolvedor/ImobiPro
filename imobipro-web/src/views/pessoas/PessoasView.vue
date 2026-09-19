<script setup>
import { onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import DataEmptyState from '@/components/base/DataEmptyState.vue'
import PaginacaoSimples from '@/components/base/PaginacaoSimples.vue'
import { useListagem } from '@/composables/useListagem'
import { useToast } from '@/composables/useToast'
import { pessoasService } from '@/services/api'
import { cpfCnpj, telefone as formatarTelefone } from '@/utils/formatters'

const { sucesso, erroDaApi, erro: avisar } = useToast()

const ENDERECO_VAZIO = {
  cep: '',
  logradouro: '',
  numero: '',
  bairro: '',
  cidade: '',
  uf: 'MG',
}

const { itens, total, pagina, totalPaginas, carregando, filtros, vazio, carregar } =
  useListagem(pessoasService.listar, { filtrosIniciais: { search: '', tipo: '' } })

const formulario = ref(null)
// Arquivo escolhido antes de existir id: sobe depois que o cadastro é criado.
const fotoEscolhida = ref(null)
const previaDaFoto = ref('')

const colunas = [
  { campo: 'nome', rotulo: 'Nome' },
  { campo: 'cpf_cnpj', rotulo: 'CPF/CNPJ' },
  { campo: 'tipo_display', rotulo: 'Tipo' },
  { campo: 'telefone', rotulo: 'Telefone' },
  { campo: 'email', rotulo: 'E-mail' },
]

function escolherFoto(evento) {
  const arquivo = evento.target.files?.[0]
  if (!arquivo) return
  fotoEscolhida.value = arquivo
  previaDaFoto.value = URL.createObjectURL(arquivo)
}

async function tirarFoto() {
  fotoEscolhida.value = null
  previaDaFoto.value = ''
  if (!formulario.value?.id || !formulario.value.foto) return
  try {
    await pessoasService.removerFoto(formulario.value.id)
    formulario.value.foto = null
    sucesso('Foto removida.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível remover a foto.')
  }
}

function abrir(pessoa = null) {
  fotoEscolhida.value = null
  previaDaFoto.value = ''
  formulario.value = pessoa
    ? { ...pessoa, endereco: { ...ENDERECO_VAZIO, ...pessoa.endereco } }
    : {
        tipo: 'FISICA',
        nome: '',
        cpf_cnpj: '',
        email: '',
        telefone: '',
        whatsapp: '',
        endereco: { ...ENDERECO_VAZIO },
      }
}

async function buscarCep() {
  const cep = formulario.value.endereco.cep
  if (!cep || cep.replace(/\D/g, '').length !== 8) return
  try {
    const { data } = await pessoasService.consultarCep(cep)
    Object.assign(formulario.value.endereco, {
      logradouro: data.logradouro,
      bairro: data.bairro,
      cidade: data.cidade,
      uf: data.uf,
    })
  } catch {
    avisar('CEP não encontrado.')
  }
}

/** Endereço é opcional no cadastro: só vai para a API se tiver conteúdo. */
function comEnderecoOpcional(dados) {
  const endereco = dados.endereco ?? {}
  const preenchido = Object.values(endereco).some(
    (valor) => valor && String(valor).trim() && valor !== 'MG',
  )
  if (preenchido) return dados

  return Object.fromEntries(Object.entries(dados).filter(([campo]) => campo !== 'endereco'))
}

async function salvar() {
  try {
    let salvo
    if (formulario.value.id) {
      salvo = await pessoasService.atualizar(
        formulario.value.id,
        comEnderecoOpcional(formulario.value),
      )
    } else {
      salvo = await pessoasService.criar(comEnderecoOpcional(formulario.value))
    }
    // A foto é opcional e vai em requisição própria: o cadastro já está salvo,
    // então falha no upload avisa sem desfazer o que o usuário digitou.
    if (fotoEscolhida.value) {
      try {
        await pessoasService.enviarFoto(salvo.data.id, fotoEscolhida.value)
      } catch (erro) {
        erroDaApi(erro, 'Cadastro salvo, mas a foto não subiu. Tente enviar de novo.')
      }
    }
    sucesso('Cadastro salvo.')
    formulario.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível salvar o cadastro.')
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Pessoas</h1>
        <p class="text-sm text-slate-500">
          Proprietários, inquilinos, compradores e fiadores {{ total }} cadastros
        </p>
      </div>
      <BaseButton data-tour="nova-pessoa" @click="abrir()">Nova pessoa</BaseButton>
    </header>

    <section class="grid gap-3 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-2">
      <BaseInput
        v-model="filtros.search"
        rotulo="Buscar"
        placeholder="nome, documento, telefone"
      />
      <BaseSelect
        v-model="filtros.tipo"
        rotulo="Tipo"
        :opcoes="[
          { value: 'FISICA', label: 'Pessoa física' },
          { value: 'JURIDICA', label: 'Pessoa jurídica' },
        ]"
        placeholder="Todos"
      />
    </section>

    <DataEmptyState
      v-if="vazio"
      icone="☺"
      titulo="Nenhuma pessoa cadastrada"
      descricao="O proprietário precisa existir antes de captar o imóvel."
    >
      <template #acao><BaseButton @click="abrir()">Nova pessoa</BaseButton></template>
    </DataEmptyState>

    <template v-else>
      <BaseTable
        :colunas="colunas"
        :linhas="itens"
        :carregando="carregando"
        @selecionar="abrir"
      >
        <template #cpf_cnpj="{ linha }">{{ cpfCnpj(linha.cpf_cnpj) }}</template>
        <template #telefone="{ linha }">{{ formatarTelefone(linha.telefone) }}</template>
      </BaseTable>

      <PaginacaoSimples v-model:pagina="pagina" :total-paginas="totalPaginas" :total="total" />
    </template>

    <BaseModal
      v-if="formulario"
      :titulo="formulario.id ? 'Editar pessoa' : 'Nova pessoa'"
      largura="max-w-2xl"
      @fechar="formulario = null"
    >
      <form class="space-y-4" @submit.prevent="salvar">
        <div class="grid gap-4 sm:grid-cols-2">
          <BaseSelect
            v-model="formulario.tipo"
            rotulo="Tipo"
            :opcoes="[
              { value: 'FISICA', label: 'Pessoa física' },
              { value: 'JURIDICA', label: 'Pessoa jurídica' },
            ]"
          />
          <BaseInput v-model="formulario.cpf_cnpj" rotulo="CPF/CNPJ" obrigatorio />
        </div>

        <BaseInput v-model="formulario.nome" rotulo="Nome / Razão social" obrigatorio />

        <div class="flex items-center gap-4">
          <img
            v-if="previaDaFoto || formulario.foto"
            :src="previaDaFoto || formulario.foto"
            alt=""
            class="size-16 rounded-full object-cover ring-1 ring-slate-200"
          />
          <span
            v-else
            aria-hidden="true"
            class="grid size-16 place-items-center rounded-full bg-marca-suave text-lg font-semibold text-marca-escura"
          >
            {{ formulario.nome ? formulario.nome.trim()[0].toUpperCase() : '?' }}
          </span>

          <div class="space-y-1">
            <label
              class="inline-block cursor-pointer rounded-lg bg-marca-suave px-3 py-1.5 text-sm font-medium text-marca-escura hover:brightness-95"
            >
              {{ previaDaFoto || formulario.foto ? 'Trocar foto' : 'Adicionar foto' }}
              <input type="file" accept="image/*" class="sr-only" @change="escolherFoto" />
            </label>
            <button
              v-if="previaDaFoto || formulario.foto"
              type="button"
              class="ml-2 text-sm text-slate-500 underline hover:text-slate-700"
              @click="tirarFoto"
            >
              remover
            </button>
            <p class="text-xs text-slate-500">Opcional. Ajuda a reconhecer quem chega.</p>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <BaseInput v-model="formulario.email" rotulo="E-mail" tipo="email" />
          <BaseInput v-model="formulario.telefone" rotulo="Telefone" />
          <BaseInput v-model="formulario.whatsapp" rotulo="WhatsApp" />
        </div>

        <fieldset class="space-y-4 rounded-lg bg-slate-50 p-4">
          <legend class="px-1 text-sm font-medium text-slate-700">Endereço</legend>
          <div class="grid gap-4 sm:grid-cols-3">
            <BaseInput v-model="formulario.endereco.cep" rotulo="CEP" @blur="buscarCep" />
            <div class="sm:col-span-2">
              <BaseInput v-model="formulario.endereco.logradouro" rotulo="Logradouro" />
            </div>
          </div>
          <div class="grid gap-4 sm:grid-cols-4">
            <BaseInput v-model="formulario.endereco.numero" rotulo="Número" />
            <BaseInput v-model="formulario.endereco.bairro" rotulo="Bairro" />
            <BaseInput v-model="formulario.endereco.cidade" rotulo="Cidade" />
            <BaseInput v-model="formulario.endereco.uf" rotulo="UF" />
          </div>
        </fieldset>
      </form>

      <template #rodape>
        <BaseButton variante="secundaria" @click="formulario = null">Cancelar</BaseButton>
        <BaseButton @click="salvar">Salvar</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
