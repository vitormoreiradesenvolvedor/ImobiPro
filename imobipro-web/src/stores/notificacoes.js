import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { useToast } from '@/composables/useToast'
import { notificacoesService } from '@/services/api'

/** Sino do topo + canal WebSocket de tempo real. */
export const useNotificacoesStore = defineStore('notificacoes', () => {
  const itens = ref([])
  const naoLidas = ref(0)
  const conectado = ref(false)
  let socket = null
  let tentativas = 0

  const recentes = computed(() => itens.value.slice(0, 12))

  async function carregar() {
    const [lista, contador] = await Promise.all([
      notificacoesService.listar({ page_size: 20 }),
      notificacoesService.naoLidas(),
    ])
    itens.value = lista.data.results ?? lista.data
    naoLidas.value = contador.data.nao_lidas
  }

  function conectar(token) {
    if (!token || socket) return

    const protocolo = window.location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocket(
      `${protocolo}://${window.location.host}/ws/notificacoes/?token=${token}`,
    )

    socket.onopen = () => {
      conectado.value = true
      tentativas = 0
    }

    socket.onmessage = (evento) => {
      const dados = JSON.parse(evento.data)
      if (dados.tipo === 'CONECTADO') return

      itens.value = [dados, ...itens.value]
      naoLidas.value += 1
      useToast().info(dados.titulo)
    }

    socket.onclose = () => {
      conectado.value = false
      socket = null
      // Reconexão com espera crescente: rede instável não vira laço de conexão.
      if (tentativas < 5) {
        const espera = 2 ** tentativas * 1000
        tentativas += 1
        setTimeout(() => conectar(token), espera)
      }
    }
  }

  function desconectar() {
    tentativas = 99
    socket?.close()
    socket = null
    itens.value = []
    naoLidas.value = 0
  }

  async function marcarLida(id) {
    await notificacoesService.marcarLida(id)
    itens.value = itens.value.map((item) => (item.id === id ? { ...item, lida: true } : item))
    naoLidas.value = Math.max(0, naoLidas.value - 1)
  }

  async function marcarTodasLidas() {
    await notificacoesService.marcarTodasLidas()
    itens.value = itens.value.map((item) => ({ ...item, lida: true }))
    naoLidas.value = 0
  }

  return {
    itens,
    recentes,
    naoLidas,
    conectado,
    carregar,
    conectar,
    desconectar,
    marcarLida,
    marcarTodasLidas,
  }
})
