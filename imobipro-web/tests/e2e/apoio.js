import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Apoio dos testes de ponta a ponta.
 *
 * A base de trabalho fica vazia (é para dado real), então cada suíte que
 * precisa de conteúdo monta o seu pela API e apaga no fim. Assim os testes não
 * dependem da massa inicial nem deixam sujeira no sistema.
 */

export const CREDENCIAIS = {
  admin: { email: 'admin@horizonteimoveis.com.br', senha: 'horizonte-2026' },
  corretor: { email: 'corretor@horizonteimoveis.com.br', senha: 'horizonte-2026' },
  financeiro: { email: 'financeiro@horizonteimoveis.com.br', senha: 'horizonte-2026' },
}

// PNG 1x1: o bastante para o upload de foto passar pela validação de imagem.
export const PNG_MINIMO = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

// Marca tudo que a suíte cria, para a limpeza saber o que é dela.
export const MARCA_TESTE = 'E2E'

export async function autenticar(request, baseURL, quem = 'admin') {
  const { email, senha } = CREDENCIAIS[quem]
  const resposta = await request.post(`${baseURL}/api/v1/auth/login/`, {
    data: { email, password: senha },
  })
  const { access } = await resposta.json()
  return { Authorization: `Bearer ${access}` }
}

/**
 * Desliga a sugestão automática do tutorial.
 *
 * O guia abre sozinho no primeiro acesso e cobre a tela comportamento
 * desejado do produto, mas que atrapalha os testes de navegação.
 */
export async function silenciarGuia(request, baseURL, papeis = Object.keys(CREDENCIAIS)) {
  for (const papel of papeis) {
    const headers = await autenticar(request, baseURL, papel)
    await request.post(`${baseURL}/api/v1/onboarding/dispensar/`, {
      headers,
      data: { dispensado: true },
    })
  }
}

export async function reativarGuia(request, baseURL, papeis = Object.keys(CREDENCIAIS)) {
  for (const papel of papeis) {
    const headers = await autenticar(request, baseURL, papel)
    await request.post(`${baseURL}/api/v1/onboarding/reiniciar/`, { headers })
  }
}

/** Monta uma carteira mínima porém completa: imóvel no ar, lead e contrato ativo. */
export async function montarCarteira(request, baseURL) {
  const headers = await autenticar(request, baseURL)
  const json = async (resposta) => {
    if (!resposta.ok()) {
      throw new Error(`${resposta.status()} em ${resposta.url()}: ${await resposta.text()}`)
    }
    return resposta.json()
  }

  const proprietario = await json(
    await request.post(`${baseURL}/api/v1/pessoas/`, {
      headers,
      data: {
        tipo: 'FISICA',
        nome: `Proprietário ${MARCA_TESTE}`,
        cpf_cnpj: '529.982.247-25',
        telefone: '35998880001',
      },
    }),
  )

  const inquilino = await json(
    await request.post(`${baseURL}/api/v1/pessoas/`, {
      headers,
      data: {
        tipo: 'FISICA',
        nome: `Inquilino ${MARCA_TESTE}`,
        cpf_cnpj: '111.444.777-35',
        telefone: '35998880002',
      },
    }),
  )

  const imovel = await json(
    await request.post(`${baseURL}/api/v1/imoveis/`, {
      headers,
      data: {
        titulo: `Apartamento de teste ${MARCA_TESTE}`,
        descricao: 'Imóvel criado pela suíte automatizada.',
        tipo: 'APARTAMENTO',
        finalidade: 'LOCACAO',
        proprietario: proprietario.id,
        quartos: 2,
        banheiros: 1,
        vagas: 1,
        area_util: '68.00',
        valor_locacao: '2500.00',
        valor_condominio: '480.00',
        valor_iptu_anual: '1200.00',
        matricula: '98765',
        endereco: {
          logradouro: 'Rua de Teste',
          numero: '100',
          bairro: 'Centro',
          cidade: 'Lavras',
          uf: 'MG',
          latitude: '-21.245000',
          longitude: '-44.999000',
        },
      },
    }),
  )

  // Publicar exige cinco fotos: é a regra de negócio, não um detalhe do teste.
  // Uma requisição por foto o multipart do Playwright não repete a chave.
  for (let indice = 0; indice < 5; indice += 1) {
    await request.post(`${baseURL}/api/v1/imoveis/${imovel.id}/fotos/`, {
      headers,
      multipart: {
        arquivo: {
          name: `foto-${indice}.png`,
          mimeType: 'image/png',
          buffer: PNG_MINIMO,
        },
      },
    })
  }
  await request.post(`${baseURL}/api/v1/imoveis/${imovel.id}/publicar/`, { headers })

  const lead = await json(
    await request.post(`${baseURL}/api/v1/leads/`, {
      headers,
      data: {
        nome: `Interessado ${MARCA_TESTE}`,
        email: 'interessado@cliente.test',
        telefone: '35991112222',
        origem: 'SITE',
        imovel_interesse: imovel.id,
        valor_estimado: '350000.00',
      },
    }),
  )

  const hoje = new Date()
  const fim = new Date(hoje.getTime() + 900 * 24 * 60 * 60 * 1000)
  const contrato = await json(
    await request.post(`${baseURL}/api/v1/contratos/`, {
      headers,
      data: {
        tipo: 'LOCACAO',
        imovel: imovel.id,
        data_inicio: hoje.toISOString().slice(0, 10),
        data_fim: fim.toISOString().slice(0, 10),
        valor: '2500.00',
        dia_vencimento: 10,
        taxa_administracao_percent: '8.00',
        taxa_intermediacao: '2500.00',
      },
    }),
  )

  for (const [pessoa, papel] of [
    [proprietario.id, 'LOCADOR'],
    [inquilino.id, 'LOCATARIO'],
  ]) {
    await request.post(`${baseURL}/api/v1/contratos/${contrato.id}/partes/`, {
      headers,
      data: { pessoa, papel, percentual: 100 },
    })
  }

  // Ativar gera comissões, cobranças e tira o imóvel do mercado.
  await request.post(`${baseURL}/api/v1/contratos/${contrato.id}/ativar/`, { headers })

  return { proprietario, inquilino, imovel, lead, contrato }
}

/** Apaga tudo que `montarCarteira` criou, na ordem que as dependências exigem. */
export async function limparCarteira(request, baseURL) {
  const headers = await autenticar(request, baseURL)

  for (const recurso of ['contratos', 'leads', 'imoveis', 'pessoas']) {
    const lista = await request.get(`${baseURL}/api/v1/${recurso}/?page_size=100`, {
      headers,
    })
    for (const item of (await lista.json()).results ?? []) {
      await request.delete(`${baseURL}/api/v1/${recurso}/${item.id}/`, { headers })
    }
  }
}

export async function entrar(page, quem = 'admin') {
  const { email, senha } = CREDENCIAIS[quem]
  await page.goto('/login')
  await page.getByLabel('E-mail').fill(email)
  await page.getByLabel('Senha').fill(senha)
  await page.getByRole('button', { name: 'Entrar' }).click()
}

/**
 * Zera a operação da imobiliária de verdade (apaga histórico e registros
 * removidos, que a API só marca como excluídos).
 *
 * A suíte do guia conta missões pendentes: qualquer resíduo de outra suíte
 * marcaria missões como cumpridas e mudaria os números esperados.
 */
export function zerarOperacao(tenant = 'horizonte') {
  const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
  execFileSync(
    'docker',
    [
      'compose',
      'exec',
      '-T',
      'api',
      'python',
      'manage.py',
      'limpar_operacao',
      '--tenant',
      tenant,
      '--confirmar',
    ],
    { cwd: raiz, stdio: 'pipe' },
  )
}

/** Apaga a imobiliária criada pelo teste de cadastre-se, com a equipe dela. */
export function apagarImobiliaria(subdominio) {
  const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
  execFileSync(
    'docker',
    [
      'compose',
      'exec',
      '-T',
      'api',
      'python',
      'manage.py',
      'shell',
      '-c',
      `from apps.accounts.models import Tenant; Tenant.objects.filter(subdominio=${JSON.stringify(subdominio)}).delete()`,
    ],
    { cwd: raiz, stdio: 'pipe' },
  )
}
