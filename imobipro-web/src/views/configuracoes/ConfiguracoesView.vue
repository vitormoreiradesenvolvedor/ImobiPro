<script setup>
import { computed, onMounted, ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import BaseModal from '@/components/base/BaseModal.vue'
import BaseSelect from '@/components/base/BaseSelect.vue'
import BaseTable from '@/components/base/BaseTable.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'
import { decimalParaApi } from '@/utils/formatters'
import { comissoesService, integracoesService, usuariosService } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { sucesso, erroDaApi } = useToast()
const { confirmar } = useConfirmacao()

const ABAS = [
  { chave: 'equipe', rotulo: 'Equipe' },
  { chave: 'comissao', rotulo: 'Tabela de comissão' },
  { chave: 'integracoes', rotulo: 'Integrações' },
]

const aba = ref('equipe')
const usuarios = ref([])
const comissao = ref(null)
const integracoes = ref([])
const eventos = ref([])
const novoUsuario = ref(null)

const somaRateio = computed(() =>
  comissao.value
    ? Number(comissao.value.rateio_captador) +
      Number(comissao.value.rateio_vendedor) +
      Number(comissao.value.rateio_imobiliaria)
    : 0,
)

const colunasUsuarios = [
  { campo: 'nome_completo', rotulo: 'Nome' },
  { campo: 'email', rotulo: 'E-mail' },
  { campo: 'papel_display', rotulo: 'Papel' },
  { campo: 'ativo', rotulo: 'Ativo' },
]

async function carregar() {
  const [equipe, tabela, portais, fila] = await Promise.all([
    usuariosService.listar({ page_size: 50 }),
    comissoesService.configuracao(),
    integracoesService.listar(),
    integracoesService.eventos({ page_size: 10 }),
  ])
  usuarios.value = equipe.data.results ?? equipe.data
  comissao.value = tabela.data
  integracoes.value = portais.data.results ?? portais.data
  eventos.value = fila.data.results ?? fila.data
}

async function salvarComissao() {
  try {
    // Percentuais digitados em pt-BR ("2,5") não são aceitos com vírgula.
    await comissoesService.salvarConfiguracao(
      Object.fromEntries(
        Object.entries(comissao.value).map(([campo, valor]) => [campo, decimalParaApi(valor)]),
      ),
    )
    sucesso('Tabela de comissão atualizada.')
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function salvarUsuario() {
  try {
    await usuariosService.criar(novoUsuario.value)
    sucesso('Usuário criado.')
    novoUsuario.value = null
    await carregar()
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível criar o usuário.')
  }
}

async function sincronizar(integracao) {
  try {
    const { data } = await integracoesService.sincronizar(integracao.id)
    sucesso(`${data.enfileirados} imóvel(is) enfileirado(s) para o portal.`)
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function rotacionar(integracao) {
  const confirmado = await confirmar({
    titulo: 'Rotacionar segredo',
    mensagem: 'O segredo atual deixa de funcionar imediatamente para este portal.',
    confirmar: 'Gerar novo segredo',
    perigo: true,
  })
  if (!confirmado) return
  try {
    await integracoesService.rotacionarSegredo(integracao.id)
    sucesso('Segredo rotacionado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function reprocessar(evento) {
  try {
    await integracoesService.reprocessar(evento.id)
    sucesso('Evento reenfileirado.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

onMounted(carregar)
</script>

<template>
  <div class="space-y-5">
    <header>
      <h1 class="text-2xl font-bold text-slate-900">Configurações</h1>
      <p class="text-sm text-slate-500">{{ auth.tenant?.razao_social }}</p>
    </header>

    <nav class="flex gap-1 border-b border-slate-200" aria-label="Seções de configuração">
      <button
        v-for="item in ABAS"
        :key="item.chave"
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium transition"
        :class="
          aba === item.chave
            ? 'border-marca text-marca'
            : 'border-transparent text-slate-500 hover:text-slate-700'
        "
        :aria-current="aba === item.chave ? 'page' : undefined"
        @click="aba = item.chave"
      >
        {{ item.rotulo }}
      </button>
    </nav>

    <section v-if="aba === 'equipe'" class="space-y-4">
      <div class="flex justify-end">
        <BaseButton
          @click="
            novoUsuario = {
              nome_completo: '',
              email: '',
              papel: 'CORRETOR',
              senha: '',
              telefone: '',
            }
          "
        >
          Novo usuário
        </BaseButton>
      </div>
      <BaseTable :colunas="colunasUsuarios" :linhas="usuarios">
        <template #ativo="{ linha }">
          <StatusBadge
            :status="linha.ativo ? 'ATIVO' : 'CANCELADO'"
            :rotulo="linha.ativo ? 'ativo' : 'inativo'"
          />
        </template>
      </BaseTable>
    </section>

    <section v-else-if="aba === 'comissao'">
      <BaseCard
        titulo="Tabela de comissão"
        subtitulo="Vale para contratos novos; os antigos mantêm o percentual congelado"
      >
        <form v-if="comissao" class="space-y-4" @submit.prevent="salvarComissao">
          <div class="grid gap-4 sm:grid-cols-2">
            <BaseInput v-model="comissao.percentual_venda" rotulo="Comissão de venda (%)" />
          </div>
          <div class="grid gap-4 sm:grid-cols-3">
            <BaseInput v-model="comissao.rateio_captador" rotulo="Captador (%)" />
            <BaseInput v-model="comissao.rateio_vendedor" rotulo="Vendedor (%)" />
            <BaseInput v-model="comissao.rateio_imobiliaria" rotulo="Imobiliária (%)" />
          </div>
          <p
            class="text-sm"
            :class="somaRateio === 100 ? 'text-slate-500' : 'text-red-600 font-medium'"
          >
            Soma do rateio: {{ somaRateio }}% (precisa ser exatamente 100%)
          </p>
          <BaseButton tipo="submit" :desabilitado="somaRateio !== 100">
            Salvar tabela
          </BaseButton>
        </form>
      </BaseCard>
    </section>

    <section v-else class="space-y-4">
      <BaseCard titulo="Portais" subtitulo="Cada portal tem seu próprio segredo de webhook">
        <ul class="divide-y divide-slate-100">
          <li
            v-for="integracao in integracoes"
            :key="integracao.id"
            class="flex flex-wrap items-center justify-between gap-3 py-3"
          >
            <div class="min-w-48">
              <p class="text-sm font-medium text-slate-900">{{ integracao.portal_display }}</p>
              <p class="break-all text-xs text-slate-500">{{ integracao.url_webhook }}</p>
            </div>
            <div class="flex gap-2">
              <BaseButton variante="secundaria" @click="sincronizar(integracao)">
                Sincronizar
              </BaseButton>
              <BaseButton variante="fantasma" @click="rotacionar(integracao)">
                Rotacionar segredo
              </BaseButton>
            </div>
          </li>
          <li v-if="!integracoes.length" class="py-4 text-sm text-slate-500">
            Nenhum portal configurado ainda.
          </li>
        </ul>
      </BaseCard>

      <BaseCard
        titulo="Fila de integração"
        subtitulo="Eventos com erro podem ser reprocessados"
      >
        <ul class="divide-y divide-slate-100">
          <li
            v-for="evento in eventos"
            :key="evento.id"
            class="flex flex-wrap items-center justify-between gap-3 py-2 text-sm"
          >
            <span class="font-medium text-slate-700">{{ evento.evento }}</span>
            <span class="text-slate-500">{{ evento.referencia }}</span>
            <StatusBadge :status="evento.status" />
            <BaseButton
              v-if="evento.status !== 'ENVIADO'"
              variante="fantasma"
              @click="reprocessar(evento)"
            >
              Reprocessar
            </BaseButton>
          </li>
          <li v-if="!eventos.length" class="py-3 text-sm text-slate-500">Fila vazia.</li>
        </ul>
      </BaseCard>
    </section>

    <BaseModal v-if="novoUsuario" titulo="Novo usuário" @fechar="novoUsuario = null">
      <div class="space-y-4">
        <BaseInput v-model="novoUsuario.nome_completo" rotulo="Nome completo" obrigatorio />
        <BaseInput v-model="novoUsuario.email" rotulo="E-mail" tipo="email" obrigatorio />
        <BaseInput v-model="novoUsuario.telefone" rotulo="Telefone" />
        <BaseSelect
          v-model="novoUsuario.papel"
          rotulo="Papel"
          :opcoes="['ADMIN', 'GERENTE', 'CORRETOR', 'FINANCEIRO']"
        />
        <BaseInput
          v-model="novoUsuario.senha"
          rotulo="Senha provisória"
          tipo="password"
          obrigatorio
        />
      </div>
      <template #rodape>
        <BaseButton variante="secundaria" @click="novoUsuario = null">Cancelar</BaseButton>
        <BaseButton @click="salvarUsuario">Criar usuário</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>
