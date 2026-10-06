<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import BaseButton from '@/components/base/BaseButton.vue'
import BaseCard from '@/components/base/BaseCard.vue'
import StatusBadge from '@/components/base/StatusBadge.vue'
import { useToast } from '@/composables/useToast'
import { vistoriasService } from '@/services/api'
import { data as formatarData } from '@/utils/formatters'

const route = useRoute()
const { sucesso, erroDaApi } = useToast()

const ESTADOS = [
  { valor: 'OTIMO', rotulo: 'Ótimo', cor: 'bg-emerald-100 text-emerald-800' },
  { valor: 'BOM', rotulo: 'Bom', cor: 'bg-sky-100 text-sky-800' },
  { valor: 'REGULAR', rotulo: 'Regular', cor: 'bg-amber-100 text-amber-800' },
  { valor: 'RUIM', rotulo: 'Ruim', cor: 'bg-red-100 text-red-800' },
  { valor: 'AUSENTE', rotulo: 'Ausente', cor: 'bg-slate-200 text-slate-700' },
]

const vistoria = ref(null)
const carregando = ref(true)
const salvandoItem = ref(null)

const editavel = computed(() => vistoria.value?.status === 'RASCUNHO')

const porComodo = computed(() => {
  const agrupado = {}
  for (const item of vistoria.value?.itens ?? []) {
    agrupado[item.comodo] ??= []
    agrupado[item.comodo].push(item)
  }
  return agrupado
})

async function carregar() {
  carregando.value = true
  const { data } = await vistoriasService.obter(route.params.id)
  vistoria.value = data
  carregando.value = false
}

async function definirEstado(item, estado) {
  if (!editavel.value) return
  salvandoItem.value = item.id
  try {
    await vistoriasService.registrarItem(vistoria.value.id, {
      comodo: item.comodo,
      item: item.item,
      estado,
      observacao: item.observacao ?? '',
      ordem: item.ordem ?? 0,
    })
    item.estado = estado
  } catch (erro) {
    erroDaApi(erro)
  } finally {
    salvandoItem.value = null
  }
}

async function anexarFotos(item, evento) {
  const arquivos = [...evento.target.files]
  if (!arquivos.length) return

  try {
    const { data } = await vistoriasService.registrarItem(
      vistoria.value.id,
      {
        comodo: item.comodo,
        item: item.item,
        estado: item.estado,
        observacao: item.observacao ?? '',
      },
      arquivos,
    )
    item.fotos = data.fotos
    sucesso(`${arquivos.length} foto(s) anexada(s).`)
  } catch (erro) {
    erroDaApi(erro)
  } finally {
    evento.target.value = ''
  }
}

async function salvarObservacao(item) {
  if (!editavel.value) return
  try {
    await vistoriasService.registrarItem(vistoria.value.id, {
      comodo: item.comodo,
      item: item.item,
      estado: item.estado,
      observacao: item.observacao ?? '',
    })
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function finalizar() {
  try {
    await vistoriasService.finalizar(vistoria.value.id)
    sucesso('Vistoria finalizada. Laudo disponível em PDF.')
    await carregar()
  } catch (erro) {
    erroDaApi(erro)
  }
}

async function assinar(quem) {
  try {
    const { data } = await vistoriasService.assinar(vistoria.value.id, { [quem]: true })
    vistoria.value = data
    sucesso('Assinatura registrada.')
  } catch (erro) {
    erroDaApi(erro)
  }
}

onMounted(carregar)
</script>

<template>
  <p v-if="carregando" class="py-16 text-center text-slate-400">Carregando vistoria…</p>

  <div v-else-if="vistoria" class="space-y-5">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-slate-900">
            Vistoria de {{ vistoria.tipo_display.toLowerCase() }}
          </h1>
          <StatusBadge :status="vistoria.status" :rotulo="vistoria.status_display" />
        </div>
        <p class="mt-1 text-sm text-slate-500">
          {{ vistoria.contrato_numero }} · {{ vistoria.imovel_codigo }} ·
          {{ formatarData(vistoria.realizada_em) }}
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <a :href="vistoriasService.urlLaudo(vistoria.id)" target="_blank" rel="noopener">
          <BaseButton variante="secundaria">Laudo em PDF</BaseButton>
        </a>
        <BaseButton v-if="editavel" @click="finalizar">Finalizar vistoria</BaseButton>
        <template v-else>
          <BaseButton
            v-if="!vistoria.assinatura_locatario"
            variante="secundaria"
            @click="assinar('locatario')"
          >
            Assinar (locatário)
          </BaseButton>
          <BaseButton
            v-if="!vistoria.assinatura_imobiliaria"
            variante="secundaria"
            @click="assinar('imobiliaria')"
          >
            Assinar (imobiliária)
          </BaseButton>
        </template>
      </div>
    </header>

    <p class="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
      {{ vistoria.total_itens }} itens ·
      <span :class="vistoria.itens_com_problema ? 'text-red-600 font-medium' : ''">
        {{ vistoria.itens_com_problema }} com apontamento
      </span>
    </p>

    <BaseCard v-for="(itens, comodo) in porComodo" :key="comodo" :titulo="comodo">
      <ul class="divide-y divide-slate-100">
        <li v-for="item in itens" :key="item.id" class="py-3">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <span class="text-sm font-medium text-slate-800">{{ item.item }}</span>

            <fieldset class="flex flex-wrap gap-1" :aria-label="`Estado de ${item.item}`">
              <button
                v-for="estado in ESTADOS"
                :key="estado.valor"
                type="button"
                class="rounded-md px-2.5 py-1 text-xs font-medium transition disabled:opacity-50"
                :class="
                  item.estado === estado.valor
                    ? estado.cor + ' ring-1 ring-inset ring-current'
                    : 'bg-slate-50 text-slate-500 hover:bg-slate-100'
                "
                :disabled="!editavel || salvandoItem === item.id"
                :aria-pressed="item.estado === estado.valor"
                @click="definirEstado(item, estado.valor)"
              >
                {{ estado.rotulo }}
              </button>
            </fieldset>
          </div>

          <div class="mt-2 flex flex-wrap items-center gap-3">
            <input
              :id="`observacao-${item.id}`"
              v-model="item.observacao"
              :aria-label="`Observação sobre ${item.item} em ${item.comodo}`"
              :disabled="!editavel"
              placeholder="Observação (ex.: risco na porta do armário)"
              class="min-w-0 flex-1 rounded-lg border-0 px-3 py-1.5 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca disabled:bg-slate-50"
              @blur="salvarObservacao(item)"
            />

            <label
              v-if="editavel"
              class="cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium text-marca ring-1 ring-marca"
            >
              + fotos
              <input
                type="file"
                accept="image/*"
                multiple
                capture="environment"
                class="sr-only"
                @change="anexarFotos(item, $event)"
              />
            </label>

            <span v-if="item.fotos?.length" class="text-xs text-slate-500">
              {{ item.fotos.length }} foto(s)
            </span>
          </div>

          <ul v-if="item.fotos?.length" class="mt-2 flex gap-2">
            <li v-for="foto in item.fotos" :key="foto.id">
              <img
                :src="foto.arquivo"
                :alt="`Foto de ${item.item}`"
                class="size-16 rounded object-cover ring-1 ring-slate-200"
              />
            </li>
          </ul>
        </li>
      </ul>
    </BaseCard>
  </div>
</template>
