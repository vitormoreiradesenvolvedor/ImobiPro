<script setup>
import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { moeda } from '@/utils/formatters'

const props = defineProps({ imoveis: { type: Array, default: () => [] } })

const container = ref(null)
const router = useRouter()
let mapa = null
let camadaMarcadores = null

// Lavras/MG como centro padrão até haver imóvel geocodificado na busca.
const CENTRO_PADRAO = [-21.245, -44.999]

function icone(imovel) {
  const valor = imovel.finalidade === 'VENDA' ? imovel.valor_venda : imovel.valor_locacao
  return L.divIcon({
    className: '',
    html: `<span class="rounded-full bg-marca px-2 py-1 text-xs font-semibold text-white
             shadow ring-2 ring-white">${moeda(valor).replace('R$', '').trim()}</span>`,
    iconSize: [70, 24],
  })
}

function desenhar() {
  if (!mapa) return
  camadaMarcadores.clearLayers()

  const pontos = props.imoveis.filter((imovel) => imovel.latitude && imovel.longitude)

  pontos.forEach((imovel) => {
    const marcador = L.marker([Number(imovel.latitude), Number(imovel.longitude)], {
      icon: icone(imovel),
      title: imovel.titulo,
    })
    marcador.bindPopup(
      `<strong>${imovel.codigo}</strong><br/>${imovel.titulo}<br/>` +
        `${imovel.bairro ?? ''}, ${imovel.cidade ?? ''}`,
    )
    marcador.on('click', () =>
      router.push({ name: 'imovel-detalhe', params: { id: imovel.id } }),
    )
    camadaMarcadores.addLayer(marcador)
  })

  // `getBounds` só existe em featureGroup; e um único ponto ainda gera limites
  // válidos, então basta conferir antes de enquadrar.
  if (pontos.length) {
    const limites = camadaMarcadores.getBounds()
    if (limites.isValid()) {
      mapa.fitBounds(limites, { padding: [40, 40], maxZoom: 15 })
    }
  }
}

onMounted(() => {
  mapa = L.map(container.value).setView(CENTRO_PADRAO, 13)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: 19,
  }).addTo(mapa)
  // featureGroup (e não layerGroup): é ele que sabe calcular os limites
  // usados para enquadrar o mapa nos imóveis encontrados.
  camadaMarcadores = L.featureGroup().addTo(mapa)
  desenhar()
})

onBeforeUnmount(() => mapa?.remove())

watch(() => props.imoveis, desenhar, { deep: true })
</script>

<template>
  <div class="overflow-hidden rounded-xl ring-1 ring-slate-200">
    <div ref="container" class="h-[70vh] w-full" />
  </div>
</template>
