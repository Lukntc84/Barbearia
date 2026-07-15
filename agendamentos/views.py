from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CadastroClienteForm, LoginClienteForm
from .models import Agendamento, Barbeiro, Cliente, Servico
from django.contrib.auth.models import User


def inicio(request):
    if not request.user.is_authenticated:
        return redirect("login_cliente")

    if (
        request.user.is_staff
        or request.user.is_superuser
        or hasattr(request.user, "barbeiro_perfil")
    ):
        return redirect("dashboard_barbeiro")

    return redirect("agendar_cliente")

def cadastro_cliente(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = CadastroClienteForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                nome_completo = form.cleaned_data["nome"].strip()
                partes_nome = nome_completo.split(maxsplit=1)

                primeiro_nome = partes_nome[0]
                sobrenome = partes_nome[1] if len(partes_nome) > 1 else ""

                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    first_name=primeiro_nome,
                    last_name=sobrenome,
                )

                Cliente.objects.create(
                    user=user,
                    nome=nome_completo,
                    telefone=form.cleaned_data["telefone"],
                )

            login(request, user)

            messages.success(
                request,
                "Cadastro realizado com sucesso! Agora você já pode agendar seu horário."
            )

            return redirect("agendar_cliente")

    else:
        form = CadastroClienteForm()

    return render(
        request,
        "agendamentos/cadastro.html",
        {"form": form},
    )

def login_cliente(request):
    if request.user.is_authenticated:
        return redirect("inicio")

    if request.method == "POST":
        form = LoginClienteForm(request=request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            messages.success(
                request,
                f"Bem-vindo, {user.first_name or user.username}!"
            )

            next_url = request.POST.get("next") or request.GET.get("next")

            if next_url:
                return redirect(next_url)

            if (
                user.is_staff
                or user.is_superuser
                or hasattr(user, "barbeiro_perfil")
            ):
                return redirect("dashboard_barbeiro")

            return redirect("agendar_cliente")

    else:
        form = LoginClienteForm(request=request)

    return render(
        request,
        "agendamentos/login.html",
        {"form": form},
    )


def logout_cliente(request):
    logout(request)
    messages.success(request, "Você saiu da sua conta.")
    return redirect("login_cliente")


@login_required
def agendar_cliente(request):
    servicos = Servico.objects.filter(ativo=True).order_by("nome")
    barbeiros = Barbeiro.objects.filter(ativo=True).order_by("nome_publico")

    data_str = request.GET.get("data") or request.POST.get("data")
    barbeiro_id = request.GET.get("barbeiro") or request.POST.get("barbeiro")

    hoje = timezone.localdate()

    if data_str:
        try:
            data_selecionada = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data_selecionada = hoje
    else:
        data_selecionada = hoje

    if data_selecionada < hoje:
        data_selecionada = hoje
        messages.warning(request, "Não é possível selecionar uma data anterior a hoje.")

    barbeiro_selecionado = None

    if barbeiro_id:
        barbeiro_selecionado = Barbeiro.objects.filter(
            id=barbeiro_id,
            ativo=True
        ).first()

    if request.method == "POST":
        servico_id = request.POST.get("servico")
        hora_str = request.POST.get("hora_slot")

        if not barbeiro_selecionado:
            messages.error(request, "Selecione um barbeiro para continuar.")

        elif not servico_id:
            messages.error(request, "Selecione um serviço.")

        elif not hora_str:
            messages.error(request, "Selecione um horário.")

        else:
            try:
                servico = Servico.objects.get(
                    id=servico_id,
                    ativo=True
                )

                hora_time = datetime.strptime(hora_str, "%H:%M").time()

                naive_datetime = datetime.combine(
                    data_selecionada,
                    hora_time
                )

                data_hora = timezone.make_aware(
                    naive_datetime,
                    timezone.get_current_timezone()
                )

                if data_hora <= timezone.now():
                    messages.error(
                        request,
                        "Não é possível agendar um horário que já passou."
                    )

                else:
                    agendamento = Agendamento(
                        cliente=request.user,
                        barbeiro=barbeiro_selecionado,
                        servico=servico,
                        data_hora=data_hora,
                        status="pendente",
                    )

                    agendamento.full_clean()
                    agendamento.save()

                    messages.success(
                        request,
                        (
                            f"Agendamento realizado para "
                            f"{data_selecionada.strftime('%d/%m/%Y')} "
                            f"às {hora_str} com "
                            f"{barbeiro_selecionado.nome_publico}!"
                        )
                    )

                    return redirect("meus_agendamentos")

            except Servico.DoesNotExist:
                messages.error(request, "O serviço selecionado não está disponível.")

            except ValidationError as error:
                mensagem = error.messages[0] if error.messages else str(error)
                messages.error(request, mensagem)

            except ValueError:
                messages.error(request, "O horário informado é inválido.")

    agendamentos_do_dia = Agendamento.objects.none()

    if barbeiro_selecionado:
        agendamentos_do_dia = (
            Agendamento.objects
            .select_related("servico")
            .filter(
                barbeiro=barbeiro_selecionado,
                data_hora__date=data_selecionada,
            )
            .exclude(status="cancelado")
        )

    slots = []

    for hora in range(8, 20):
        horario_slot = time(hora, 0)

        dt_slot = timezone.make_aware(
            datetime.combine(data_selecionada, horario_slot),
            timezone.get_current_timezone()
        )

        fim_slot = dt_slot + timedelta(hours=1)

        ja_passou = dt_slot <= timezone.now()
        ocupado = False

        if barbeiro_selecionado:
            for agendado in agendamentos_do_dia:
                inicio_agendado = agendado.data_hora
                fim_agendado = inicio_agendado + timedelta(
                    minutes=agendado.servico.duracao_minutos
                )

                if dt_slot < fim_agendado and fim_slot > inicio_agendado:
                    ocupado = True
                    break

        disponivel = (
            barbeiro_selecionado is not None
            and not ocupado
            and not ja_passou
        )

        if not barbeiro_selecionado:
            motivo = "Escolha o barbeiro"
        elif ja_passou:
            motivo = "Passou"
        elif ocupado:
            motivo = "Ocupado"
        else:
            motivo = "Livre"

        slots.append({
            "hora": horario_slot.strftime("%H:%M"),
            "disponivel": disponivel,
            "motivo": motivo,
        })

    return render(request, "agendamentos/agendar.html", {
        "servicos": servicos,
        "barbeiros": barbeiros,
        "barbeiro_selecionado": barbeiro_selecionado,
        "slots": slots,
        "data_selecionada": data_selecionada.strftime("%Y-%m-%d"),
        "hoje": hoje.strftime("%Y-%m-%d"),
    })


@login_required
def meus_agendamentos(request):
    agendamentos = (
        Agendamento.objects
        .select_related("barbeiro", "servico")
        .filter(cliente=request.user)
        .order_by("-data_hora")
    )

    agora = timezone.now()

    proximos = []
    historico = []

    for agendamento in agendamentos:
        agendamento.pode_cancelar = (
            agendamento.data_hora > agora
            and agendamento.status in ["pendente", "confirmado"]
        )

        if (
            agendamento.data_hora >= agora
            and agendamento.status not in [
                "concluido",
                "cancelado",
                "nao_compareceu",
            ]
        ):
            proximos.append(agendamento)
        else:
            historico.append(agendamento)

    return render(
        request,
        "agendamentos/meus_agendamentos.html",
        {
            "proximos": proximos,
            "historico": historico,
        },
    )

@login_required
@require_POST
def cancelar_agendamento(request, agendamento_id):
    """
    Só permite que o dono do agendamento cancele.
    """
    agendamento = get_object_or_404(
        Agendamento,
        id=agendamento_id,
        cliente=request.user,
    )

    if agendamento.status not in ["pendente", "confirmado"]:
        messages.error(
            request,
            "Este agendamento não pode mais ser cancelado."
        )

        return redirect("meus_agendamentos")

    if agendamento.data_hora <= timezone.now():
        messages.error(
            request,
            "Não é possível cancelar um agendamento que já passou."
        )

        return redirect("meus_agendamentos")

    agendamento.status = "cancelado"
    agendamento.save(update_fields=["status"])

    messages.success(
        request,
        "Agendamento cancelado com sucesso."
    )

    return redirect("meus_agendamentos")


@login_required
def dashboard_barbeiro(request):
    barbeiro = getattr(request.user, "barbeiro_perfil", None)

    if not request.user.is_staff and not barbeiro:
        messages.error(request, "Acesso restrito aos barbeiros.")
        return redirect("agendar_cliente")

    if request.method == "POST":
        agendamento_id = request.POST.get("agendamento_id")
        novo_status = request.POST.get("status")

        status_validos = dict(Agendamento.STATUS_CHOICES)

        if not agendamento_id or novo_status not in status_validos:
            messages.error(request, "Dados inválidos.")
            return redirect("dashboard_barbeiro")

        try:
            agendamentos_permitidos = Agendamento.objects.all()

            if (
                barbeiro
                and not request.user.is_staff
                and not request.user.is_superuser
            ):
                agendamentos_permitidos = agendamentos_permitidos.filter(
                    barbeiro=barbeiro
                )

            agendamento = agendamentos_permitidos.get(
                id=agendamento_id
            )

            agendamento.status = novo_status
            agendamento.save(update_fields=["status"])

            messages.success(
                request,
                (
                    f"Status de {agendamento.cliente.username} "
                    f"atualizado para "
                    f"{agendamento.get_status_display()}."
                )
            )

        except Agendamento.DoesNotExist:
            messages.error(request, "Agendamento não encontrado.")

        return redirect("dashboard_barbeiro")

    agendamentos = (
        Agendamento.objects
        .select_related("cliente", "barbeiro", "servico")
        .order_by("data_hora")
    )

    if (
        barbeiro
        and not request.user.is_staff
        and not request.user.is_superuser
    ):
        agendamentos = agendamentos.filter(barbeiro=barbeiro)

    data_filtro = request.GET.get("data")
    status_filtro = request.GET.get("status")

    if data_filtro:
        try:
            data_obj = datetime.strptime(
                data_filtro,
                "%Y-%m-%d"
            ).date()

            agendamentos = agendamentos.filter(
                data_hora__date=data_obj
            )

        except ValueError:
            messages.warning(request, "Data inválida.")

    if status_filtro:
        agendamentos = agendamentos.filter(
            status=status_filtro
        )

    return render(request, "agendamentos/dashboard.html", {
        "agendamentos": agendamentos,
        "data_filtro": data_filtro or "",
        "status_filtro": status_filtro or "",
        "status_choices": Agendamento.STATUS_CHOICES,
    })