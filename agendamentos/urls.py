from django.urls import path

from . import views


urlpatterns = [
    path("", views.inicio, name="inicio"),

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
        "meus-agendamentos/<int:agendamento_id>/cancelar/",
        views.cancelar_agendamento,
        name="cancelar_agendamento"
    ),

    path(
        "barbeiro/dashboard/",
        views.dashboard_barbeiro,
        name="dashboard_barbeiro"
    ),
]