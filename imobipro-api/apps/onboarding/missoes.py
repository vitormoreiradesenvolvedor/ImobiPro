"""Catálogo de missões do onboarding.

Cada missão é conferida contra o dado real da imobiliária não existe "marcar
como concluída" pelo front. Assim o progresso reflete o sistema realmente em
uso, e não cliques no tutorial.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from apps.accounts.models import Papel


@dataclass(frozen=True)
class Missao:
    chave: str
    titulo: str
    descricao: str
    dica: str
    trilha: str
    rota: str
    pontos: int
    verificar: Callable
    # Papéis que enxergam a missão; vazio = todos os papéis internos.
    papeis: tuple = field(default_factory=tuple)


# ------------------------------------------------------------- verificadores


def _tem_pessoa(tenant):
    from apps.pessoas.models import Pessoa

    return Pessoa.objects.filter(tenant=tenant, deletado_em__isnull=True).exists()


def _tem_imovel(tenant):
    from apps.imoveis.models import Imovel

    return Imovel.objects.filter(tenant=tenant, deletado_em__isnull=True).exists()


def _tem_imovel_publicado(tenant):
    """Já publicou alguma vez e não "está publicado agora".

    Um imóvel alugado sai do ar automaticamente; olhar só o estado atual faria
    a missão regredir justamente quando a imobiliária fechou negócio.
    """

    from apps.imoveis.models import HistoricoImovel, Imovel, TipoEventoImovel

    if Imovel.objects.filter(
        tenant=tenant, publicado_site=True, deletado_em__isnull=True
    ).exists():
        return True

    return HistoricoImovel.objects.filter(
        imovel__tenant=tenant, tipo=TipoEventoImovel.PUBLICACAO
    ).exists()


def _tem_lead(tenant):
    from apps.crm.models import Lead

    return Lead.objects.filter(tenant=tenant).exists()


def _tem_primeiro_contato(tenant):
    from apps.crm.models import Lead

    return Lead.objects.filter(tenant=tenant, primeiro_contato_em__isnull=False).exists()


def _tem_visita(tenant):
    from apps.crm.models import Visita

    return Visita.objects.filter(tenant=tenant).exists()


def _tem_proposta(tenant):
    from apps.crm.models import Proposta

    return Proposta.objects.filter(tenant=tenant).exists()


def _tem_contrato(tenant):
    from apps.contratos.models import Contrato

    return Contrato.objects.filter(tenant=tenant, deletado_em__isnull=True).exists()


def _tem_contrato_ativo(tenant):
    from apps.contratos.models import Contrato, StatusContrato

    return Contrato.objects.filter(tenant=tenant, status=StatusContrato.ATIVO).exists()


def _tem_cobranca_paga(tenant):
    from apps.locacao.models import Cobranca, StatusCobranca

    return Cobranca.objects.filter(tenant=tenant, status=StatusCobranca.PAGA).exists()


def _tem_repasse_pago(tenant):
    from apps.locacao.models import Repasse, StatusRepasse

    return Repasse.objects.filter(tenant=tenant, status=StatusRepasse.PAGO).exists()


def _tem_vistoria_finalizada(tenant):
    from apps.vistorias.models import StatusVistoria, Vistoria

    return Vistoria.objects.filter(tenant=tenant, status=StatusVistoria.FINALIZADA).exists()


# ------------------------------------------------------------------ catálogo

GESTAO_E_FINANCEIRO = (Papel.ADMIN, Papel.FINANCEIRO, Papel.SUPERADMIN)

MISSOES = [
    Missao(
        chave="cadastrar_pessoa",
        titulo="Cadastre o primeiro proprietário",
        descricao="Todo imóvel precisa de um dono no sistema antes de ser captado.",
        dica="Em Pessoas, clique em 'Nova pessoa'. O CPF/CNPJ é validado por "
        "dígito verificador e o CEP preenche o endereço sozinho.",
        trilha="carteira",
        rota="/pessoas",
        pontos=10,
        verificar=_tem_pessoa,
    ),
    Missao(
        chave="captar_imovel",
        titulo="Capte o primeiro imóvel",
        descricao="O cadastro é um assistente de 5 passos e gera o código REF automático.",
        dica="Em Imóveis, clique em 'Captar imóvel'. Preencha latitude e "
        "longitude no passo de endereço: sem elas o imóvel não vai ao ar.",
        trilha="carteira",
        rota="/imoveis/novo",
        pontos=15,
        verificar=_tem_imovel,
    ),
    Missao(
        chave="publicar_imovel",
        titulo="Publique o imóvel no site",
        descricao="A publicação só libera quando o cadastro está completo de verdade.",
        dica="Abra a ficha do imóvel, envie 5 fotos na aba 'Fotos e mídia' e "
        "clique em 'Publicar'. O sistema lista o que ainda falta.",
        trilha="carteira",
        rota="/imoveis",
        pontos=20,
        verificar=_tem_imovel_publicado,
    ),
    Missao(
        chave="receber_lead",
        titulo="Registre o primeiro lead",
        descricao="O lead é distribuído automaticamente para um corretor ativo.",
        dica="No Funil de vendas, clique em 'Novo lead'. Leads do site e dos "
        "portais entram aqui sozinhos.",
        trilha="comercial",
        rota="/crm",
        pontos=10,
        verificar=_tem_lead,
    ),
    Missao(
        chave="cumprir_sla",
        titulo="Faça o primeiro contato dentro do SLA",
        descricao="São 15 minutos para falar com o lead; depois disso ele volta "
        "para a fila.",
        dica="Abra o lead e registre uma interação (ligação, WhatsApp ou "
        "e-mail). O cronômetro do SLA para nesse momento.",
        trilha="comercial",
        rota="/crm",
        pontos=15,
        verificar=_tem_primeiro_contato,
    ),
    Missao(
        chave="agendar_visita",
        titulo="Agende uma visita",
        descricao="A visita move o lead no funil e aparece na agenda do corretor.",
        dica="Na ficha do lead, use 'Agendar visita'. Depois registre o "
        "feedback ele também move o cartão no kanban.",
        trilha="comercial",
        rota="/crm",
        pontos=15,
        verificar=_tem_visita,
    ),
    Missao(
        chave="registrar_proposta",
        titulo="Registre uma proposta",
        descricao="Aceitar a proposta reserva o imóvel e recusa as concorrentes.",
        dica="Na ficha do lead, clique em 'Nova proposta'. O sistema calcula o "
        "desconto em relação ao valor anunciado.",
        trilha="comercial",
        rota="/crm",
        pontos=15,
        verificar=_tem_proposta,
    ),
    Missao(
        chave="montar_contrato",
        titulo="Monte um contrato",
        descricao="O contrato nasce como rascunho e só vale depois de assinado.",
        dica="Em Contratos, clique em 'Novo contrato'. Locação exige locador, "
        "locatário e data de término.",
        trilha="contratos",
        rota="/contratos/novo",
        pontos=20,
        verificar=_tem_contrato,
    ),
    Missao(
        chave="ativar_contrato",
        titulo="Ative o contrato assinado",
        descricao="A ativação tira o imóvel do mercado, gera comissões e as cobranças.",
        dica="Abra o contrato e clique em 'Ativar contrato'. Se faltar algo, a "
        "tela lista as pendências antes de deixar ativar.",
        trilha="contratos",
        rota="/contratos",
        pontos=25,
        verificar=_tem_contrato_ativo,
    ),
    Missao(
        chave="dar_baixa",
        titulo="Receba um aluguel",
        descricao="A baixa calcula multa e juros e gera o repasse ao proprietário.",
        dica="Em Contas a receber, clique em 'Dar baixa' na cobrança. Para "
        "boleto, o arquivo de retorno do banco faz isso em lote.",
        trilha="financeiro",
        rota="/financeiro/receber",
        pontos=20,
        verificar=_tem_cobranca_paga,
        papeis=GESTAO_E_FINANCEIRO,
    ),
    Missao(
        chave="liquidar_repasse",
        titulo="Repasse ao proprietário",
        descricao="Aluguel menos taxa de administração e retenções, com extrato em PDF.",
        dica="Em Repasses, confira o líquido e clique em 'Liquidar'. Condomínio "
        "e IPTU não entram na base são de terceiros.",
        trilha="financeiro",
        rota="/financeiro/pagar",
        pontos=20,
        verificar=_tem_repasse_pago,
        papeis=GESTAO_E_FINANCEIRO,
    ),
    Missao(
        chave="fazer_vistoria",
        titulo="Faça a vistoria de entrada",
        descricao="É ela que sustenta a retenção de caução na saída do inquilino.",
        dica="Na ficha do contrato, clique em 'Vistoria de entrada'. O "
        "checklist já vem pronto; marque o estado e anexe fotos pelo celular.",
        trilha="vistorias",
        rota="/vistorias",
        pontos=20,
        verificar=_tem_vistoria_finalizada,
    ),
]

TRILHAS = {
    "carteira": {"nome": "Montar a carteira", "icone": "⌂"},
    "comercial": {"nome": "Vender e alugar", "icone": "◈"},
    "contratos": {"nome": "Fechar contratos", "icone": "✎"},
    "financeiro": {"nome": "Rodar o financeiro", "icone": "₿"},
    "vistorias": {"nome": "Proteger o imóvel", "icone": "☑"},
}

# Faixas de reconhecimento por pontuação acumulada.
NIVEIS = [
    (0, "Começando"),
    (25, "Aprendiz"),
    (70, "Operando"),
    (130, "Veterano"),
    (205, "Imobiliária no controle"),
]


def missoes_do_papel(papel):
    return [m for m in MISSOES if not m.papeis or papel in m.papeis]


def nivel_para(pontos: int) -> str:
    atual = NIVEIS[0][1]
    for minimo, nome in NIVEIS:
        if pontos >= minimo:
            atual = nome
    return atual
