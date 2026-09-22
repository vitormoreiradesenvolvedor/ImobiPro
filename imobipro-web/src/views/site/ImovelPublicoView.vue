<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import CabecalhoPublico from '@/components/site/CabecalhoPublico.vue'
import MapaDoImovel from '@/components/site/MapaDoImovel.vue'
import RodapePublico from '@/components/site/RodapePublico.vue'
import { useIdentidade } from '@/composables/useIdentidade'
import { siteService } from '@/services/api'
import { moeda } from '@/utils/formatters'

const route = useRoute()
const subdominio = computed(() => route.params.subdominio)
const { identidade } = useIdentidade(() => route.params.subdominio)

const imovel = ref(null)
const carregando = ref(true)
const fotoAtual = ref(0)
const enviando = ref(false)
const protocolo = ref('')
const erro = ref('')

const pedido = ref({
  solicitante_nome: '',
  solicitante_telefone: '',
  solicitante_email: '',
  preferencia_data: '',
  preferencia_periodo: 'MANHA',
  mensagem: '',
})

const galeria = computed(() => imovel.value?.fotos ?? [])
const videos = computed(
  () => imovel.value?.midias?.filter((midia) => midia.tipo === 'VIDEO') ?? [],
)
const banner = computed(() =>
  imovel.value?.midias?.find((midia) => midia.tipo === 'BANNER' && midia.destaque),
)
const plantas = computed(
  () => imovel.value?.midias?.filter((midia) => midia.tipo === 'PLANTA') ?? [],
)

const enderecoCompleto = computed(() => {
  const endereco = imovel.value?.endereco
  if (!endereco) return ''
  const rua = [endereco.logradouro, endereco.numero].filter(Boolean).join(', ')
  return [rua, endereco.bairro, `${endereco.cidade}/${endereco.uf}`].filter(Boolean).join(' · ')
})

const preco = computed(() => {
  if (!imovel.value) return ''
  return imovel.value.valor_locacao
    ? `${moeda(imovel.value.valor_locacao)}/mês`
    : moeda(imovel.value.valor_venda)
})

async function pedirVisita() {
  enviando.value = true
  erro.value = ''
  try {
    const { data } = await siteService.abrirTicket(subdominio.value, {
      tipo: 'VISITA',
      imovel_codigo: imovel.value.codigo,
      ...pedido.value,
      preferencia_data: pedido.value.preferencia_data || null,
    })
    protocolo.value = data.protocolo
  } catch (falha) {
    const campos = falha.response?.data?.campos ?? {}
    erro.value =
      Object.values(campos).flat()[0] ??
      falha.response?.data?.detail ??
      'Não foi possível enviar o pedido. Tente de novo.'
  } finally {
    enviando.value = false
  }
}

onMounted(async () => {
  const { data } = await siteService.imovel(subdominio.value, route.params.codigo)
  imovel.value = data
  carregando.value = false
})
</script>

<template>
  <div class="superficie flex min-h-screen flex-col">
    <p v-if="carregando" class="py-20 text-center text-slate-400">Carregando imóvel…</p>

    <template v-else-if="imovel">
      <CabecalhoPublico :identidade="identidade" :subdominio="subdominio" compacto>
        <div class="mx-auto max-w-6xl px-4 pb-8">
          <RouterLink
            :to="{ name: 'site-vitrine', params: { subdominio } }"
            class="text-sm text-white/70 transition hover:text-white"
          >
            todos os imóveis
          </RouterLink>
          <h1 class="mt-2 text-3xl font-bold tracking-tight">{{ imovel.titulo }}</h1>
          <p class="mt-1 text-sm text-white/70">
            {{ imovel.codigo }} · {{ imovel.tipo_display }} · {{ enderecoCompleto }}
          </p>
          <p class="numerico mt-4 text-2xl font-bold">
            {{ preco }}
            <span class="text-sm font-medium text-white/60">{{
              imovel.finalidade_display
            }}</span>
          </p>
        </div>
      </CabecalhoPublico>

      <main
        class="mx-auto grid w-full max-w-6xl flex-1 gap-8 px-4 py-10 lg:grid-cols-[1.6fr_1fr]"
      >
        <div class="space-y-8">
          <section v-if="banner" class="overflow-hidden rounded-xl">
            <img :src="banner.arquivo" :alt="banner.titulo || imovel.titulo" class="w-full" />
          </section>

          <section v-if="galeria.length" class="space-y-3">
            <img
              :src="galeria[fotoAtual].arquivo"
              :alt="galeria[fotoAtual].legenda || imovel.titulo"
              class="aspect-video w-full rounded-xl object-cover ring-1 ring-slate-200"
            />
            <div class="flex gap-2 overflow-x-auto pb-1">
              <button
                v-for="(foto, indice) in galeria"
                :key="foto.id"
                type="button"
                class="shrink-0 overflow-hidden rounded-lg ring-2 transition"
                :class="indice === fotoAtual ? 'ring-marca' : 'ring-transparent'"
                :aria-label="`Foto ${indice + 1}`"
                :aria-current="indice === fotoAtual"
                @click="fotoAtual = indice"
              >
                <img
                  :src="foto.arquivo_thumb || foto.arquivo"
                  alt=""
                  class="h-16 w-24 object-cover"
                  loading="lazy"
                />
              </button>
            </div>
          </section>

          <section v-if="videos.length" class="space-y-3">
            <h2 class="text-lg font-semibold text-slate-900">Vídeo do imóvel</h2>
            <video
              v-for="video in videos"
              :key="video.id"
              :src="video.arquivo"
              controls
              class="w-full rounded-xl ring-1 ring-slate-200"
            >
              <track kind="captions" />
            </video>
          </section>

          <section class="space-y-3">
            <h2 class="text-lg font-semibold text-slate-900">Sobre o imóvel</h2>
            <p class="whitespace-pre-line leading-relaxed text-slate-600">
              {{ imovel.descricao || 'Sem descrição cadastrada.' }}
            </p>

            <dl class="grid grid-cols-2 gap-3 pt-2 sm:grid-cols-4">
              <div v-if="imovel.quartos" class="cartao p-3">
                <dt class="text-xs text-slate-500">Quartos</dt>
                <dd class="text-lg font-semibold">{{ imovel.quartos }}</dd>
              </div>
              <div v-if="imovel.banheiros" class="cartao p-3">
                <dt class="text-xs text-slate-500">Banheiros</dt>
                <dd class="text-lg font-semibold">{{ imovel.banheiros }}</dd>
              </div>
              <div v-if="imovel.vagas" class="cartao p-3">
                <dt class="text-xs text-slate-500">Vagas</dt>
                <dd class="text-lg font-semibold">{{ imovel.vagas }}</dd>
              </div>
              <div v-if="imovel.area_util" class="cartao p-3">
                <dt class="text-xs text-slate-500">Área útil</dt>
                <dd class="text-lg font-semibold">{{ imovel.area_util }} m²</dd>
              </div>
            </dl>

            <ul v-if="imovel.caracteristicas_detalhe?.length" class="flex flex-wrap gap-2 pt-1">
              <li
                v-for="item in imovel.caracteristicas_detalhe"
                :key="item.id"
                class="rounded-full bg-marca-suave px-3 py-1 text-sm font-medium text-marca-escura"
              >
                {{ item.nome }}
              </li>
            </ul>
          </section>

          <section v-if="plantas.length" class="space-y-3">
            <h2 class="text-lg font-semibold text-slate-900">Planta</h2>
            <img
              v-for="planta in plantas"
              :key="planta.id"
              :src="planta.arquivo"
              :alt="planta.titulo || 'Planta do imóvel'"
              class="w-full rounded-xl ring-1 ring-slate-200"
            />
          </section>

          <section class="space-y-3">
            <h2 class="text-lg font-semibold text-slate-900">Onde fica</h2>
            <MapaDoImovel
              :latitude="imovel.endereco?.latitude"
              :longitude="imovel.endereco?.longitude"
              :titulo="imovel.titulo"
              :endereco="enderecoCompleto"
            />
          </section>
        </div>

        <aside class="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <div class="cartao overflow-hidden">
            <div class="bg-marca-suave px-5 py-4">
              <p class="text-sm font-medium text-marca-escura">
                {{ imovel.finalidade_display }}
              </p>
              <p class="numerico text-3xl font-bold text-marca-escura">{{ preco }}</p>
            </div>
            <div
              v-if="Number(imovel.valor_condominio) > 0 || Number(imovel.valor_iptu_mensal) > 0"
              class="space-y-1 px-5 py-4 text-sm text-slate-500"
            >
              <p v-if="Number(imovel.valor_condominio) > 0" class="numerico">
                + {{ moeda(imovel.valor_condominio) }} de condomínio
              </p>
              <p v-if="Number(imovel.valor_iptu_mensal) > 0" class="numerico">
                + {{ moeda(imovel.valor_iptu_mensal) }} de IPTU por mês
              </p>
            </div>
          </div>

          <div class="cartao p-5">
            <output v-if="protocolo" class="block space-y-2 text-sm">
              <p class="text-lg font-semibold text-slate-900">Pedido registrado</p>
              <p class="text-slate-600">
                Guarde o protocolo <strong class="numerico">{{ protocolo }}</strong
                >. Um corretor entra em contato pelo telefone informado.
              </p>
              <RouterLink
                :to="{ name: 'site-acompanhar', params: { subdominio }, query: { protocolo } }"
                class="inline-block pt-1 font-medium text-marca hover:underline"
              >
                Acompanhar o atendimento
              </RouterLink>
            </output>

            <form v-else class="space-y-3" @submit.prevent="pedirVisita">
              <h2 class="text-lg font-semibold text-slate-900">Agendar uma visita</h2>
              <p class="text-sm text-slate-500">
                Sem cadastro. Você recebe um protocolo para acompanhar.
              </p>

              <label class="block">
                <span class="mb-1 block text-sm font-medium text-slate-700">Seu nome</span>
                <input
                  v-model="pedido.solicitante_nome"
                  required
                  class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                />
              </label>

              <label class="block">
                <span class="mb-1 block text-sm font-medium text-slate-700">Telefone</span>
                <input
                  v-model="pedido.solicitante_telefone"
                  required
                  placeholder="(35) 99999-0000"
                  class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                />
              </label>

              <label class="block">
                <span class="mb-1 block text-sm font-medium text-slate-700">E-mail</span>
                <input
                  v-model="pedido.solicitante_email"
                  type="email"
                  class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                />
              </label>

              <div class="grid grid-cols-2 gap-3">
                <label class="block">
                  <span class="mb-1 block text-sm font-medium text-slate-700">Dia</span>
                  <input
                    v-model="pedido.preferencia_data"
                    type="date"
                    class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                  />
                </label>
                <label class="block">
                  <span class="mb-1 block text-sm font-medium text-slate-700">Período</span>
                  <select
                    v-model="pedido.preferencia_periodo"
                    class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                  >
                    <option value="MANHA">Manhã</option>
                    <option value="TARDE">Tarde</option>
                    <option value="NOITE">Noite</option>
                  </select>
                </label>
              </div>

              <label class="block">
                <span class="mb-1 block text-sm font-medium text-slate-700">Mensagem</span>
                <textarea
                  v-model="pedido.mensagem"
                  rows="3"
                  placeholder="Conte o que precisa saber"
                  class="w-full rounded-lg border-0 px-3 py-2 text-sm ring-1 ring-inset ring-slate-200 focus:ring-marca"
                />
              </label>

              <p v-if="erro" class="text-sm text-red-600" role="alert">{{ erro }}</p>

              <button
                type="submit"
                :disabled="enviando"
                class="w-full rounded-lg bg-marca px-4 py-3 font-semibold text-white shadow-sm transition hover:brightness-110 disabled:opacity-60"
              >
                {{ enviando ? 'Enviando…' : 'Pedir visita' }}
              </button>
            </form>
          </div>
        </aside>
      </main>

      <RodapePublico :identidade="identidade" />
    </template>
  </div>
</template>
