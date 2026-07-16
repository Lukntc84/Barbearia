from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.inicio,
        name="inicio"
    ),

    path(
        "cadastro/",
        views.cadastro_cliente,
        name="cadastro_cliente"
    ),

    path(
        "login/",
        views.login_cliente,
        name="login_cliente"
    ),

    path(
        "logout/",
        views.logout_cliente,
        name="logout_cliente"
    ),

    path(
        "agendar/",
        views.agendar_cliente,
        name="agendar_cliente"
    ),

    path(
        "meus-agendamentos/",
        views.meus_agendamentos,
        name="meus_agendamentos"
    ),

    path(
        "meus-agendamentos/<int:agendamento_id>/reagendar/",
        views.reagendar_agendamento,
        name="reagendar_agendamento"
    ),

    path(
        "meus-agendamentos/<int:agendamento_id>/cancelar/",
        views.cancelar_agendamento,
        name="cancelar_agendamento"
    ),

    path(
        "barbeiro/configuracoes/",
        views.configuracoes_barbeiro,
        name="configuracoes_barbeiro"
    ),
    path(
        "barbeiro/clientes/<int:cliente_id>/",
        views.cliente_detalhe,
        name="cliente_detalhe"
    ),
    path(
    "barbeiro/servicos/",
    views.servicos_painel,
    name="servicos_painel"
    ),

    path(
        "barbeiro/servicos/novo/",
        views.servico_novo,
        name="servico_novo"
    ),

    path(
        "barbeiro/servicos/<int:servico_id>/editar/",
        views.servico_editar,
        name="servico_editar"
    ),

    path(
        "barbeiro/servicos/<int:servico_id>/status/",
        views.servico_alternar_status,
        name="servico_alternar_status"
    ),
    path(
        "barbeiro/dashboard/",
        views.dashboard_barbeiro,
        name="dashboard_barbeiro"
    ),
    path(
    "notificacoes/",
    views.notificacoes_usuario,
    name="notificacoes_usuario"
    ),

    path(
        "notificacoes/<int:notificacao_id>/lida/",
        views.notificacao_marcar_lida,
        name="notificacao_marcar_lida"
    ),

    path(
        "notificacoes/marcar-todas-lidas/",
        views.notificacoes_marcar_todas_lidas,
        name="notificacoes_marcar_todas_lidas"
    ),

    
]