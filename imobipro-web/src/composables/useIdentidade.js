import { onMounted, ref } from 'vue'

import { siteService } from '@/services/api'

/**
 * Marca da imobiliária nas telas abertas do site.
 *
 * Quem chega pela vitrine não tem sessão, então a cor e o nome não podem vir do
 * `/auth/me/`. Sem isto o site de toda imobiliária sairia na cor padrão do
 * produto, que é o oposto do que um site próprio deveria parecer.
 *
 * Falha na chamada não quebra a página: fica o padrão e o visitante continua
 * vendo os imóveis.
 */
export function useIdentidade(subdominio) {
  const identidade = ref(null)

  onMounted(async () => {
    try {
      const { data } = await siteService.identidade(
        typeof subdominio === 'function' ? subdominio() : subdominio,
      )
      identidade.value = data
      if (data.cor_primaria) {
        document.documentElement.style.setProperty('--cor-primaria', data.cor_primaria)
      }
      document.title = `${data.nome} · imóveis`
    } catch {
      identidade.value = null
    }
  })

  return { identidade }
}
