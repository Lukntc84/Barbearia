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
    
class ConfiguracaoBarbeiro(models.Model):
    barbeiro = models.OneToOneField(
        Barbeiro,
        on_delete=models.CASCADE,
        related_name="configuracao"
    )

    antecedencia_cancelamento_horas = models.PositiveIntegerField(
        default=2,
        verbose_name="Antecedência para cancelamento",
        help_text="Quantidade mínima de horas antes do atendimento."
    )

    antecedencia_reagendamento_horas = models.PositiveIntegerField(
        default=2,
        verbose_name="Antecedência para reagendamento",
        help_text="Quantidade mínima de horas antes do atendimento."
    )

    antecedencia_agendamento_minutos = models.PositiveIntegerField(
        default=60,
        verbose_name="Antecedência para novo agendamento",
        help_text="Exemplo: 60 significa que o cliente deve agendar com pelo menos 1 hora de antecedência."
    )

    dias_futuros_agendamento = models.PositiveIntegerField(
        default=30,
        verbose_name="Limite de dias futuros",
        help_text="Até quantos dias no futuro o cliente pode agendar."
    )

    permitir_agendamento_mesmo_dia = models.BooleanField(
        default=True,
        verbose_name="Permitir agendamento no mesmo dia"
    )

    ativo = models.BooleanField(
        default=True,
        verbose_name="Configuração ativa"
    )

    class Meta:
        verbose_name = "Configuração do barbeiro"
        verbose_name_plural = "Configurações dos barbeiros"

    def __str__(self):
        return f"Configurações de {self.barbeiro.nome_publico}"

    def clean(self):
        if self.antecedencia_cancelamento_horas > 168:
            raise ValidationError(
                "A antecedência para cancelamento não pode ultrapassar 168 horas."
            )

        if self.antecedencia_reagendamento_horas > 168:
            raise ValidationError(
                "A antecedência para reagendamento não pode ultrapassar 168 horas."
            )

        if self.antecedencia_agendamento_minutos > 10080:
            raise ValidationError(
                "A antecedência para agendamento não pode ultrapassar 7 dias."
            )

        if self.dias_futuros_agendamento < 1:
            raise ValidationError(
                "O limite de dias futuros precisa ser de pelo menos 1 dia."
            )

        if self.dias_futuros_agendamento > 365:
            raise ValidationError(
                "O limite de dias futuros não pode ultrapassar 365 dias."
            )
    
class HorarioFuncionamento(models.Model):
    DIA_SEMANA_CHOICES = [
        (0, "Segunda-feira"),
        (1, "Terça-feira"),
        (2, "Quarta-feira"),
        (3, "Quinta-feira"),
        (4, "Sexta-feira"),
        (5, "Sábado"),
        (6, "Domingo"),
    ]

    barbeiro = models.ForeignKey(
        Barbeiro,
        on_delete=models.CASCADE,
        related_name="horarios_funcionamento"
    )

    dia_semana = models.PositiveSmallIntegerField(
        choices=DIA_SEMANA_CHOICES
    )

    hora_inicio = models.TimeField()

    hora_fim = models.TimeField()

    intervalo_minutos = models.PositiveIntegerField(
        default=30,
        help_text="Intervalo usado para gerar os horários disponíveis."
    )

    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["barbeiro", "dia_semana", "hora_inicio"]

        constraints = [
            models.UniqueConstraint(
                fields=["barbeiro", "dia_semana"],
                name="horario_unico_por_barbeiro_e_dia"
            )
        ]

        verbose_name = "Horário de funcionamento"
        verbose_name_plural = "Horários de funcionamento"

    def __str__(self):
        return (
            f"{self.barbeiro.nome_publico} - "
            f"{self.get_dia_semana_display()} - "
            f"{self.hora_inicio.strftime('%H:%M')} às "
            f"{self.hora_fim.strftime('%H:%M')}"
        )

    def clean(self):
        if self.hora_inicio and self.hora_fim:
            if self.hora_inicio >= self.hora_fim:
                raise ValidationError(
                    "O horário final precisa ser posterior ao horário inicial."
                )

        if self.intervalo_minutos is not None:
            if self.intervalo_minutos < 5:
                raise ValidationError(
                    "O intervalo precisa ter pelo menos 5 minutos."
                )

            if self.intervalo_minutos > 240:
                raise ValidationError(
                    "O intervalo não pode ultrapassar 240 minutos."
                )


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