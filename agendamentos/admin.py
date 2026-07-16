from django.contrib import admin
from .models import (
    Cliente,
    Barbeiro,
    HorarioFuncionamento,
    Servico,
    Agendamento,
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "user", "telefone", "criado_em")
    search_fields = ("nome", "telefone", "user__username")


@admin.register(Barbeiro)
class BarbeiroAdmin(admin.ModelAdmin):
    list_display = ("nome_publico", "user", "telefone", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome_publico", "telefone", "user__username")
    
@admin.register(HorarioFuncionamento)
class HorarioFuncionamentoAdmin(admin.ModelAdmin):
    list_display = (
        "barbeiro",
        "dia_semana",
        "hora_inicio",
        "hora_fim",
        "intervalo_minutos",
        "ativo",
    )

    list_filter = (
        "barbeiro",
        "dia_semana",
        "ativo",
    )

    search_fields = (
        "barbeiro__nome_publico",
        "barbeiro__user__username",
    )

    ordering = (
        "barbeiro",
        "dia_semana",
        "hora_inicio",
    )

    list_editable = (
        "hora_inicio",
        "hora_fim",
        "intervalo_minutos",
        "ativo",
    )


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco", "duracao_minutos", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome",)


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "barbeiro", "servico", "data_hora", "status")
    list_filter = ("status", "data_hora", "servico", "barbeiro")
    search_fields = (
        "cliente__username",
        "cliente__first_name",
        "barbeiro__nome_publico",
        "servico__nome",
    )
    list_editable = ("status",)
    date_hierarchy = "data_hora"