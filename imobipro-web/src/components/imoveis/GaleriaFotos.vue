<script setup>
import { ref } from 'vue'

import BaseButton from '@/components/base/BaseButton.vue'
import { useConfirmacao } from '@/composables/useConfirmacao'
import { useToast } from '@/composables/useToast'
import { imoveisService } from '@/services/api'

const props = defineProps({
  imovelId: { type: String, required: true },
  fotos: { type: Array, default: () => [] },
  editavel: { type: Boolean, default: true },
})

const emit = defineEmits(['atualizado'])
const { sucesso, erroDaApi } = useToast()
const { confirmar } = useConfirmacao()

const enviando = ref(false)
const arrastando = ref(null)
const lista = ref([...props.fotos])

async function enviar(evento) {
  const arquivos = [...evento.target.files]
  if (!arquivos.length) return

  enviando.value = true
  try {
    const { data } = await imoveisService.enviarFotos(props.imovelId, arquivos)
    lista.value = [...lista.value, ...data]
    sucesso(`${data.length} foto(s) enviada(s).`)
    emit('atualizado')
  } catch (erro) {
    erroDaApi(erro, 'Falha ao enviar as fotos.')
  } finally {
    enviando.value = false
    evento.target.value = ''
  }
}

function aoSoltar(indiceDestino) {
  if (arrastando.value === null || arrastando.value === indiceDestino) return

  const copia = [...lista.value]
  const [movida] = copia.splice(arrastando.value, 1)
  copia.splice(indiceDestino, 0, movida)
  lista.value = copia
  arrastando.value = null

  salvarOrdem()
}

async function salvarOrdem() {
  try {
    // A primeira posição vira a capa regra do back, refletida aqui.
    const { data } = await imoveisService.reordenarFotos(
      props.imovelId,
      lista.value.map((foto) => foto.id),
    )
    lista.value = data
    emit('atualizado')
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível reordenar.')
  }
}

async function remover(foto) {
  const confirmado = await confirmar({
    titulo: 'Remover foto',
    mensagem: 'A foto sai do anúncio imediatamente.',
    confirmar: 'Remover',
    perigo: true,
  })
  if (!confirmado) return
  try {
    await imoveisService.removerFoto(props.imovelId, foto.id)
    lista.value = lista.value.filter((item) => item.id !== foto.id)
    emit('atualizado')
  } catch (erro) {
    erroDaApi(erro, 'Não foi possível remover a foto.')
  }
}
</script>

<template>
  <div class="space-y-4">
    <div v-if="editavel" class="flex items-center gap-3">
      <label
        class="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-marca px-4 py-2.5 text-sm font-semibold text-white hover:brightness-110"
      >
        {{ enviando ? 'Enviando…' : 'Adicionar fotos' }}
        <input type="file" accept="image/*" multiple class="sr-only" @change="enviar" />
      </label>
      <p class="text-xs text-slate-500">
        Arraste para reordenar. A primeira foto é a capa do anúncio.
      </p>
    </div>

    <ul v-if="lista.length" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <li
        v-for="(foto, indice) in lista"
        :key="foto.id"
        class="group relative aspect-[4/3] overflow-hidden rounded-lg bg-slate-100 ring-1 ring-slate-200"
        :draggable="editavel"
        @dragstart="arrastando = indice"
        @dragover.prevent
        @drop="aoSoltar(indice)"
      >
        <img
          :src="foto.arquivo_thumb || foto.arquivo"
          :alt="foto.legenda || `Foto ${indice + 1}`"
          class="size-full object-cover"
        />
        <span
          v-if="foto.capa"
          class="absolute left-1.5 top-1.5 rounded bg-marca px-1.5 py-0.5 text-[10px] font-semibold text-white"
        >
          capa
        </span>
        <button
          v-if="editavel"
          type="button"
          class="absolute right-1.5 top-1.5 hidden rounded bg-white/90 px-1.5 py-0.5 text-xs text-red-600 group-hover:block"
          @click.prevent="remover(foto)"
        >
          remover
        </button>
      </li>
    </ul>

    <p
      v-else
      class="rounded-lg border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500"
    >
      Nenhuma foto ainda. São necessárias 5 para publicar o imóvel.
    </p>

    <BaseButton v-if="editavel && lista.length" variante="secundaria" @click="salvarOrdem">
      Salvar ordem
    </BaseButton>
  </div>
</template>
