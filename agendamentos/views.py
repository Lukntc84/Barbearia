from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    CadastroClienteForm,
    ConfiguracaoBarbeiroForm,
    HorarioFuncionamentoForm,
    LoginClienteForm,
)

from .models import (
    Agendamento,
    Barbeiro,
    Cliente,
    ConfiguracaoBarbeiro,
    HorarioFuncionamento,
    Servico,
)


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

def obter_barbeiro_do_usuario(user):
    if not user or not user.is_authenticated:
        return None

    return getattr(user, "barbeiro_perfil", None)


def obter_configuracao_barbeiro(barbeiro):
    if not barbeiro:
        return None

    configuracao, _ = ConfiguracaoBarbeiro.objects.get_or_create(
        barbeiro=barbeiro
    )

    return configuracao


def usuario_pode_gerenciar_barbeiro(user, barbeiro):
    if user.is_staff or user.is_superuser:
        return True

    barbeiro_usuario = obter_barbeiro_do_usuario(user)

    return (
        barbeiro_usuario is not None
        and barbeiro_usuario.id == barbeiro.id
    )

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
    horario_funcionamento = None

    if barbeiro_selecionado:
        horario_funcionamento = (
            HorarioFuncionamento.objects
            .filter(
                barbeiro=barbeiro_selecionado,
                dia_semana=data_selecionada.weekday(),
                ativo=True,
            )
            .first()
        )

    if barbeiro_selecionado and horario_funcionamento:
        inicio_expediente = timezone.make_aware(
            datetime.combine(
                data_selecionada,
                horario_funcionamento.hora_inicio,
            ),
            timezone.get_current_timezone(),
        )

        fim_expediente = timezone.make_aware(
            datetime.combine(
                data_selecionada,
                horario_funcionamento.hora_fim,
            ),
            timezone.get_current_timezone(),
        )

        horario_atual = inicio_expediente

        while horario_atual < fim_expediente:
            proximo_slot = horario_atual + timedelta(
                minutes=horario_funcionamento.intervalo_minutos
            )

            # Não gera um slot que ultrapasse o horário final.
            if proximo_slot > fim_expediente:
                break

            ja_passou = horario_atual <= timezone.now()
            ocupado = False

            for agendado in agendamentos_do_dia:
                inicio_agendado = agendado.data_hora

                fim_agendado = inicio_agendado + timedelta(
                    minutes=agendado.servico.duracao_minutos
                )

                if (
                    horario_atual < fim_agendado
                    and proximo_slot > inicio_agendado
                ):
                    ocupado = True
                    break

            disponivel = not ja_passou and not ocupado

            if ja_passou:
                motivo = "Passou"
            elif ocupado:
                motivo = "Ocupado"
            else:
                motivo = "Livre"

            slots.append({
                "hora": horario_atual.strftime("%H:%M"),
                "disponivel": disponivel,
                "motivo": motivo,
            })

            horario_atual = proximo_slot

    return render(request, "agendamentos/agendar.html", {
        "servicos": servicos,
        "barbeiros": barbeiros,
        "barbeiro_selecionado": barbeiro_selecionado,
        "horario_funcionamento": horario_funcionamento,
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
def reagendar_agendamento(request, agendamento_id):
    agendamento = get_object_or_404(
        Agendamento.objects.select_related(
            "barbeiro",
            "servico",
        ),
        id=agendamento_id,
        cliente=request.user,
    )

    # Só permite reagendar atendimentos ainda ativos.
    if agendamento.status not in ["pendente", "confirmado"]:
        messages.error(
            request,
            "Este agendamento não pode mais ser reagendado."
        )
        return redirect("meus_agendamentos")

    if agendamento.data_hora <= timezone.now():
        messages.error(
            request,
            "Não é possível reagendar um atendimento que já passou."
        )
        return redirect("meus_agendamentos")

    servicos = Servico.objects.filter(
        ativo=True
    ).order_by("nome")

    barbeiros = Barbeiro.objects.filter(
        ativo=True
    ).order_by("nome_publico")

    hoje = timezone.localdate()

    # Valores recebidos ou valores atuais do agendamento.
    barbeiro_id = (
        request.GET.get("barbeiro")
        or request.POST.get("barbeiro")
        or agendamento.barbeiro_id
    )

    servico_id = (
        request.GET.get("servico")
        or request.POST.get("servico")
        or agendamento.servico_id
    )

    data_str = (
        request.GET.get("data")
        or request.POST.get("data")
        or timezone.localtime(
            agendamento.data_hora
        ).date().strftime("%Y-%m-%d")
    )

    try:
        data_selecionada = datetime.strptime(
            str(data_str),
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        data_selecionada = hoje

    if data_selecionada < hoje:
        data_selecionada = hoje

        messages.warning(
            request,
            "Não é possível escolher uma data anterior a hoje."
        )

    barbeiro_selecionado = Barbeiro.objects.filter(
        id=barbeiro_id,
        ativo=True,
    ).first()

    servico_selecionado = Servico.objects.filter(
        id=servico_id,
        ativo=True,
    ).first()

    horario_funcionamento = None
    slots = []

    if barbeiro_selecionado:
        horario_funcionamento = (
            HorarioFuncionamento.objects
            .filter(
                barbeiro=barbeiro_selecionado,
                dia_semana=data_selecionada.weekday(),
                ativo=True,
            )
            .first()
        )

    agendamentos_do_dia = Agendamento.objects.none()

    if barbeiro_selecionado:
        agendamentos_do_dia = (
            Agendamento.objects
            .select_related("servico")
            .filter(
                barbeiro=barbeiro_selecionado,
                data_hora__date=data_selecionada,
            )
            .exclude(id=agendamento.id)
            .exclude(status="cancelado")
        )

    if (
        barbeiro_selecionado
        and servico_selecionado
        and horario_funcionamento
    ):
        inicio_expediente = timezone.make_aware(
            datetime.combine(
                data_selecionada,
                horario_funcionamento.hora_inicio,
            ),
            timezone.get_current_timezone(),
        )

        fim_expediente = timezone.make_aware(
            datetime.combine(
                data_selecionada,
                horario_funcionamento.hora_fim,
            ),
            timezone.get_current_timezone(),
        )

        horario_atual = inicio_expediente

        while horario_atual < fim_expediente:
            # O fim do atendimento considera a duração do serviço.
            fim_atendimento = horario_atual + timedelta(
                minutes=servico_selecionado.duracao_minutos
            )

            # Não exibe horários cujo serviço terminaria após o expediente.
            if fim_atendimento > fim_expediente:
                break

            ja_passou = horario_atual <= timezone.now()
            ocupado = False

            for agendado in agendamentos_do_dia:
                inicio_existente = agendado.data_hora

                fim_existente = inicio_existente + timedelta(
                    minutes=agendado.servico.duracao_minutos
                )

                if (
                    horario_atual < fim_existente
                    and fim_atendimento > inicio_existente
                ):
                    ocupado = True
                    break

            disponivel = not ja_passou and not ocupado

            if ja_passou:
                motivo = "Passou"
            elif ocupado:
                motivo = "Ocupado"
            else:
                motivo = "Livre"

            slots.append({
                "hora": horario_atual.strftime("%H:%M"),
                "disponivel": disponivel,
                "motivo": motivo,
            })

            horario_atual += timedelta(
                minutes=horario_funcionamento.intervalo_minutos
            )

    if request.method == "POST":
        hora_str = request.POST.get("hora_slot")

        if not barbeiro_selecionado:
            messages.error(
                request,
                "Selecione um barbeiro."
            )

        elif not servico_selecionado:
            messages.error(
                request,
                "Selecione um serviço."
            )

        elif not horario_funcionamento:
            messages.error(
                request,
                "O barbeiro não atende nesta data."
            )

        elif not hora_str:
            messages.error(
                request,
                "Selecione um novo horário."
            )

        else:
            try:
                hora_selecionada = datetime.strptime(
                    hora_str,
                    "%H:%M"
                ).time()

                nova_data_hora = timezone.make_aware(
                    datetime.combine(
                        data_selecionada,
                        hora_selecionada,
                    ),
                    timezone.get_current_timezone(),
                )

                if nova_data_hora <= timezone.now():
                    messages.error(
                        request,
                        "O novo horário precisa estar no futuro."
                    )

                else:
                    with transaction.atomic():
                        agendamento.barbeiro = barbeiro_selecionado
                        agendamento.servico = servico_selecionado
                        agendamento.data_hora = nova_data_hora

                        # O barbeiro deve confirmar novamente.
                        agendamento.status = "pendente"

                        agendamento.full_clean()

                        agendamento.save(
                            update_fields=[
                                "barbeiro",
                                "servico",
                                "data_hora",
                                "status",
                            ]
                        )

                    messages.success(
                        request,
                        (
                            "Agendamento alterado para "
                            f"{data_selecionada.strftime('%d/%m/%Y')} "
                            f"às {hora_str} com "
                            f"{barbeiro_selecionado.nome_publico}."
                        )
                    )

                    return redirect("meus_agendamentos")

            except ValueError:
                messages.error(
                    request,
                    "O horário selecionado é inválido."
                )

            except ValidationError as error:
                mensagem = (
                    error.messages[0]
                    if error.messages
                    else str(error)
                )

                messages.error(request, mensagem)

    horario_atual_agendamento = timezone.localtime(
        agendamento.data_hora
    ).strftime("%H:%M")

    return render(
        request,
        "agendamentos/reagendar.html",
        {
            "agendamento": agendamento,
            "barbeiros": barbeiros,
            "servicos": servicos,
            "barbeiro_selecionado": barbeiro_selecionado,
            "servico_selecionado": servico_selecionado,
            "horario_funcionamento": horario_funcionamento,
            "slots": slots,
            "data_selecionada": data_selecionada.strftime(
                "%Y-%m-%d"
            ),
            "hoje": hoje.strftime("%Y-%m-%d"),
            "horario_atual_agendamento": horario_atual_agendamento,
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
def configuracoes_barbeiro(request):
    barbeiro_usuario = obter_barbeiro_do_usuario(request.user)

    if request.user.is_staff or request.user.is_superuser:
        barbeiro_id = request.GET.get("barbeiro") or request.POST.get(
            "barbeiro_id"
        )

        if barbeiro_id:
            barbeiro = get_object_or_404(
                Barbeiro,
                id=barbeiro_id
            )
        else:
            barbeiro = (
                Barbeiro.objects
                .filter(ativo=True)
                .order_by("nome_publico")
                .first()
            )

    else:
        barbeiro = barbeiro_usuario

    if not barbeiro:
        messages.error(
            request,
            "Nenhum perfil de barbeiro foi encontrado."
        )
        return redirect("inicio")

    if not usuario_pode_gerenciar_barbeiro(
        request.user,
        barbeiro
    ):
        messages.error(
            request,
            "Você não possui permissão para editar este barbeiro."
        )
        return redirect("inicio")

    configuracao = obter_configuracao_barbeiro(barbeiro)

    # Garante que existam os sete dias para edição.
    horarios = []

    for dia_numero, dia_nome in HorarioFuncionamento.DIA_SEMANA_CHOICES:
        horario, _ = HorarioFuncionamento.objects.get_or_create(
            barbeiro=barbeiro,
            dia_semana=dia_numero,
            defaults={
                "hora_inicio": time(9, 0),
                "hora_fim": time(18, 0),
                "intervalo_minutos": 30,
                "ativo": False,
            }
        )

        horarios.append(horario)

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "salvar_configuracoes":
            configuracao_form = ConfiguracaoBarbeiroForm(
                request.POST,
                instance=configuracao,
                prefix="config"
            )

            if configuracao_form.is_valid():
                configuracao_form.save()

                messages.success(
                    request,
                    "Configurações gerais salvas com sucesso."
                )

                return redirect("configuracoes_barbeiro")

        elif acao == "salvar_horarios":
            formularios_horarios = []

            todos_validos = True

            for horario in horarios:
                form_horario = HorarioFuncionamentoForm(
                    request.POST,
                    instance=horario,
                    prefix=f"dia_{horario.dia_semana}"
                )

                formularios_horarios.append(
                    {
                        "dia": horario.get_dia_semana_display(),
                        "dia_numero": horario.dia_semana,
                        "form": form_horario,
                    }
                )

                if not form_horario.is_valid():
                    todos_validos = False

            if todos_validos:
                with transaction.atomic():
                    for item in formularios_horarios:
                        item["form"].save()

                messages.success(
                    request,
                    "Horários da semana atualizados com sucesso."
                )

                return redirect("configuracoes_barbeiro")

        else:
            configuracao_form = ConfiguracaoBarbeiroForm(
                instance=configuracao,
                prefix="config"
            )

            formularios_horarios = [
                {
                    "dia": horario.get_dia_semana_display(),
                    "dia_numero": horario.dia_semana,
                    "form": HorarioFuncionamentoForm(
                        instance=horario,
                        prefix=f"dia_{horario.dia_semana}"
                    ),
                }
                for horario in horarios
            ]

    else:
        configuracao_form = ConfiguracaoBarbeiroForm(
            instance=configuracao,
            prefix="config"
        )

        formularios_horarios = [
            {
                "dia": horario.get_dia_semana_display(),
                "dia_numero": horario.dia_semana,
                "form": HorarioFuncionamentoForm(
                    instance=horario,
                    prefix=f"dia_{horario.dia_semana}"
                ),
            }
            for horario in horarios
        ]

    barbeiros_disponiveis = Barbeiro.objects.filter(
        ativo=True
    ).order_by("nome_publico")

    return render(
        request,
        "agendamentos/configuracoes.html",
        {
            "barbeiro": barbeiro,
            "barbeiros_disponiveis": barbeiros_disponiveis,
            "configuracao_form": configuracao_form,
            "formularios_horarios": formularios_horarios,
        },
    )

@login_required
def dashboard_barbeiro(request):
    barbeiro = getattr(request.user, "barbeiro_perfil", None)

    is_admin = request.user.is_staff or request.user.is_superuser

    if not is_admin and not barbeiro:
        messages.error(request, "Acesso restrito aos barbeiros.")
        return redirect("agendar_cliente")

    # =====================================================
    # ALTERAÇÃO DE STATUS
    # =====================================================
    if request.method == "POST":
        agendamento_id = request.POST.get("agendamento_id")
        novo_status = request.POST.get("status")

        status_validos = dict(Agendamento.STATUS_CHOICES)

        if not agendamento_id or novo_status not in status_validos:
            messages.error(request, "Dados inválidos.")
            return redirect("dashboard_barbeiro")

        agendamentos_permitidos = Agendamento.objects.all()

        if barbeiro and not is_admin:
            agendamentos_permitidos = agendamentos_permitidos.filter(
                barbeiro=barbeiro
            )

        try:
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

    # =====================================================
    # QUERY PRINCIPAL
    # =====================================================
    base_qs = (
        Agendamento.objects
        .select_related(
            "cliente",
            "cliente__cliente_perfil",
            "barbeiro",
            "servico",
        )
        .order_by("data_hora")
    )

    # Barbeiro comum vê apenas a própria agenda.
    if barbeiro and not is_admin:
        base_qs = base_qs.filter(barbeiro=barbeiro)

    hoje = timezone.localdate()
    agora = timezone.now()

    # =====================================================
    # KPIs SEM FILTROS
    # =====================================================
    agendamentos_hoje_qs = base_qs.filter(
        data_hora__date=hoje
    )

    total_hoje = agendamentos_hoje_qs.count()

    total_pendentes = agendamentos_hoje_qs.filter(
        status="pendente"
    ).count()

    total_confirmados = agendamentos_hoje_qs.filter(
        status="confirmado"
    ).count()

    total_concluidos = agendamentos_hoje_qs.filter(
        status="concluido"
    ).count()

    total_cancelados = agendamentos_hoje_qs.filter(
        status="cancelado"
    ).count()

    faturamento_previsto = (
        agendamentos_hoje_qs
        .exclude(
            status__in=[
                "cancelado",
                "nao_compareceu",
            ]
        )
        .aggregate(total=Sum("servico__preco"))
        .get("total")
        or 0
    )

    faturamento_realizado = (
        agendamentos_hoje_qs
        .filter(status="concluido")
        .aggregate(total=Sum("servico__preco"))
        .get("total")
        or 0
    )

    # =====================================================
    # FILTROS
    # =====================================================
    data_inicio = request.GET.get("data_inicio", "").strip()
    data_fim = request.GET.get("data_fim", "").strip()
    status_filtro = request.GET.get("status", "").strip()
    cliente_filtro = request.GET.get("cliente", "").strip()
    servico_filtro = request.GET.get("servico", "").strip()

    agendamentos_filtrados = base_qs

    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(
                data_inicio,
                "%Y-%m-%d"
            ).date()

            agendamentos_filtrados = agendamentos_filtrados.filter(
                data_hora__date__gte=data_inicio_obj
            )

        except ValueError:
            messages.warning(request, "Data inicial inválida.")

    if data_fim:
        try:
            data_fim_obj = datetime.strptime(
                data_fim,
                "%Y-%m-%d"
            ).date()

            agendamentos_filtrados = agendamentos_filtrados.filter(
                data_hora__date__lte=data_fim_obj
            )

        except ValueError:
            messages.warning(request, "Data final inválida.")

    if status_filtro:
        agendamentos_filtrados = agendamentos_filtrados.filter(
            status=status_filtro
        )

    if cliente_filtro:
        agendamentos_filtrados = agendamentos_filtrados.filter(
            Q(cliente__username__icontains=cliente_filtro)
            | Q(cliente__first_name__icontains=cliente_filtro)
            | Q(cliente__last_name__icontains=cliente_filtro)
            | Q(cliente__cliente_perfil__nome__icontains=cliente_filtro)
            | Q(cliente__cliente_perfil__telefone__icontains=cliente_filtro)
        )

    if servico_filtro:
        agendamentos_filtrados = agendamentos_filtrados.filter(
            servico_id=servico_filtro
        )

    # =====================================================
    # SEPARAÇÃO DAS LISTAS
    # =====================================================
    agenda_hoje = agendamentos_filtrados.filter(
        data_hora__date=hoje
    ).order_by("data_hora")

    proximos_agendamentos = (
        agendamentos_filtrados
        .filter(data_hora__gt=agora)
        .exclude(data_hora__date=hoje)
        .exclude(
            status__in=[
                "concluido",
                "cancelado",
                "nao_compareceu",
            ]
        )
        .order_by("data_hora")
    )

    historico = (
        agendamentos_filtrados
        .filter(
            Q(data_hora__lt=agora)
            | Q(
                status__in=[
                    "concluido",
                    "cancelado",
                    "nao_compareceu",
                ]
            )
        )
        .exclude(
            id__in=agenda_hoje.values_list("id", flat=True)
        )
        .order_by("-data_hora")
    )

    servicos = Servico.objects.filter(
        ativo=True
    ).order_by("nome")

    context = {
        "agenda_hoje": agenda_hoje,
        "proximos_agendamentos": proximos_agendamentos,
        "historico": historico,

        "total_hoje": total_hoje,
        "total_pendentes": total_pendentes,
        "total_confirmados": total_confirmados,
        "total_concluidos": total_concluidos,
        "total_cancelados": total_cancelados,
        "faturamento_previsto": faturamento_previsto,
        "faturamento_realizado": faturamento_realizado,

        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "status_filtro": status_filtro,
        "cliente_filtro": cliente_filtro,
        "servico_filtro": servico_filtro,

        "status_choices": Agendamento.STATUS_CHOICES,
        "servicos": servicos,
        "hoje": hoje,
    }

    return render(
        request,
        "agendamentos/dashboard.html",
        context,
    )