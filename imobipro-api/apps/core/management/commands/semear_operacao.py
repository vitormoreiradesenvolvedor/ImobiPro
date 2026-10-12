"""Massa inicial: imobiliária, equipe e com --completo a operação inteira.

Sem `--completo` cria só o mínimo para o login funcionar. Com a flag, monta um
mês de operação: carteira, funil, contratos ativos, cobranças, repasses e
vistorias o suficiente para validar todas as telas com dado de verdade.
"""

from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from apps.accounts.models import Papel, Plano, Tenant, Usuario

SENHA_PADRAO = "horizonte-2026"

# Atalho de demonstração: entra no painel e no Django Admin com admin/admin.
# Credencial fraca de propósito, para a avaliação e para quem clona o projeto.
# Em instalação real, apague esta conta ou troque a senha no primeiro acesso.
ATALHO_ADMIN = ("admin@admin.com", "admin", "Administrador da Demonstração")

EQUIPE = [
    ("admin@horizonteimoveis.com.br", "Ana Ribeiro", Papel.ADMIN),
    ("gerente@horizonteimoveis.com.br", "Bruno Carvalho", Papel.GERENTE),
    ("corretor@horizonteimoveis.com.br", "Carla Dias", Papel.CORRETOR),
    ("corretor2@horizonteimoveis.com.br", "Eduardo Lima", Papel.CORRETOR),
    ("financeiro@horizonteimoveis.com.br", "Diego Souza", Papel.FINANCEIRO),
]

PROPRIETARIOS = [
    ("Helena Martins Prado", "52998224725", "35998880001"),
    ("Roberto Alves Cunha", "11144477735", "35998880002"),
    ("Construtora Vale Verde Ltda", "11222333000181", "3533330001"),
    ("Marina Figueiredo", "39053344705", "35998880004"),
]

INQUILINOS = [
    ("Paulo Henrique Souza", "12345678909", "35997770001"),
    ("Juliana Campos", "88350041502", "35997770002"),
    ("Rafael Nogueira", "19100000000", "35997770003"),
]

# Bairros de Lavras/MG com coordenadas reais para o mapa ficar coerente.
BAIRROS = [
    ("Centro", -21.2450, -44.9990),
    ("Jardim Floresta", -21.2380, -45.0080),
    ("Vila Ester", -21.2520, -44.9930),
    ("Aquenta Sol", -21.2300, -44.9880),
    ("Jardim Glória", -21.2560, -45.0050),
]

IMOVEIS = [
    (
        "Apartamento 2 quartos no Centro",
        "APARTAMENTO",
        "LOCACAO",
        2,
        1,
        1,
        68,
        None,
        2500,
        480,
    ),
    (
        "Cobertura duplex com vista livre",
        "COBERTURA",
        "VENDA",
        3,
        2,
        2,
        180,
        890000,
        None,
        950,
    ),
    (
        "Casa em condomínio fechado",
        "CASA_CONDOMINIO",
        "VENDA",
        4,
        3,
        3,
        260,
        1250000,
        None,
        620,
    ),
    ("Kitnet mobiliada perto da UFLA", "KITNET", "LOCACAO", 1, 1, 0, 32, None, 1200, 0),
    (
        "Sala comercial no eixo bancário",
        "SALA_COMERCIAL",
        "LOCACAO",
        0,
        1,
        1,
        45,
        None,
        2200,
        380,
    ),
    ("Casa térrea com quintal", "CASA", "VENDA_E_LOCACAO", 3, 2, 2, 140, 620000, 3200, 0),
    (
        "Apartamento reformado 3 quartos",
        "APARTAMENTO",
        "LOCACAO",
        3,
        2,
        1,
        92,
        None,
        3400,
        520,
    ),
    ("Terreno plano de 360 m²", "TERRENO", "VENDA", 0, 0, 0, 360, 380000, None, 0),
]

ORIGENS = ["SITE", "PORTAL", "TELEFONE", "WHATSAPP", "INDICACAO", "PLACA"]
ESTAGIOS = [
    "NOVO",
    "EM_CONTATO",
    "QUALIFICADO",
    "VISITA_AGENDADA",
    "VISITA_REALIZADA",
    "PROPOSTA",
    "NEGOCIACAO",
]

DESCRICAO_PADRAO = (
    "Imóvel com boa ventilação, sol da manhã e acabamento em porcelanato. "
    "Documentação em ordem e pronto para transferência."
)

NOMES_LEADS = [
    "Fernanda Rocha",
    "Thiago Barbosa",
    "Camila Duarte",
    "Lucas Pereira",
    "Beatriz Antunes",
    "Gustavo Moreira",
    "Larissa Teixeira",
    "André Villela",
    "Patrícia Gomes",
    "Rodrigo Ferraz",
    "Isabela Monteiro",
    "Vinícius Braga",
]


# Fotos livres (CC0) que acompanham o repositório: cinco ambientes por imóvel,
# que é também o mínimo exigido para publicar um imóvel no site.
PASTA_FOTOS = Path(__file__).resolve().parents[2] / "seed" / "fotos"
AMBIENTES = ["fachada", "sala", "quarto", "cozinha", "banheiro"]


def foto_real(imovel_indice, posicao):
    """Foto de imóvel de verdade, quando o pacote está no repositório.

    Retângulo cinza no lugar da foto não vende: quem visita o site julga o
    produto pela vitrine, e vitrine sem foto parece sistema vazio.
    """

    ambiente = AMBIENTES[posicao % len(AMBIENTES)]
    caminho = PASTA_FOTOS / f"imovel{imovel_indice % 8 + 1}-{ambiente}.jpg"
    if not caminho.exists():
        return None
    return ContentFile(caminho.read_bytes(), name=caminho.name)


def foto_gerada(indice, titulo):
    """Reserva sintética, para quando o pacote de fotos não estiver presente."""

    cores = [(203, 213, 225), (148, 163, 184), (100, 116, 139), (71, 85, 105)]
    imagem = Image.new("RGB", (960, 720), cores[indice % len(cores)])
    desenho = ImageDraw.Draw(imagem)
    desenho.rectangle([40, 40, 920, 680], outline=(255, 255, 255), width=6)
    desenho.text((60, 60), f"{titulo[:38]}\nfoto {indice + 1}", fill=(255, 255, 255))

    buffer = BytesIO()
    imagem.save(buffer, format="JPEG", quality=80)
    return ContentFile(buffer.getvalue(), name=f"ambiente-{indice}.jpg")


class Command(BaseCommand):
    help = "Cria a imobiliária inicial (use --completo para a operação inteira)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--completo",
            action="store_true",
            help="Gera carteira, funil, contratos, cobranças, repasses e vistorias.",
        )

    def handle(self, *args, **options):
        tenant = self.criar_tenant()
        equipe = self.criar_equipe(tenant)

        if not options["completo"]:
            self.stdout.write(self.style.SUCCESS(f"\nSenha de todos: {SENHA_PADRAO}"))
            return

        from apps.imoveis.models import Imovel

        if Imovel.objects.filter(tenant=tenant).exists():
            self.stdout.write(self.style.WARNING("Operação já populada; nada a fazer."))
            return

        pessoas = self.criar_pessoas(tenant)
        imoveis = self.criar_imoveis(tenant, pessoas["proprietarios"], equipe)
        self.criar_funil(tenant, imoveis)
        self.criar_operacao_de_locacao(tenant, imoveis, pessoas)
        self.criar_integracao(tenant)

        self.stdout.write(self.style.SUCCESS(f"\nSenha de todos: {SENHA_PADRAO}"))

    # ------------------------------------------------------------- básicos

    def criar_tenant(self):
        tenant, criado = Tenant.objects.get_or_create(
            subdominio="horizonte",
            defaults={
                "razao_social": "Horizonte Negócios Imobiliários Ltda",
                "nome_fantasia": "Horizonte Imóveis",
                "cnpj": "12345678000199",
                "creci": "J-12345",
                "plano": Plano.PROFISSIONAL,
                "email_contato": "contato@horizonteimoveis.com.br",
                "telefone": "3533331000",
            },
        )
        self.stdout.write(f"Imobiliária {'criada' if criado else 'existente'}: {tenant}")
        return tenant

    def criar_equipe(self, tenant):
        equipe = {}
        for email, nome, papel in EQUIPE:
            usuario, criado = Usuario.objects.get_or_create(
                email=email,
                defaults={"tenant": tenant, "nome_completo": nome, "papel": papel},
            )
            if criado:
                usuario.set_password(SENHA_PADRAO)
                usuario.save(update_fields=["password"])
            equipe.setdefault(papel, []).append(usuario)
            self.stdout.write(f"  {papel:12} {email}")

        if not Usuario.objects.filter(papel=Papel.SUPERADMIN).exists():
            Usuario.objects.create_superuser(
                "superadmin@horizonteimoveis.com.br",
                SENHA_PADRAO,
                nome_completo="Operador da Plataforma",
            )
            self.stdout.write("  SUPERADMIN   superadmin@horizonteimoveis.com.br")

        email_atalho, senha_atalho, nome_atalho = ATALHO_ADMIN
        atalho, criado = Usuario.objects.get_or_create(
            email=email_atalho,
            defaults={
                "tenant": tenant,
                "nome_completo": nome_atalho,
                "papel": Papel.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if criado:
            atalho.set_password(senha_atalho)
            atalho.save(update_fields=["password"])
            self.stdout.write(f"  ADMIN        {email_atalho} (senha: {senha_atalho})")

        return equipe

    # -------------------------------------------------------------- carteira

    def criar_pessoas(self, tenant):
        from apps.pessoas.models import Endereco, Pessoa

        def nova(nome, documento, telefone, indice):
            bairro, latitude, longitude = BAIRROS[indice % len(BAIRROS)]
            endereco = Endereco.objects.create(
                cep="37200066",
                logradouro="Rua das Palmeiras",
                numero=str(100 + indice * 7),
                bairro=bairro,
                cidade="Lavras",
                uf="MG",
                latitude=Decimal(str(latitude)),
                longitude=Decimal(str(longitude)),
            )
            return Pessoa.objects.create(
                tenant=tenant,
                tipo="JURIDICA" if len(documento) == 14 else "FISICA",
                nome=nome,
                cpf_cnpj=documento,
                telefone=telefone,
                email=f"{nome.split()[0].lower()}@cliente.test",
                endereco=endereco,
            )

        proprietarios = [nova(*dados, i) for i, dados in enumerate(PROPRIETARIOS)]
        inquilinos = [nova(*dados, i + 10) for i, dados in enumerate(INQUILINOS)]

        self.stdout.write(
            f"  {len(proprietarios)} proprietários e {len(inquilinos)} inquilinos"
        )
        return {"proprietarios": proprietarios, "inquilinos": inquilinos}

    def criar_imoveis(self, tenant, proprietarios, equipe):
        from apps.imoveis.models import Caracteristica, FotoImovel
        from apps.imoveis.services import atualizar_indice_busca, criar_imovel, publicar
        from apps.pessoas.models import Endereco

        catalogo = list(Caracteristica.objects.all())
        corretores = equipe[Papel.CORRETOR]
        criados = []

        for indice, (
            titulo,
            tipo,
            finalidade,
            quartos,
            banheiros,
            vagas,
            area,
            venda,
            locacao,
            condominio,
        ) in enumerate(IMOVEIS):
            bairro, latitude, longitude = BAIRROS[indice % len(BAIRROS)]

            endereco = Endereco.objects.create(
                cep="37200066",
                logradouro="Avenida Central",
                numero=str(200 + indice * 13),
                bairro=bairro,
                cidade="Lavras",
                uf="MG",
                latitude=Decimal(str(latitude + indice * 0.0012)),
                longitude=Decimal(str(longitude - indice * 0.0009)),
            )

            imovel = criar_imovel(
                {
                    "titulo": titulo,
                    "descricao": DESCRICAO_PADRAO,
                    "tipo": tipo,
                    "finalidade": finalidade,
                    "proprietario": proprietarios[indice % len(proprietarios)],
                    "captador": corretores[indice % len(corretores)],
                    "endereco": endereco,
                    "quartos": quartos,
                    "suites": 1 if quartos >= 3 else 0,
                    "banheiros": banheiros,
                    "vagas": vagas,
                    "area_util": Decimal(str(area)),
                    "area_total": Decimal(str(area + 12)),
                    "valor_venda": Decimal(str(venda)) if venda else None,
                    "valor_locacao": Decimal(str(locacao)) if locacao else None,
                    "valor_condominio": Decimal(str(condominio)),
                    "valor_iptu_anual": Decimal(str(round(area * 12))),
                    "matricula": f"{40000 + indice}",
                    "mobiliado": indice % 3 == 0,
                    "aceita_pet": indice % 2 == 0,
                },
                tenant,
            )

            if catalogo:
                # Recorte determinístico do catálogo: massa reproduzível entre
                # execuções e sem gerador pseudoaleatório no código de produção.
                inicio = (indice * 3) % max(1, len(catalogo) - 5)
                imovel.caracteristicas.set(catalogo[inicio : inicio + 5])

            for posicao in range(len(AMBIENTES)):
                FotoImovel.objects.create(
                    imovel=imovel,
                    arquivo=foto_real(indice, posicao) or foto_gerada(posicao, titulo),
                    ordem=posicao,
                    capa=posicao == 0,
                    legenda=AMBIENTES[posicao].capitalize(),
                )

            atualizar_indice_busca(imovel)

            # Deixa dois em captação para a tela mostrar pendências reais.
            if indice < len(IMOVEIS) - 2:
                publicar(imovel)

            criados.append(imovel)

        self.stdout.write(f"  {len(criados)} imóveis com fotos")
        return criados

    # ------------------------------------------------------------------ CRM

    def criar_funil(self, tenant, imoveis):
        from apps.crm.models import Lead
        from apps.crm.services import criar_lead, mover_estagio

        disponiveis = [i for i in imoveis if i.situacao == "DISPONIVEL"]
        agora = timezone.now()

        for indice, nome in enumerate(NOMES_LEADS):
            lead = criar_lead(
                {
                    "nome": nome,
                    "email": f"{nome.split()[0].lower()}@cliente.test",
                    "telefone": f"3599{indice:03d}1234",
                    "origem": ORIGENS[indice % len(ORIGENS)],
                    "imovel_interesse": disponiveis[indice % len(disponiveis)],
                    "valor_estimado": Decimal(str(250000 + indice * 45000)),
                    "temperatura": ["FRIO", "MORNO", "QUENTE"][indice % 3],
                    "mensagem": "Tenho interesse em visitar. Pode ser no fim de semana?",
                },
                tenant,
            )

            # Um em cada seis fica sem contato para o SLA aparecer estourado.
            if indice % 6 == 0:
                Lead.objects.filter(pk=lead.pk).update(
                    atribuido_em=agora - timedelta(minutes=25)
                )
                continue

            self._avancar_lead(lead, ESTAGIOS[indice % len(ESTAGIOS)], indice, agora)

        # Um ganho e um perdido para os relatórios terem numerador e denominador.
        ganho, perdido = Lead.objects.filter(tenant=tenant)[:2]
        mover_estagio(ganho, "FECHADO_GANHO")
        mover_estagio(
            perdido, "FECHADO_PERDIDO", motivo_perda="PRECO", observacao="Achou caro."
        )

        self.stdout.write(f"  {Lead.objects.filter(tenant=tenant).count()} leads no funil")

    def _avancar_lead(self, lead, estagio, indice, agora):
        """Leva o lead até o estágio sorteado, criando visita/proposta no caminho."""

        from apps.crm.services import (
            agendar_visita,
            criar_proposta,
            marcar_primeiro_contato,
            mover_estagio,
            registrar_feedback_visita,
        )

        marcar_primeiro_contato(lead)

        com_visita = {"VISITA_AGENDADA", "VISITA_REALIZADA", "PROPOSTA", "NEGOCIACAO"}
        if estagio in com_visita:
            visita = agendar_visita(
                lead, lead.imovel_interesse, agora + timedelta(days=indice % 5, hours=2)
            )
            if estagio != "VISITA_AGENDADA":
                registrar_feedback_visita(
                    visita,
                    "Gostou do imóvel; achou o valor um pouco acima do orçamento.",
                    "ALTO" if indice % 2 else "MEDIO",
                )

        if estagio in {"PROPOSTA", "NEGOCIACAO"}:
            criar_proposta(
                lead,
                lead.imovel_interesse,
                {
                    "valor_ofertado": Decimal(str(230000 + indice * 40000)),
                    "condicoes_pagamento": "Entrada de 30% e financiamento do saldo.",
                    "validade": timezone.localdate() + timedelta(days=10),
                },
            )

        if estagio in {"EM_CONTATO", "QUALIFICADO"}:
            mover_estagio(lead, estagio)

    # ------------------------------------------------------------- locação

    @transaction.atomic
    def criar_operacao_de_locacao(self, tenant, imoveis, pessoas):
        from apps.contratos.models import PapelParte, ParteContrato
        from apps.contratos.services import ativar_contrato, criar_contrato
        from apps.locacao.services import baixar_cobranca, executar_etapa_da_regua
        from apps.vistorias.services import criar_vistoria, finalizar_vistoria

        para_locar = [
            imovel
            for imovel in imoveis
            if imovel.situacao == "DISPONIVEL" and imovel.valor_locacao
        ][:3]

        hoje = timezone.localdate()

        for indice, imovel in enumerate(para_locar):
            contrato = criar_contrato(
                {
                    "tipo": "LOCACAO",
                    "imovel": imovel,
                    "data_inicio": hoje - timedelta(days=30 * (indice + 1)),
                    "data_fim": hoje + timedelta(days=900 - 30 * indice),
                    "valor": imovel.valor_locacao,
                    "dia_vencimento": 10,
                    "taxa_administracao_percent": Decimal("8.00"),
                    "taxa_intermediacao": imovel.valor_locacao,
                    "garantia_tipo": "FIADOR",
                    "multa_rescisoria_meses": 3,
                },
                tenant,
            )

            ParteContrato.objects.create(
                contrato=contrato, pessoa=imovel.proprietario, papel=PapelParte.LOCADOR
            )
            ParteContrato.objects.create(
                contrato=contrato,
                pessoa=pessoas["inquilinos"][indice % len(pessoas["inquilinos"])],
                papel=PapelParte.LOCATARIO,
            )

            ativar_contrato(contrato)

            cobrancas = list(contrato.cobrancas.order_by("competencia"))

            # Primeiro contrato: tudo pago. Segundo: uma em atraso na régua.
            if indice == 0:
                for cobranca in cobrancas[:2]:
                    baixar_cobranca(cobranca, cobranca.valor_total)
            elif indice == 1 and cobrancas:
                atrasada = cobrancas[0]
                atrasada.vencimento = hoje - timedelta(days=7)
                atrasada.save(update_fields=["vencimento"])
                executar_etapa_da_regua(atrasada, "COBRANCA")

            vistoria = criar_vistoria(contrato, "ENTRADA")
            finalizar_vistoria(vistoria)

        self.stdout.write(f"  {len(para_locar)} contratos de locação ativos")

    def criar_integracao(self, tenant):
        from apps.integracoes.models import IntegracaoPortal

        for portal in ["VIVA_REAL", "ZAP"]:
            IntegracaoPortal.objects.get_or_create(
                tenant=tenant,
                portal=portal,
                defaults={"identificador_externo": f"conta-{portal.lower()}"},
            )
        self.stdout.write("  2 integrações de portal configuradas")
