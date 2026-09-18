import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    // Porta de entrada: o visitante escolhe entre a vitrine e o painel.
    path: '/home',
    name: 'home',
    component: () => import('@/views/EscolhaDeVisaoView.vue'),
    meta: { publico: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { publico: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
      },
      {
        path: 'imoveis',
        name: 'imoveis',
        component: () => import('@/views/imoveis/ImoveisListView.vue'),
      },
      {
        path: 'imoveis/novo',
        name: 'imovel-novo',
        component: () => import('@/views/imoveis/ImovelFormView.vue'),
      },
      {
        path: 'imoveis/:id/editar',
        name: 'imovel-editar',
        component: () => import('@/views/imoveis/ImovelFormView.vue'),
      },
      {
        path: 'imoveis/:id',
        name: 'imovel-detalhe',
        component: () => import('@/views/imoveis/ImovelDetalheView.vue'),
      },
      {
        path: 'pessoas',
        name: 'pessoas',
        component: () => import('@/views/pessoas/PessoasView.vue'),
      },
      {
        path: 'crm',
        name: 'crm',
        component: () => import('@/views/crm/KanbanView.vue'),
        meta: { permissao: 'ver_crm' },
      },
      {
        path: 'crm/leads/:id',
        name: 'lead-detalhe',
        component: () => import('@/views/crm/LeadDetalheView.vue'),
        meta: { permissao: 'ver_crm' },
      },
      {
        path: 'atendimento',
        name: 'atendimento',
        component: () => import('@/views/atendimento/AtendimentoView.vue'),
        meta: { permissao: 'ver_crm' },
      },
      {
        path: 'candidaturas',
        name: 'candidaturas',
        component: () => import('@/views/candidaturas/CandidaturasView.vue'),
      },
      {
        path: 'agenda',
        name: 'agenda',
        component: () => import('@/views/agenda/AgendaView.vue'),
      },
      {
        path: 'contratos',
        name: 'contratos',
        component: () => import('@/views/contratos/ContratosListView.vue'),
      },
      {
        path: 'contratos/novo',
        name: 'contrato-novo',
        component: () => import('@/views/contratos/ContratoFormView.vue'),
      },
      {
        path: 'contratos/:id',
        name: 'contrato-detalhe',
        component: () => import('@/views/contratos/ContratoDetalheView.vue'),
      },
      {
        path: 'financeiro/receber',
        name: 'cobrancas',
        component: () => import('@/views/financeiro/CobrancasView.vue'),
        meta: { permissao: 'ver_financeiro' },
      },
      {
        path: 'financeiro/pagar',
        name: 'repasses',
        component: () => import('@/views/financeiro/RepassesView.vue'),
        meta: { permissao: 'ver_financeiro' },
      },
      {
        path: 'financeiro/comissoes',
        name: 'comissoes',
        component: () => import('@/views/financeiro/ComissoesView.vue'),
      },
      {
        path: 'vistorias',
        name: 'vistorias',
        component: () => import('@/views/vistorias/VistoriasListView.vue'),
      },
      {
        path: 'vistorias/:id',
        name: 'vistoria',
        component: () => import('@/views/vistorias/VistoriaExecucaoView.vue'),
      },
      {
        path: 'relatorios',
        name: 'relatorios',
        component: () => import('@/views/relatorios/RelatoriosView.vue'),
        meta: { permissao: 'ver_financeiro' },
      },
      {
        path: 'configuracoes',
        name: 'configuracoes',
        component: () => import('@/views/configuracoes/ConfiguracoesView.vue'),
        meta: { permissao: 'gerenciar_usuarios' },
      },
    ],
  },
  // Portal do inquilino: mesmo login, outro mundo. Quem entra aqui não opera a
  // imobiliária, então não passa pelo layout do painel.
  {
    path: '/portal',
    name: 'portal',
    component: () => import('@/views/portal/PortalView.vue'),
  },
  // Site do cliente: sem login, sem sessão. É a vitrine que o visitante recebe
  // por link e onde ele pede a visita.
  {
    path: '/site/:subdominio',
    name: 'site-vitrine',
    component: () => import('@/views/site/VitrineView.vue'),
    meta: { publico: true },
  },
  {
    path: '/site/:subdominio/imovel/:codigo',
    name: 'site-imovel',
    component: () => import('@/views/site/ImovelPublicoView.vue'),
    meta: { publico: true },
  },
  {
    path: '/candidatura/:subdominio/:token',
    name: 'site-candidatura',
    component: () => import('@/views/site/CandidaturaView.vue'),
    meta: { publico: true },
  },
  {
    path: '/site/:subdominio/acompanhar',
    name: 'site-acompanhar',
    component: () => import('@/views/site/AcompanhamentoView.vue'),
    meta: { publico: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'nao-encontrado',
    component: () => import('@/views/NaoEncontradoView.vue'),
    meta: { publico: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((para) => {
  const auth = useAuthStore()

  if (!para.meta.publico && !auth.autenticado) {
    return { name: 'login', query: { proximo: para.fullPath } }
  }

  // Cliente com acesso vai para o portal, não para o painel: o painel é da
  // equipe da imobiliária e a API recusaria cada chamada dele.
  const ehCliente = auth.autenticado && auth.pode('usar_portal')
  if (ehCliente && para.name !== 'portal' && !para.meta.publico) {
    return { name: 'portal' }
  }
  if (!ehCliente && para.name === 'portal') {
    return { name: 'dashboard' }
  }

  if (para.name === 'login' && auth.autenticado) {
    return { name: ehCliente ? 'portal' : 'dashboard' }
  }
  // Rota com permissão exigida devolve o usuário ao dashboard em vez de
  // mostrar uma tela que a API recusaria com 403.
  if (para.meta.permissao && !auth.pode(para.meta.permissao)) {
    return { name: 'dashboard' }
  }
  // Sem retorno explícito: o Vue Router entende como "pode seguir".
  return undefined
})

window.addEventListener('sessao-expirada', () => {
  useAuthStore().limpar()
  router.push({ name: 'login' })
})

export default router
