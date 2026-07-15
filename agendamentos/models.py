from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone


class Cliente(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cliente_perfil"
    )
    nome = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome or self.user.username


class Barbeiro(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="barbeiro_perfil"
    )
    nome_publico = models.CharField(max_length=120)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome_publico


class Servico(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    duracao_minutos = models.PositiveIntegerField(help_text="Duração em minutos")
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nome} ({self.duracao_minutos} min)"


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("confirmado", "Confirmado"),
        ("em_atendimento", "Em atendimento"),
        ("concluido", "Concluído"),
        ("cancelado", "Cancelado"),
        ("nao_compareceu", "Não compareceu"),
    ]

    cliente = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="agendamentos"
    )

    barbeiro = models.ForeignKey(
        Barbeiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agendamentos"
    )

    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE
    )

    data_hora = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pendente"
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        barbeiro = self.barbeiro.nome_publico if self.barbeiro else "Sem barbeiro"
        return f"{self.cliente.username} - {barbeiro} - {self.servico.nome} ({self.data_hora.strftime('%d/%m/%Y %H:%M')})"

    def clean(self):
        """
        Evita conflito de horário para o mesmo barbeiro.
        Barbeiros diferentes podem atender no mesmo horário.
        """
        if not self.data_hora or not self.servico or not self.barbeiro:
            return

        inicio_atual = timezone.localtime(self.data_hora)
        fim_atual = inicio_atual + timedelta(minutes=self.servico.duracao_minutos)

        agendamentos_do_dia = Agendamento.objects.filter(
            barbeiro=self.barbeiro,
            data_hora__date=inicio_atual.date()
        ).exclude(status="cancelado")

        if self.pk:
            agendamentos_do_dia = agendamentos_do_dia.exclude(pk=self.pk)

        for agendado in agendamentos_do_dia:
            inicio_outro = timezone.localtime(agendado.data_hora)
            fim_outro = inicio_outro + timedelta(minutes=agendado.servico.duracao_minutos)

            if inicio_atual < fim_outro and fim_atual > inicio_outro:
                raise ValidationError(
                    f"Este horário conflita com o agendamento de {agendado.cliente.username} "
                    f"com {agendado.barbeiro.nome_publico} "
                    f"({inicio_outro.strftime('%H:%M')} até {fim_outro.strftime('%H:%M')})."
                )