import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

/**
 * O mapa quebrava o app inteiro: `layerGroup` não tem `getBounds`, o erro subia
 * pelo watcher e corrompia o render a tela seguinte nem trocava de conteúdo.
 * Leaflet é falsificado aqui porque jsdom não dá layout ao contêiner.
 */
const camada = {
  clearLayers: vi.fn(),
  addLayer: vi.fn(),
  addTo: vi.fn(() => camada),
  getBounds: vi.fn(() => ({ isValid: () => true })),
}

const mapa = {
  setView: vi.fn(() => mapa),
  fitBounds: vi.fn(),
  remove: vi.fn(),
}

const leaflet = {
  map: vi.fn(() => mapa),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  featureGroup: vi.fn(() => camada),
  layerGroup: vi.fn(() => ({ ...camada, getBounds: undefined })),
  marker: vi.fn(() => ({ bindPopup: vi.fn(), on: vi.fn() })),
  divIcon: vi.fn(() => ({})),
}

vi.mock('leaflet', () => ({ default: leaflet }))
vi.mock('leaflet/dist/leaflet.css', () => ({}))
vi.mock('vue-router', async () => {
  const real = await vi.importActual('vue-router')
  return { ...real, useRouter: () => ({ push: vi.fn() }) }
})

const { default: MapaImoveis } = await import('@/components/imoveis/MapaImoveis.vue')

const IMOVEL = {
  id: 'i1',
  codigo: 'REF-000001',
  titulo: 'Apartamento 302',
  bairro: 'Centro',
  cidade: 'Lavras',
  finalidade: 'LOCACAO',
  valor_locacao: '2500.00',
  latitude: '-21.245',
  longitude: '-44.997',
}

describe('MapaImoveis', () => {
  beforeEach(() => vi.clearAllMocks())

  it('usa featureGroup, que é quem sabe calcular os limites', () => {
    mount(MapaImoveis, { props: { imoveis: [IMOVEL] } })

    expect(leaflet.featureGroup).toHaveBeenCalled()
    expect(leaflet.layerGroup).not.toHaveBeenCalled()
  })

  it('enquadra o mapa nos imóveis geocodificados', () => {
    mount(MapaImoveis, { props: { imoveis: [IMOVEL] } })

    expect(leaflet.marker).toHaveBeenCalledTimes(1)
    expect(mapa.fitBounds).toHaveBeenCalled()
  })

  it('ignora imóvel sem coordenada e não tenta enquadrar', () => {
    mount(MapaImoveis, { props: { imoveis: [{ ...IMOVEL, latitude: null, longitude: null }] } })

    expect(leaflet.marker).not.toHaveBeenCalled()
    expect(mapa.fitBounds).not.toHaveBeenCalled()
  })

  it('não enquadra quando os limites são inválidos', () => {
    camada.getBounds.mockReturnValueOnce({ isValid: () => false })

    mount(MapaImoveis, { props: { imoveis: [IMOVEL] } })

    expect(mapa.fitBounds).not.toHaveBeenCalled()
  })
})
