from .models import Notificacao


def notificacoes_globais(request):
    if not request.user.is_authenticated:
        return {
            "notificacoes_nao_lidas_count": 0,
            "notificacao_popup": None,
        }

    notificacoes_nao_lidas = Notificacao.objects.filter(
        usuario=request.user,
        lida=False,
    ).order_by("-criada_em")

    return {
        "notificacoes_nao_lidas_count": notificacoes_nao_lidas.count(),
        "notificacao_popup": notificacoes_nao_lidas.first(),
    }