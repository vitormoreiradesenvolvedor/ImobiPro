"""Zera a operação da imobiliária, preservando a conta e a equipe.

Serve para sair da massa inicial e começar a lançar dados reais sem
recriar o banco: imobiliária, usuários e o catálogo de características ficam;
carteira, funil, contratos, financeiro e vistorias saem.

    python manage.py limpar_operacao --tenant horizonte --confirmar
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Papel, Tenant, Usuario


class Command(BaseCommand):
    help = "Apaga os dados operacionais de uma imobiliária (mantém conta e equipe)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            required=True,
            help="Subdomínio da imobiliária (ex.: horizonte).",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma a exclusão. Sem esta flag, só mostra o que seria apagado.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.atendimento.models import EventoTicket, Ticket
        from apps.candidaturas.models import (
            Candidatura,
            DocumentoCandidatura,
            EventoCandidatura,
        )
        from apps.contratos.models import Comissao, Contrato, ParteContrato, Reajuste
        from apps.core.models import LogAuditoria
        from apps.crm.models import Interacao, Lead, Proposta, Visita
        from apps.financeiro.models import Transacao
        from apps.imoveis.models import FotoImovel, HistoricoImovel, Imovel
        from apps.integracoes.models import EventoIntegracao
        from apps.locacao.models import Cobranca, EventoCobranca, Repasse
        from apps.notificacoes.models import Notificacao
        from apps.pessoas.models import Endereco, Pessoa
        from apps.vistorias.models import FotoItemVistoria, ItemVistoria, Vistoria

        tenant = Tenant.objects.filter(subdominio=options["tenant"]).first()
        if not tenant:
            raise CommandError(f"Imobiliária '{options['tenant']}' não encontrada.")

        # A ordem respeita as dependências: filhos antes dos pais.
        alvos = [
            ("eventos de integração", EventoIntegracao.objects.filter(tenant=tenant)),
            (
                "eventos de candidatura",
                EventoCandidatura.objects.filter(candidatura__tenant=tenant),
            ),
            (
                "documentos de candidatura",
                DocumentoCandidatura.objects.filter(candidatura__tenant=tenant),
            ),
            ("candidaturas", Candidatura.objects.filter(tenant=tenant)),
            ("eventos de atendimento", EventoTicket.objects.filter(ticket__tenant=tenant)),
            ("tickets", Ticket.objects.filter(tenant=tenant)),
            ("notificações", Notificacao.objects.filter(tenant=tenant)),
            ("transações", Transacao.objects.filter(tenant=tenant)),
            (
                "fotos de vistoria",
                FotoItemVistoria.objects.filter(item__vistoria__tenant=tenant),
            ),
            ("itens de vistoria", ItemVistoria.objects.filter(vistoria__tenant=tenant)),
            ("vistorias", Vistoria.objects.filter(tenant=tenant)),
            (
                "eventos de cobrança",
                EventoCobranca.objects.filter(cobranca__tenant=tenant),
            ),
            ("repasses", Repasse.objects.filter(tenant=tenant)),
            ("cobranças", Cobranca.objects.filter(tenant=tenant)),
            ("comissões", Comissao.objects.filter(tenant=tenant)),
            ("reajustes", Reajuste.objects.filter(contrato__tenant=tenant)),
            ("partes de contrato", ParteContrato.objects.filter(contrato__tenant=tenant)),
            ("contratos", Contrato.objects.filter(tenant=tenant)),
            ("propostas", Proposta.objects.filter(tenant=tenant)),
            ("visitas", Visita.objects.filter(tenant=tenant)),
            ("interações", Interacao.objects.filter(lead__tenant=tenant)),
            ("leads", Lead.objects.filter(tenant=tenant)),
            ("histórico de imóveis", HistoricoImovel.objects.filter(imovel__tenant=tenant)),
            ("fotos de imóveis", FotoImovel.objects.filter(imovel__tenant=tenant)),
            ("imóveis", Imovel.objects.filter(tenant=tenant)),
            # Acesso de cliente vem da operação, não da equipe: sai junto com ela.
            (
                "acessos de clientes",
                Usuario.objects.filter(
                    tenant=tenant, papel__in=[Papel.INQUILINO, Papel.PROPRIETARIO]
                ),
            ),
            ("pessoas", Pessoa.objects.filter(tenant=tenant)),
            ("logs de auditoria", LogAuditoria.objects.filter(tenant=tenant)),
        ]

        total = 0
        for rotulo, consulta in alvos:
            quantidade = consulta.count()
            total += quantidade
            if quantidade:
                self.stdout.write(f"  {quantidade:5} {rotulo}")
            if options["confirmar"]:
                consulta.delete()

        # Endereços ficam órfãos depois que pessoas e imóveis somem.
        orfaos = Endereco.objects.filter(pessoas__isnull=True, imovel__isnull=True)
        self.stdout.write(f"  {orfaos.count():5} endereços órfãos")
        if options["confirmar"]:
            orfaos.delete()
            # O código do próximo imóvel volta a começar em REF-000001.
            Tenant.objects.filter(pk=tenant.pk).update(sequencia_imovel=0)

        if options["confirmar"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{total} registros apagados. {tenant} pronta para uso real."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\nNada foi apagado ({total} registros elegíveis). "
                    "Use --confirmar para executar."
                )
            )
