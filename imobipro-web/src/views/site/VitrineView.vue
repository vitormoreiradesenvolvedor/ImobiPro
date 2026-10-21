<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import CabecalhoPublico from '@/components/site/CabecalhoPublico.vue'
import RodapePublico from '@/components/site/RodapePublico.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { siteService } from '@/services/api'
import { moeda } from '@/utils/formatters'

const route = useRoute()
const router = useRouter()

const subdominio = computed(() => route.params.subdominio)
const { identidade } = useIdentidade(() => route.params.subdominio)
const catalogo = ref(null)
const destaques = ref([])
const imoveis = ref([])
const total = ref(0)
const carregando = ref(true)

// O filtro vive na URL: link de categoria é o que o corretor manda no WhatsApp.
const filtros = ref({
  finalidade: route.query.finalidade ?? '',
  tipo: route.query.tipo ?? '',
  bairro: route.query.bairro ?? '',
  quartos_min: route.query.quartos_min ?? '',
  search: route.query.search ?? '',
})

const FAIXAS = {
  ate_1500: { valor_locacao_max: 1500 },
  '1500_3000': { valor_locacao_min: 1500, valor_locacao_max: 3000 },
  '3000_5000': { valor_locacao_min: 3000, valor_locacao_max: 5000 },
  acima_5000: { valor_locacao_min: 5000 },
}
const faixaEscolhida = ref(route.query.faixa ?? '')

const parametros = computed(() => {
  const limpos = Object.fromEntries(
    Object.entries(filtros.value).filter(([, valor]) => valor !== '' && valor !== null),
  )
  const faixa = FAIXAS[faixaEscolhida.value]
  return faixa ? { ...limpos, ...faixa } : limpos
})

const temFiltro = computed(() => Object.keys(parametros.value).length > 0)

const grupos = computed(() =>
  catalogo.value
    ? [
        { titulo: 'Finalidade', campo: 'finalidade', itens: catalogo.value.por_finalidade },
        { titulo: 'Tipo de imóvel', campo: 'tipo', itens: catalogo.value.por_tipo },
        { titulo: 'Bairro', campo: 'bairro', itens: catalogo.value.por_bairro },
        {
          titulo: 'Faixa de aluguel',
          campo: 'faixa',
          itens: catalogo.value.por_faixa_de_aluguel,
        },
      ]
    : [],
)

async function carregar() {
  carregando.value = true
  try {
    const [lista, categorias] = await Promise.all([
      siteService.imoveis(subdominio.value, { ...parametros.value, page_size: 24 }),
      siteService.catalogo(subdominio.value, parametros.value),
    ])
    imoveis.value = lista.data.results ?? lista.data
    total.value = lista.data.count ?? imoveis.value.length
    catalogo.value = categorias.data
  } finally {
    carregando.value = false
  }
}

function escolhido(campo, valor) {
  return (campo === 'faixa' ? faixaEscolhida.value : filtros.value[campo]) === valor
}

function aplicar(campo, valor) {
  if (campo === 'faixa') {
    faixaEscolhida.value = faixaEscolhida.value === valor ? '' : valor
  } else {
    filtros.value[campo] = filtros.value[campo] === valor ? '' : valor
  }
  router.replace({
    query: {
      ...Object.fromEntries(Object.entries(filtros.value).filter(([, v]) => v)),
      ...(faixaEscolhida.value ? { faixa: faixaEscolhida.value } : {}),
    },
  })
}

function limpar() {
  filtros.value = { finalidade: '', tipo: '', bairro: '', quartos_min: '', search: '' }
  faixaEscolhida.value = ''
  router.replace({ query: {} })
}

function preco(imovel) {
  if (imovel.valor_locacao) return `${moeda(imovel.valor_locacao)}/mês`
  return moeda(imovel.valor_venda)
}

onMounted(async () => {
  const { data } = await siteService.destaques(subdominio.value)
  destaques.value = data
  await carregar()
})

watch([filtros, faixaEscolhida], carregar, { deep: true })
</script>

<template>
  <div class="superficie flex min-h-screen flex-col">
    <CabecalhoPublico :identidade="identidade" :subdominio="subdominio">
      <div class="mx-auto max-w-6xl px-4 pb-12 pt-6">
        <p class="text-sm font-medium uppercase tracking-widest text-white/60">
          {{ identidade?.nome ?? 'Vitrine' }}
        </p>
        <h1 class="mt-2 max-w-2xl text-3xl font-bold leading-tight sm:text-4xl">
          O próximo endereço da sua vida está aqui
        </h1>
        <p class="mt-2 text-white/70">
          {{ total }} {{ total === 1 ? 'imóvel publicado' : 'imóveis publicados' }} e
          atualizados hoje. Agende a visita sem cadastro.
        </p>

        <label class="mt-6 block max-w-2xl">
          <span class="sr-only">Buscar</span>
          <input
            v-model="filtros.search"
            type="search"
            placeholder="cobertura com vista, apartamento no centro…"
            class="w-full rounded-xl border-0 bg-white/95 px-4 py-3.5 text-slate-800 shadow-lg shadow-black/20 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-white/70"
          />
        </label>
      </div>
    </CabecalhoPublico>

    <main class="mx-auto w-full max-w-6xl flex-1 space-y-10 px-4 py-10">
      <section v-if="destaques.length && !temFiltro">
        <h2 class="mb-4 text-lg font-semibold text-slate-900">Em destaque</h2>
        <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="imovel in destaques.slice(0, 3)"
            :key="imovel.id"
            :to="{ name: 'site-imovel', params: { subdominio, codigo: imovel.codigo } }"
            class="cartao group relative overflow-hidden transition hover:-translate-y-1"
          >
            <div class="relative">
              <img
                v-if="imovel.foto_capa"
                :src="imovel.foto_capa"
                :alt="imovel.titulo"
                class="h-52 w-full object-cover transition duration-500 group-hover:scale-105"
                loading="lazy"
              />
              <span
                class="absolute left-3 top-3 rounded-full bg-marca-profunda/85 px-3 py-1 text-xs font-semibold text-white backdrop-blur"
              >
                Destaque
              </span>
            </div>
            <div class="space-y-1 p-5">
              <p class="text-xs uppercase tracking-wide text-slate-400">
                {{ imovel.codigo }}
              </p>
              <p class="font-semibold text-slate-900 group-hover:text-marca">
                {{ imovel.titulo }}
              </p>
              <p class="text-sm text-slate-500">{{ imovel.bairro }}, {{ imovel.cidade }}</p>
              <p class="numerico pt-1 text-xl font-bold text-marca-escura">
                {{ preco(imovel) }}
              </p>
            </div>
          </RouterLink>
        </div>
      </section>

      <section v-if="catalogo" class="cartao space-y-5 p-6">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold text-slate-900">Encontre pelo que importa</h2>
          <button
            v-if="temFiltro"
            type="button"
            class="rounded-lg bg-marca-suave px-3 py-1.5 text-sm font-medium text-marca-escura transition hover:brightness-95"
            @click="limpar"
          >
            limpar filtros
          </button>
        </div>

        <div v-for="grupo in grupos" :key="grupo.campo">
          <p v-if="grupo.itens.length" class="mb-2 text-sm font-medium text-slate-700">
            {{ grupo.titulo }}
          </p>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="categoria in grupo.itens"
              :key="categoria.valor"
              type="button"
              class="rounded-full px-3.5 py-1.5 text-sm font-medium transition"
              :class="
                escolhido(grupo.campo, categoria.valor)
                  ? 'bg-marca text-white shadow-sm'
                  : 'bg-marca-suave text-marca-escura hover:bg-marca-borda'
              "
              :aria-pressed="escolhido(grupo.campo, categoria.valor)"
              @click="aplicar(grupo.campo, categoria.valor)"
            >
              {{ categoria.rotulo }}
              <span class="numerico ml-1 text-xs opacity-70">{{ categoria.total }}</span>
            </button>
          </div>
        </div>
      </section>

      <section>
        <p v-if="carregando" class="py-12 text-center text-slate-400">Carregando…</p>

        <p v-else-if="!imoveis.length" class="cartao p-10 text-center text-slate-500">
          Nenhum imóvel com esses filtros. Tente tirar um deles.
        </p>

        <div v-else class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <RouterLink
            v-for="imovel in imoveis"
            :key="imovel.id"
            :to="{ name: 'site-imovel', params: { subdominio, codigo: imovel.codigo } }"
            class="cartao group overflow-hidden transition hover:-translate-y-1"
          >
            <img
              v-if="imovel.foto_capa"
              :src="imovel.foto_capa"
              :alt="imovel.titulo"
              class="h-48 w-full object-cover transition duration-500 group-hover:scale-105"
              loading="lazy"
            />
            <div class="space-y-1 p-5">
              <p class="text-xs uppercase tracking-wide text-slate-400">
                {{ imovel.codigo }} · {{ imovel.tipo_display }}
              </p>
              <p class="font-semibold text-slate-900 group-hover:text-marca">
                {{ imovel.titulo }}
              </p>
              <p class="text-sm text-slate-500">{{ imovel.bairro }}, {{ imovel.cidade }}</p>
              <p class="flex flex-wrap gap-x-3 pt-1 text-sm text-slate-500">
                <span v-if="imovel.quartos">{{ imovel.quartos }} quartos</span>
                <span v-if="imovel.banheiros">{{ imovel.banheiros }} banh.</span>
                <span v-if="imovel.area_util">{{ imovel.area_util }} m²</span>
              </p>
              <p class="numerico pt-2 text-xl font-bold text-marca-escura">
                {{ preco(imovel) }}
              </p>
            </div>
          </RouterLink>
        </div>
      </section>
    </main>

    <RodapePublico :identidade="identidade" />
  </div>
</template>
