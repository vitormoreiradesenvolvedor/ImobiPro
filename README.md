# ImobiPro

Sistema de gestão imobiliária **Django REST Framework** (API) + **Vue 3** (SPA).
Arquitetura e escopo completos em [`HANDOFF.md`](./HANDOFF.md).

Estado: **Sprints 0 a 9 entregues** captação, CRM com SLA, contratos, locação,
vistorias, financeiro, relatórios e integrações, com o painel completo no front,
mais o **guia de uso gamificado** (tours guiados e missões conferidas no dado real).

## Integrantes do grupo

| Integrante | GitHub |
|---|---|
| Vitor Moreira | [@vitormoreiradesenvolvedor](https://github.com/vitormoreiradesenvolvedor) |
| Andree | [@dree-pdf](https://github.com/dree-pdf) |

Disciplina de Programação WEB, UFLA, 2026/2.

## Fluxo de branches

| Branch | Para que serve |
|---|---|
| `main` | versão avaliada, sempre funcionando |
| `develop` | integração do que está pronto, antes de ir para a `main` |
| `feature/*` | uma frente de trabalho por vez, nasce da `develop` e volta para ela |

## Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Back-end | Django 6, Django REST Framework 3.16, SimpleJWT, Celery, Channels |
| Banco | PostgreSQL 16 |
| Front-end | Vue 3.5, Vite 6, Pinia 3, Vue Router 4, Tailwind CSS 4, Leaflet |
| Administração | Django Admin com tema Unfold, filtros por módulo |
| Documentos | WeasyPrint (contrato, laudo de vistoria, extrato de repasse) |
| Infraestrutura | Docker Compose, Nginx, Redis |
| Qualidade | pytest, Vitest, Playwright, Ruff, Black, ESLint, Prettier, SonarQube |

## Funcionalidades principais

- Autenticação por e-mail e senha, com JWT de acesso curto e renovação em cookie.
- Seis papéis com permissões distintas: superadmin, administrador, gerente,
  corretor, financeiro e inquilino. O corretor não alcança o financeiro nem
  digitando o endereço.
- Carteira de imóveis com fotos, mídia, publicação, busca textual e mapa.
- Funil de vendas com prazo de primeiro contato cobrado pelo sistema.
- Contratos que, ao serem ativados, tiram o imóvel do mercado, geram comissões
  e criam as cobranças do período.
- Financeiro com régua de inadimplência, conciliação por arquivo de retorno,
  repasses e comissões.
- Vistorias com laudo em PDF assinado pelas duas partes.
- Site público por imobiliária: catálogo por categoria, ficha com mapa e pedido
  de visita sem cadastro, que vira ticket com analista e prazo.
- Portal do inquilino: contrato, boletos, chamados de manutenção e assinatura
  de laudo.
- Tema claro e escuro em toda a interface, seguindo o sistema operacional na
  primeira visita e guardando a escolha depois.

## Subir o ambiente

```bash
cp imobipro-api/.env.example imobipro-api/.env   # ajuste SECRET_KEY se quiser
docker compose up --build
```

Portas do host ocupadas? Todas são sobrescrevíveis:

```bash
API_PORT=8010 WS_PORT=8011 WEB_PORT=5174 PROXY_PORT=8081 docker compose up -d
```

Navegue sempre pela porta do `proxy`: front e API na mesma origem é o que faz o
cookie HttpOnly de refresh funcionar.

| Endereço | O que é |
|---|---|
| http://localhost:8080/home | Porta de entrada: escolha entre a vitrine e o painel |
| http://localhost:8080 | Painel da imobiliária |
| http://localhost:8080/site/horizonte | Site público da imobiliária |
| http://localhost:8080/api/docs/ | OpenAPI (Swagger) |
| http://localhost:8080/admin/ | Django admin |
| http://localhost:8080/health/ | Sonda de saúde |

O contêiner `api` roda `migrate` e `semear_operacao` no start. O seed padrão cria só a
imobiliária e a equipe a base nasce **vazia, pronta para dado real**, e o guia
de uso conduz o primeiro cadastro.

Para gerar uma massa de trabalho (carteira, funil, contratos ativos,
cobranças, repasses e vistorias) ou voltar à base limpa depois dela:

```bash
docker compose exec api python manage.py seed_caracteristicas
docker compose exec api python manage.py semear_operacao --completo      # massa de exemplo
docker compose exec api python manage.py limpar_operacao --tenant horizonte             # simula
docker compose exec api python manage.py limpar_operacao --tenant horizonte --confirmar # apaga
```

Para a demonstração (fila de atendimento com prazo correndo, candidatura com
documento recusado e acesso do inquilino ao portal), rode depois do seed:

```bash
docker compose exec -T api python manage.py shell < imobipro-api/cenario_demonstracao.py
```

`limpar_operacao` zera carteira, funil, contratos, financeiro e vistorias, e
preserva a imobiliária, a equipe e o catálogo de características. Sem
`--confirmar` ele só lista o que sairia.

**Atalho de avaliação:** `admin@admin.com` / `admin` entra no painel e no Django
Admin. É credencial fraca de propósito, para quem clona o projeto não precisar
caçar senha. Em instalação real, apague a conta ou troque a senha.

**Contas criadas pelo `semear_operacao`** (senha `horizonte-2026`, troque em produção):

| E-mail | Papel | O que enxerga |
|---|---|---|
| admin@horizonteimoveis.com.br | ADMIN | tudo, inclusive financeiro e configurações |
| gerente@horizonteimoveis.com.br | GERENTE | equipe e funil consolidado |
| corretor@horizonteimoveis.com.br | CORRETOR | a própria carteira e os próprios leads |
| financeiro@horizonteimoveis.com.br | FINANCEIRO | cobranças, repasses e relatórios |
| superadmin@horizonteimoveis.com.br | SUPERADMIN | plataforma (Django admin) |

## Módulos

| Sprint | Módulo | Destaques |
|---|---|---|
| 0 | Infra e autenticação | JWT com refresh em cookie HttpOnly, isolamento multi-tenant, CI |
| 12 | Pessoas e imóveis | wizard de captação, busca por CEP, galeria ordenável, mapa, vitrine pública |
| 34 | CRM | distribuição round-robin, SLA de 15 min, kanban arrastável, visitas, propostas |
| 5 | Contratos | numeração por ano, ativação com validações, comissão congelada, reajuste, rescisão proporcional |
| 6 | Locação | cobrança mensal automática, multa e juros, repasse com retenções, régua de inadimplência |
| 7 | Vistorias | checklist por cômodo, fotos pelo celular, laudo em PDF, comparativo entrada × saída |
| 8 | Financeiro | DRE separando dinheiro de terceiros, estorno, conciliação CNAB, relatórios |
| 9 | Integrações | webhook de portal assinado por HMAC, fila com reprocessamento, sincronização |
| | Guia de uso | tours guiados com coach marks, 12 missões conferidas no dado real, pontos, níveis e trilhas |
| | Site do cliente | catálogo categorizado, ficha com mapa real (OpenStreetMap), banner e vídeo, pedido de visita sem cadastro |
| | Atendimento | ticket com protocolo, analista por rodízio, SLA de 30 min, histórico e nota interna |
| | Candidaturas | documentos enviados por link seguro, conferência item a item, aprovação e contrato gerado |
| | Portal do inquilino | contrato, boletos com Pix, chamados de manutenção e assinatura de laudo |

## Guia de uso (onboarding gamificado)

O botão **🎓 Tutorial**, no topo do painel, mostra quantas missões ainda faltam e
abre o painel do guia. Ele tem duas partes:

- **Tours guiados** o roteiro escurece a tela, ilumina o elemento certo com um
  balão ("Passo 2 de 5") e, nos passos de ação, só avança quando o botão
  destacado é clicado de verdade. São cinco: primeiros passos, captar imóvel,
  funil de vendas, fechar contrato e rodar o financeiro (esse último só para
  quem tem permissão de financeiro).
- **Missões** 12 tarefas agrupadas em cinco trilhas (carteira, comercial,
  contratos, financeiro, vistorias), com pontos e níveis
  (Começando → Aprendiz → Operando → Veterano → Imobiliária no controle). Cada
  missão é conferida no servidor contra o dado real: cadastrar a primeira
  pessoa, publicar um imóvel, mover um lead no funil, ativar um contrato,
  registrar um pagamento, fechar uma vistoria e assim por diante.

Ao salvar algo que cumpre uma missão, a comemoração ("Missão cumprida!") aparece
sozinha e o contador cai na hora sem recarregar a página. Cada usuário tem seu
próprio progresso; **Reiniciar** reabre o guia do zero e **Não sugerir** silencia
a abertura automática. Nada disso toca os dados da operação.

## Testes e qualidade

```bash
# Backend: lint, formatação e testes com cobertura
docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test \
  api sh -c "ruff check . && black --check apps config && pytest"

# Frontend: lint, unitários e build
cd imobipro-web && npm run lint && npx vitest run --coverage && npm run build

# End-to-end (stack de pé): navega todas as telas em Chromium
cd imobipro-web && npx playwright test

# Só a varredura funcional ponta a ponta (35 etapas, com screenshot de cada uma)
cd imobipro-web && npx playwright test tests/e2e/varredura.spec.js
```

As suítes E2E são três:

| Arquivo | O que cobre |
|---|---|
| `navegacao.spec.js` | todas as telas, permissões por papel, responsividade, estado vazio |
| `onboarding.spec.js` | tutorial que abre sozinho, passos, painel de missões, comemoração |
| `varredura.spec.js` | a operação inteira pela interface: captação → funil → contrato → cobrança → repasse → vistoria → relatórios, incluindo os cinco tutoriais e um teste final que falha se **qualquer** erro de JavaScript tiver aparecido no caminho |
| `cliente.spec.js` | a jornada do cliente: vitrine → pedido de visita sem cadastro → atendimento → candidatura com documentos → contrato → portal do inquilino |

A varredura roda com um único worker e zera a operação antes de começar: ela
cria o próprio cenário pela tela, do jeito que um usuário criaria.

Antes de considerar qualquer funcionalidade pronta, vale o portão de aceite
descrito na seção 11 do `HANDOFF.md`: clique em todo elemento interativo,
navegação só por teclado, sete resoluções, entrada adversarial nos campos
(emoji em campo numérico, valores de fronteira, arquivo com extensão trocada),
permissão testada por requisição e zero erro de JavaScript no console. Item sem
evidência conta como falha.

Resultado atual:

| Verificação | Resultado |
|---|---|
| Testes de backend | 324 passando · cobertura 86,2% |
| Testes de frontend | 175 passando · cobertura 88% |
| End-to-end (Playwright) | 90 passando · screenshots em `imobipro-web/tests/e2e/telas/` |
| SonarQube | 0 bugs · 0 vulnerabilidades · 0 hotspots · 0 code smells · Quality Gate **OK** (última análise antes das mudanças de agosto) |
| Confiabilidade / Segurança / Manutenibilidade | A / A / A |
| Cobertura medida pelo Sonar · duplicação | 85,7% · 1,4% |

### SonarQube

```bash
docker compose -f docker-compose.qualidade.yml up -d sonarqube   # http://localhost:9000
export SONAR_TOKEN=<token de análise>
./scripts/qualidade.sh                                           # lint + testes + scanner
```

O perfil de JavaScript usado é o `Sonar way` com um único ajuste: a regra de
nomenclatura de parâmetro de `catch` (S7718) aceita `erro` e `falha`, porque o
código é escrito em português o parâmetro `ignore` da regra existe para isso.

Duas ocorrências de `Web:S6840` (atributo `autocomplete`) estão marcadas como
aceitas: o atributo fica em `<BaseInput>`, componente Vue que repassa `$attrs`
para um `<input>` real o analisador de HTML não enxerga o componente.

O SonarQube não emite “nota em %”: o equivalente a uma avaliação máxima é o que
está na tabela acima nota **A** nos três eixos, zero problema aberto e o
Quality Gate aprovado.

## Material comercial

| Peça | Onde | Como refazer |
|---|---|---|
| Vídeo de apresentação (9min55s, 1080p, com locução e trilha) | `imobipro-web/midia/imobipro-apresentacao.mp4` | `node scripts/gravar-demo.mjs --ensaio && node scripts/gravar-demo.mjs && node scripts/montar-demo.mjs` |
| Legenda sincronizada | `imobipro-web/midia/imobipro-apresentacao.srt` | gerada junto com o vídeo |
| Roteiro de locução | `imobipro-web/midia/roteiro-locucao.md` | gerado junto com o vídeo |
| Capturas em alta | `imobipro-web/midia/telas-comerciais/` | `node scripts/telas-comerciais.mjs` |
| Deck comercial (27 slides) | `docs/comercial/deck-comercial.html` e `.pdf` | `python3 docs/comercial/fonte/gerar_deck.py` e `node imobipro-web/scripts/deck-pdf.mjs` |
| Fotos de imóveis | procedência em `docs/comercial/creditos-imagens.md` | `python3 docs/comercial/fonte/baixar-fotos.py <pasta>` |
| Voz e trilha do vídeo | `imobipro-web/midia/voz/` e `midia/trilha/` | `node scripts/baixar-midia-livre.mjs` |

O vídeo é gravado navegando no sistema de verdade, contra a API: nenhum número
é montado na edição. Antes de gravar, carregue a massa de exemplo
(`semear_operacao --completo`) e devolva a base ao estado limpo depois com
`limpar_operacao --confirmar`.

**Locução e trilha.** A narração é sintetizada na máquina, e a trilha é uma
faixa CC0 do Freesound. Dois motores de voz, nesta ordem:

| Motor | Licença | Onde roda | Quando entra |
|---|---|---|---|
| [Chatterbox](https://github.com/resemble-ai/chatterbox) (checkpoint pt-BR dedicado) | MIT | GPU, ambiente próprio em `~/.cache/imobipro-tts` | padrão, é a voz que soa natural |
| [Piper](https://github.com/rhasspy/piper) `pt_BR-faber-medium` | MIT | qualquer CPU | reserva, quando não há GPU ou ambiente preparado |

Uma vez, antes da primeira gravação:

```bash
python3 -m pip install --user piper-tts   # voz reserva
cd imobipro-web && node scripts/baixar-midia-livre.mjs
```

O script monta o ambiente do Chatterbox sozinho se o [uv](https://docs.astral.sh/uv/)
estiver instalado (são alguns GB de torch com CUDA, só na primeira vez). O
modelo fica vivo em um processo durante a gravação, porque carregá-lo por fala
custaria mais que gravar o vídeo inteiro.

A gravação é feita em duas passadas. A primeira (`--ensaio`) percorre o roteiro
sem gravar, só para sintetizar as falas: carregar o modelo durante a gravação
deixa a tela parada e abre buracos de vinte segundos no vídeo. A segunda grava
com o áudio pronto em cache.

O tempo de cada cena vem da duração real da locução, então voz, legenda e tela
contam a mesma coisa. Sem nenhum motor instalado, o vídeo sai mudo e com os
tempos estimados do roteiro.

A trilha é *Corporate company introduction video*, de Bertsz, CC0. A
procedência fica em `imobipro-web/midia/trilha/CREDITOS.md`, gerada pelo próprio
script de preparo. A captura do portal do inquilino para os slides precisa da
senha do acesso: `SENHA_INQUILINO=... node scripts/telas-comerciais.mjs`.

O texto dos slides fica em `docs/comercial/fonte/slides.py`, separado do
gerador: o time comercial edita lá e roda o script para publicar a versão nova.

As fotos dos imóveis na demonstração são fotografias reais de licença livre (CC0
e domínio público), baixadas pelo Openverse. Numa apresentação para um cliente,
troque pelas fotos da carteira dele.

## Estrutura

```
imobipro-api/          Django + DRF + Celery + Channels
  config/              settings por ambiente, urls, asgi/wsgi, celery (beat)
  apps/core/           BaseModel, TenantMiddleware, money, auditoria, PDF
  apps/accounts/       Tenant, Usuario, JWT, permissões por papel
  apps/pessoas/        Pessoa, Endereço, consulta de CEP
  apps/imoveis/        Imóvel, fotos, publicação, busca textual e por raio
  apps/crm/            Lead, interações, visitas, propostas, SLA
  apps/contratos/      Contrato, partes, comissões, reajuste, rescisão
  apps/locacao/        Cobrança, repasse, régua de inadimplência
  apps/vistorias/      Vistoria, itens, laudo, comparativo
  apps/financeiro/     Transação, DRE, conciliação CNAB, relatórios
  apps/integracoes/    Portais, webhook HMAC, fila de saída
  apps/notificacoes/   Notificação e WebSocket
  apps/onboarding/     missões, trilhas, pontos e níveis do guia de uso
  apps/atendimento/    ticket do site, SLA de resposta, agenda da visita
  apps/candidaturas/   documentos do pretendente, análise e virada para contrato
  apps/portal/         rotas /meu/ do inquilino: contrato, boletos, chamados
imobipro-web/          Vue 3 + Vite + Pinia + Tailwind 4
  src/components/base/ design system (botão, campo, tabela, modal, toast)
  src/components/onboarding/  spotlight, balão do tour, painel de missões
  src/composables/     listagem paginada, toast, confirmação
  src/onboarding/      roteiro dos tours guiados (passos e alvos)
  tests/unit/          132 testes de componente e store
  tests/e2e/           39 testes de navegação em Chromium
nginx/dev.conf         borda de desenvolvimento (origem única)
scripts/qualidade.sh   pipeline local de qualidade
```

## Tema claro e escuro

A troca não duplica folha de estilo nem espalha variante `dark:` pelas telas: o
atributo `data-tema` no `<html>` redefine os tokens de cor que o Tailwind já
consome, então `bg-slate-50` e `text-slate-900` passam a apontar para a escala
invertida e a interface inteira vira de uma vez. Tela nova nasce nos dois temas
sem trabalho extra.

Trechos que já nascem escuros (menu lateral, faixa da marca, véu de modal e
avisos) carregam a classe `paleta-fixa`, que restaura a escala original: sem
isso, inverter de novo deixaria texto branco sobre fundo branco.

Na primeira visita vale a preferência do sistema operacional; depois, a escolha
do usuário, guardada no navegador. O tema é aplicado por um script no
`index.html` antes da primeira pintura, para a tela não piscar branca.

## Decisões que valem saber antes de mexer

- **Isolamento por tenant é infraestrutura.** Toda ViewSet herda
  `TenantQuerySetMixin` e ganha teste em `apps/core/tests/test_isolamento_tenant.py`.
- **Refresh token só existe em cookie HttpOnly**; o access fica em memória, nunca
  em `localStorage`. O `localStorage` guarda apenas um marcador de "já houve
  login" para não disparar refresh em visita anônima.
- **Dinheiro passa por `apps/core/money.py`** `Decimal`, `ROUND_HALF_EVEN` e
  rateio que fecha no centavo.
- **Regra de negócio mora em `services.py`**, chamada tanto pela view quanto
  pela task Celery.
- **Duas locações ativas sobrepostas no mesmo imóvel são barradas pelo banco**
  (`ExclusionConstraint` + `btree_gist`), não só pela aplicação.
- **Transação financeira nunca é deletada**: estorna com lançamento de contrapartida.
- **Cada limite de requisição tem balde próprio.** Login, renovação de sessão e
  recuperação de senha não passam pelo balde anônimo global: navegar pela vitrine
  pública (ou uma bateria de testes) não pode trancar a equipe para fora do
  sistema. Os limites vêm de `THROTTLE_LOGIN`, `THROTTLE_REFRESH`, `THROTTLE_ANON`
  e `THROTTLE_USER`; o padrão de produção é 5 tentativas de login por minuto e o
  `.env` local afrouxa para caber a suíte E2E.
- **`NUM_PROXIES` diz quantos proxies existem na frente da API** (nginx = 1, CDN
  mais nginx = 2). Sem isso, todo visitante chega com o endereço do proxy e um
  único usuário consome o limite de todos.
- **Sessão do cliente HTTP é versionada.** Uma resposta 401 atrasada, de antes
  de um logout ou troca de usuário, não derruba a sessão nova
  (`imobipro-web/src/services/http.js`).
- **Toda cobrança nasce com "nosso número"** sem ele o retorno CNAB do banco
  não teria como casar a baixa.
- **Ativar, rescindir ou encerrar contrato relê o registro antes de responder**:
  a instância carregada com prefetch devolveria as comissões desatualizadas.
- **Percentual digitado com vírgula é convertido antes de ir para a API**
  (`decimalParaApi`): "4,5" é como o brasileiro escreve, e o DRF só aceita "4.5".
- **Cliente com login não entra no painel.** A permissão padrão da API exige
  papel interno; inquilino e proprietário só alcançam as rotas `/meu/`, sempre
  filtradas pela pessoa vinculada ao acesso. Sem essa barreira, estar
  autenticado no mesmo tenant daria acesso à carteira inteira.
- **O pretendente não tem conta.** Ele acompanha o pedido por protocolo mais o
  contato usado na abertura, e envia documentos por um link com token longo.
  Protocolo sozinho não abre histórico: número sequencial é fácil de adivinhar.
- **A candidatura só vira contrato depois da conferência item a item.** O
  sistema recusa a aprovação enquanto houver documento faltando, recusado ou
  sem conferir, e o cadastro da pessoa nasce com o CPF normalizado.
- **O mapa da vitrine usa OpenStreetMap e a geocodificação é do Nominatim**,
  serviços abertos e sem chave. A busca é estruturada (rua, cidade, estado)
  porque a busca livre erra com endereço brasileiro, e cai para rua sem número
  e depois bairro antes de desistir.
- **Missão do guia nunca é marcada no cliente.** O backend confere cada uma
  contra o dado real (`apps/onboarding/missoes.py`); o front só desenha o
  progresso que a API devolve. Quem "pulou" o tutorial e fez o trabalho direto
  aparece com as missões cumpridas do mesmo jeito.

## Rotinas agendadas (Celery Beat)

| Tarefa | Quando |
|---|---|
| Vigilância do SLA de atendimento | a cada 5 min |
| Sincronização com portais | a cada 30 min |
| Geração das cobranças do mês (D-10) | diária, 02:00 |
| Reajustes anuais | diária, 03:00 |
| Régua de inadimplência (D+1, D+5, D+15, D+30) | diária, 08:00 |
| Aviso de contrato a vencer (90/60/30 dias) | diária, 08:30 |
