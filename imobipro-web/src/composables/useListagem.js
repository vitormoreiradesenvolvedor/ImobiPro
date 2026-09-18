import { computed, ref, watch } from 'vue'

/**
 * Paginação + filtros + busca com debounce, no formato que o DRF espera.
 * Toda listagem do sistema usa isto para não reinventar o mesmo laço.
 */
export function useListagem(carregador, { filtrosIniciais = {}, tamanhoPagina = 20 } = {}) {
  const itens = ref([])
  const total = ref(0)
  const pagina = ref(1)
  const carregando = ref(false)
  const erro = ref(null)
  const filtros = ref({ ...filtrosIniciais })

  const totalPaginas = computed(() => Math.max(1, Math.ceil(total.value / tamanhoPagina)))
  const vazio = computed(() => !carregando.value && itens.value.length === 0)

  async function carregar() {
    carregando.value = true
    erro.value = null
    try {
      const limpos = Object.fromEntries(
        Object.entries(filtros.value).filter(([, valor]) => valor !== '' && valor != null),
      )
      const { data } = await carregador({
        page: pagina.value,
        page_size: tamanhoPagina,
        ...limpos,
      })
      // Endpoints agregados devolvem lista pura; os paginados, {count, results}.
      itens.value = data.results ?? data
      total.value = data.count ?? itens.value.length
    } catch (falha) {
      erro.value = falha
      itens.value = []
      total.value = 0
    } finally {
      carregando.value = false
    }
  }

  let temporizador
  watch(
    filtros,
    () => {
      clearTimeout(temporizador)
      temporizador = setTimeout(() => {
        pagina.value = 1
        carregar()
      }, 300)
    },
    { deep: true },
  )

  watch(pagina, carregar)

  return { itens, total, pagina, totalPaginas, carregando, erro, filtros, vazio, carregar }
}
