from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from agendamentos.models import Agendamento, ConfiguracaoBarbeiro, Notificacao


class Command(BaseCommand):
    help = "Envia lembretes internos para agendamentos próximos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--horas",
            type=int,
            default=None,
            help=(
                "Força uma antecedência específica em horas. "
                "Se não informado, usa a configuração de cada barbeiro."
            ),
        )

    def handle(self, *args, **options):
        horas_forcadas = options["horas"]

        agora = timezone.now()

        agendamentos = (
            Agendamento.objects
            .select_related(
                "cliente",
                "cliente__cliente_perfil",
                "barbeiro",
                "barbeiro__user",
                "servico",
            )
            .filter(
                data_hora__gt=agora,
                status__in=[
                    "pendente",
                    "confirmado",
                ],
                barbeiro__isnull=False,
            )
            .order_by("data_hora")
        )

        total_criadas = 0
        total_ignoradas = 0

        for agendamento in agendamentos:
            barbeiro = agendamento.barbeiro

            configuracao, _ = ConfiguracaoBarbeiro.objects.get_or_create(
                barbeiro=barbeiro
            )

            if not configuracao.lembretes_ativos:
                total_ignoradas += 1
                continue

            horas_antecedencia = (
                horas_forcadas
                if horas_forcadas is not None
                else configuracao.antecedencia_lembrete_horas
            )

            limite = agora + timedelta(hours=horas_antecedencia)

            if agendamento.data_hora > limite:
                total_ignoradas += 1
                continue

            data_local = timezone.localtime(agendamento.data_hora)

            nome_cliente = (
                getattr(
                    getattr(agendamento.cliente, "cliente_perfil", None),
                    "nome",
                    None,
                )
                or agendamento.cliente.get_full_name()
                or agendamento.cliente.username
            )

            nome_barbeiro = barbeiro.nome_publico

            data_formatada = data_local.strftime("%d/%m/%Y")
            hora_formatada = data_local.strftime("%H:%M")

            ja_tem_cliente = Notificacao.objects.filter(
                usuario=agendamento.cliente,
                agendamento=agendamento,
                tipo="lembrete",
                titulo="Lembrete de agendamento",
            ).exists()

            if not ja_tem_cliente:
                Notificacao.objects.create(
                    usuario=agendamento.cliente,
                    agendamento=agendamento,
                    tipo="lembrete",
                    titulo="Lembrete de agendamento",
                    mensagem=(
                        f"Seu agendamento de {agendamento.servico.nome} "
                        f"com {nome_barbeiro} está marcado para "
                        f"{data_formatada} às {hora_formatada}."
                    ),
                )

                total_criadas += 1

            ja_tem_barbeiro = Notificacao.objects.filter(
                usuario=barbeiro.user,
                agendamento=agendamento,
                tipo="lembrete",
                titulo="Lembrete de atendimento",
            ).exists()

            if not ja_tem_barbeiro:
                Notificacao.objects.create(
                    usuario=barbeiro.user,
                    agendamento=agendamento,
                    tipo="lembrete",
                    titulo="Lembrete de atendimento",
                    mensagem=(
                        f"Você tem atendimento de {agendamento.servico.nome} "
                        f"com {nome_cliente} em {data_formatada} "
                        f"às {hora_formatada}."
                    ),
                )

                total_criadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Lembretes processados. "
                    f"Notificações criadas: {total_criadas}. "
                    f"Agendamentos ignorados: {total_ignoradas}."
                )
            )
        )