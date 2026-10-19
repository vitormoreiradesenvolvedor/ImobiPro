import http from './http'

/** Fábrica de serviço REST: cada módulo fala com o DRF do mesmo jeito. */
const recurso = (base) => ({
  listar: (params) => http.get(`/${base}/`, { params }),
  obter: (id) => http.get(`/${base}/${id}/`),
  criar: (dados) => http.post(`/${base}/`, dados),
  atualizar: (id, dados) => http.patch(`/${base}/${id}/`, dados),
  remover: (id) => http.delete(`/${base}/${id}/`),
  acao: (id, nome, dados, config) => http.post(`/${base}/${id}/${nome}/`, dados, config),
  colecao: (nome, params) => http.get(`/${base}/${nome}/`, { params }),
})

export const pessoasService = {
  ...recurso('pessoas'),
  consultarCep: (cep) => http.get(`/pessoas/cep/${cep}/`),
  enviarFoto: (id, arquivo) => {
    const formulario = new FormData()
    formulario.append('foto', arquivo)
    return http.post(`/pessoas/${id}/foto/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  removerFoto: (id) => http.delete(`/pessoas/${id}/foto/`),
}

export const imoveisService = {
  ...recurso('imoveis'),
  estatisticas: () => http.get('/imoveis/estatisticas/'),
  mapa: (params) => http.get('/imoveis/mapa/', { params }),
  historico: (id) => http.get(`/imoveis/${id}/historico/`),
  publicar: (id) => http.post(`/imoveis/${id}/publicar/`),
  despublicar: (id, motivo) => http.post(`/imoveis/${id}/despublicar/`, { motivo }),
  mudarSituacao: (id, situacao, motivo) =>
    http.patch(`/imoveis/${id}/situacao/`, { situacao, motivo }),
  enviarFotos: (id, arquivos) => {
    const formulario = new FormData()
    arquivos.forEach((arquivo) => formulario.append('arquivo', arquivo))
    return http.post(`/imoveis/${id}/fotos/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  reordenarFotos: (id, ordem) => http.patch(`/imoveis/${id}/fotos/reordenar/`, { ordem }),
  geocodificar: (id) => http.post(`/imoveis/${id}/geocodificar/`),
  enviarMidias: (id, arquivos, { tipo = 'BANNER', titulo = '', descricao = '' } = {}) => {
    const formulario = new FormData()
    arquivos.forEach((arquivo) => formulario.append('arquivo', arquivo))
    formulario.append('tipo', tipo)
    formulario.append('titulo', titulo)
    formulario.append('descricao', descricao)
    return http.post(`/imoveis/${id}/midias/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  destacarMidia: (id, midiaId) => http.post(`/imoveis/${id}/midias/${midiaId}/destaque/`),
  removerMidia: (id, midiaId) => http.delete(`/imoveis/${id}/midias/${midiaId}/`),
  removerFoto: (id, fotoId) => http.delete(`/imoveis/${id}/fotos/${fotoId}/`),
  definirCapa: (id, fotoId) => http.post(`/imoveis/${id}/fotos/${fotoId}/capa/`),
  caracteristicas: () => http.get('/caracteristicas/'),
}

export const leadsService = {
  ...recurso('leads'),
  funil: (params) => http.get('/leads/funil/', { params }),
  estatisticas: (params) => http.get('/leads/estatisticas/', { params }),
  mover: (id, dados) => http.patch(`/leads/${id}/mover/`, dados),
  registrarInteracao: (id, dados) => http.post(`/leads/${id}/interacoes/`, dados),
  atribuir: (id, corretorId) =>
    http.post(`/leads/${id}/atribuir/`, { corretor_id: corretorId }),
}

export const visitasService = {
  ...recurso('visitas'),
  agenda: (data) => http.get('/visitas/agenda/', { params: { data } }),
  feedback: (id, dados) => http.post(`/visitas/${id}/feedback/`, dados),
  cancelar: (id) => http.post(`/visitas/${id}/cancelar/`),
}

export const propostasService = {
  ...recurso('propostas'),
  aceitar: (id) => http.post(`/propostas/${id}/aceitar/`),
  recusar: (id, motivo) => http.post(`/propostas/${id}/recusar/`, { motivo }),
}

export const contratosService = {
  ...recurso('contratos'),
  adicionarParte: (id, dados) => http.post(`/contratos/${id}/partes/`, dados),
  criarAcessoDoInquilino: (id) => http.post(`/contratos/${id}/acesso-do-inquilino/`),
  ativar: (id, assinadoEm) =>
    http.post(`/contratos/${id}/ativar/`, { assinado_em: assinadoEm }),
  rescindir: (id, motivo, data) => http.post(`/contratos/${id}/rescindir/`, { motivo, data }),
  encerrar: (id) => http.post(`/contratos/${id}/encerrar/`),
  previaReajuste: (id, percentual) =>
    http.post(`/contratos/${id}/reajustar/`, { percentual, aplicar: false }),
  aplicarReajuste: (id, percentual) =>
    http.post(`/contratos/${id}/reajustar/`, { percentual, aplicar: true }),
  urlPdf: (id) => `${http.defaults.baseURL}/contratos/${id}/pdf/`,
}

export const comissoesService = {
  ...recurso('comissoes'),
  liberar: (id) => http.post(`/comissoes/${id}/liberar/`),
  pagar: (id) => http.post(`/comissoes/${id}/pagar/`),
  configuracao: () => http.get('/configuracoes/comissao/'),
  salvarConfiguracao: (dados) => http.post('/configuracoes/comissao/', dados),
}

export const cobrancasService = {
  ...recurso('cobrancas'),
  baixar: (id, dados) => http.post(`/cobrancas/${id}/baixar/`, dados),
  eventos: (id) => http.get(`/cobrancas/${id}/eventos/`),
  inadimplencia: (competencia) =>
    http.get('/cobrancas/inadimplencia/', { params: { competencia } }),
  gerar: (contratoId, dados) => http.post(`/cobrancas/gerar/${contratoId}/`, dados),
  conciliar: (arquivo) => {
    const formulario = new FormData()
    formulario.append('arquivo', arquivo)
    return http.post('/cobrancas/conciliar/', formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export const repassesService = {
  ...recurso('repasses'),
  liquidar: (id, data) => http.post(`/repasses/${id}/liquidar/`, { data }),
  adicionarRetencao: (id, dados) => http.post(`/repasses/${id}/retencoes/`, dados),
  aPagar: () => http.get('/repasses/a_pagar/'),
  urlExtrato: (id) => `${http.defaults.baseURL}/repasses/${id}/extrato/`,
}

export const vistoriasService = {
  ...recurso('vistorias'),
  registrarItem: (id, dados, fotos = []) => {
    const formulario = new FormData()
    Object.entries(dados).forEach(([chave, valor]) => formulario.append(chave, valor))
    fotos.forEach((foto) => formulario.append('fotos', foto))
    return http.post(`/vistorias/${id}/itens/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  finalizar: (id) => http.post(`/vistorias/${id}/finalizar/`),
  assinar: (id, dados) => http.post(`/vistorias/${id}/assinar/`, dados),
  comparativo: (contratoId) => http.get(`/vistorias/comparativo/${contratoId}/`),
  urlLaudo: (id) => `${http.defaults.baseURL}/vistorias/${id}/laudo/`,
}

export const financeiroService = {
  ...recurso('transacoes'),
  estornar: (id, motivo) => http.post(`/transacoes/${id}/estornar/`, { motivo }),
  resumo: () => http.get('/financeiro/resumo/'),
  relatorio: (nome, params) => http.get(`/relatorios/${nome}/`, { params }),
}

export const usuariosService = recurso('auth/usuarios')

export const notificacoesService = {
  ...recurso('notificacoes'),
  naoLidas: () => http.get('/notificacoes/nao-lidas/'),
  marcarLida: (id) => http.post(`/notificacoes/${id}/marcar_lida/`),
  marcarTodasLidas: () => http.post('/notificacoes/marcar-todas-lidas/'),
}

export const integracoesService = {
  ...recurso('integracoes/portais'),
  sincronizar: (id) => http.post(`/integracoes/portais/${id}/sincronizar/`),
  rotacionarSegredo: (id) => http.post(`/integracoes/portais/${id}/rotacionar-segredo/`),
  eventos: (params) => http.get('/integracoes/eventos/', { params }),
  reprocessar: (id) => http.post(`/integracoes/eventos/${id}/reprocessar/`),
}

export const onboardingService = {
  progresso: () => http.get('/onboarding/'),
  concluirTour: (identificador) => http.post(`/onboarding/tours/${identificador}/concluir/`),
  dispensar: (dispensado) => http.post('/onboarding/dispensar/', { dispensado }),
  reiniciar: () => http.post('/onboarding/reiniciar/'),
}

export const ticketsService = {
  ...recurso('tickets'),
  painel: () => http.get('/tickets/painel/'),
  responder: (id, mensagem, visivelAoCliente = true) =>
    http.post(`/tickets/${id}/responder/`, {
      mensagem,
      visivel_ao_cliente: visivelAoCliente,
    }),
  mudarSituacao: (id, dados) => http.patch(`/tickets/${id}/situacao/`, dados),
  reatribuir: (id, analista, motivo = '') =>
    http.post(`/tickets/${id}/reatribuir/`, { analista, motivo }),
}

/**
 * Vitrine e atendimento do site, sem login.
 *
 * O visitante não tem token: estas chamadas passam pelo mesmo cliente HTTP,
 * mas nunca dependem de sessão.
 */
export const candidaturasService = {
  ...recurso('candidaturas'),
  painel: () => http.get('/candidaturas/painel/'),
  conferir: (id, documentoId, aprovado, observacao = '') =>
    http.post(`/candidaturas/${id}/documentos/${documentoId}/conferir/`, {
      aprovado,
      observacao,
    }),
  decidir: (id, status, observacao = '') =>
    http.patch(`/candidaturas/${id}/situacao/`, { status, observacao }),
  gerarContrato: (id, dados) => http.post(`/candidaturas/${id}/gerar-contrato/`, dados),
}

/** Portal do cliente: tudo derivado do cadastro vinculado ao acesso. */
export const portalService = {
  resumo: () => http.get('/meu/resumo/'),
  contratos: () => http.get('/meu/contratos/'),
  cobrancas: (params) => http.get('/meu/cobrancas/', { params }),
  vistorias: () => http.get('/meu/vistorias/'),
  chamados: () => http.get('/meu/chamados/'),
  abrirChamado: (mensagem) => http.post('/meu/chamados/', { mensagem }),
  assinarVistoria: (id) => http.post(`/meu/vistorias/${id}/assinar/`),
  urlContratoPdf: (id) => `/api/v1/meu/contratos/${id}/pdf/`,
}

export const siteService = {
  identidade: (subdominio) => http.get(`/public/${subdominio}/identidade/`),
  catalogo: (subdominio, params) =>
    http.get(`/public/${subdominio}/imoveis/categorias/`, { params }),
  destaques: (subdominio) => http.get(`/public/${subdominio}/imoveis/destaques/`),
  imoveis: (subdominio, params) => http.get(`/public/${subdominio}/imoveis/`, { params }),
  imovel: (subdominio, codigo) => http.get(`/public/${subdominio}/imoveis/${codigo}/`),
  abrirTicket: (subdominio, dados) => http.post(`/public/${subdominio}/tickets/`, dados),
  acompanharTicket: (subdominio, protocolo, contato) =>
    http.get(`/public/${subdominio}/tickets/${protocolo}/`, { params: { contato } }),
  candidatura: (subdominio, token) => http.get(`/public/${subdominio}/candidatura/${token}/`),
  enviarDocumento: (subdominio, token, tipo, arquivo) => {
    const formulario = new FormData()
    formulario.append('tipo', tipo)
    formulario.append('arquivo', arquivo)
    return http.post(`/public/${subdominio}/candidatura/${token}/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
