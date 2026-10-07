<script setup>
import 'leaflet/dist/leaflet.css'

import L from 'leaflet'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  latitude: { type: [String, Number], default: null },
  longitude: { type: [String, Number], default: null },
  titulo: { type: String, default: '' },
  endereco: { type: String, default: '' },
})

const container = ref(null)
let mapa = null
let marcador = null

const temCoordenada = () =>
  props.latitude !== null &&
  props.longitude !== null &&
  !Number.isNaN(Number(props.latitude)) &&
  !Number.isNaN(Number(props.longitude))

/**
 * Mapa do imóvel com tiles do OpenStreetMap.
 *
 * Serviço aberto, sem chave e sem custo por visita, que é o que permite deixar
 * o mapa na página pública de cada anúncio. A atribuição no rodapé do mapa é
 * exigida pela licença dos dados.
 */
function desenhar() {
  if (!container.value || !temCoordenada()) return

  const ponto = [Number(props.latitude), Number(props.longitude)]

  if (!mapa) {
    mapa = L.map(container.value, { scrollWheelZoom: false }).setView(ponto, 16)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap',
      maxZoom: 19,
    }).addTo(mapa)
  } else {
    mapa.setView(ponto, 16)
  }

  if (marcador) marcador.remove()
  marcador = L.marker(ponto).addTo(mapa)
  if (props.titulo) marcador.bindPopup(`<strong>${props.titulo}</strong>`)
}

onMounted(desenhar)
watch(() => [props.latitude, props.longitude], desenhar)
onBeforeUnmount(() => mapa?.remove())
</script>

<template>
  <figure class="m-0">
    <div
      v-if="temCoordenada()"
      ref="container"
      class="h-80 w-full overflow-hidden rounded-xl ring-1 ring-slate-200"
    />
    <p
      v-else
      class="rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500 ring-1 ring-slate-200"
    >
      Este anúncio ainda não tem localização no mapa.
    </p>
    <figcaption v-if="endereco" class="mt-2 text-sm text-slate-500">
      {{ endereco }}
    </figcaption>
  </figure>
</template>
