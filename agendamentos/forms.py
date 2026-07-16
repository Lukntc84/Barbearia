from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import (
    Cliente,
    ConfiguracaoBarbeiro,
    HorarioFuncionamento,
)


class CadastroClienteForm(forms.Form):
    nome = forms.CharField(
        label="Nome completo",
        max_length=120,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Digite seu nome completo",
            "autocomplete": "name",
        }),
    )

    telefone = forms.CharField(
        label="WhatsApp",
        max_length=20,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "(11) 99999-9999",
            "autocomplete": "tel",
        }),
    )

    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "seuemail@exemplo.com",
            "autocomplete": "email",
        }),
    )

    username = forms.CharField(
        label="Usuário",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Escolha um nome de usuário",
            "autocomplete": "username",
        }),
    )

    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Crie uma senha",
            "autocomplete": "new-password",
        }),
    )

    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Digite a senha novamente",
            "autocomplete": "new-password",
        }),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nome de usuário já está em uso.")

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe uma conta cadastrada com este e-mail.")

        return email

    def clean_telefone(self):
        telefone = self.cleaned_data["telefone"].strip()

        if Cliente.objects.filter(telefone=telefone).exists():
            raise ValidationError("Já existe uma conta cadastrada com este telefone.")

        return telefone

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não coincidem.")

        if password1 and len(password1) < 8:
            self.add_error("password1", "A senha deve ter pelo menos 8 caracteres.")

        return cleaned_data


class LoginClienteForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Digite seu usuário",
        })
    )

    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Digite sua senha",
        })
    )


class ConfiguracaoBarbeiroForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoBarbeiro

        fields = [
            "antecedencia_cancelamento_horas",
            "antecedencia_reagendamento_horas",
            "antecedencia_agendamento_minutos",
            "dias_futuros_agendamento",
            "permitir_agendamento_mesmo_dia",
        ]

        widgets = {
            "antecedencia_cancelamento_horas": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "max": 168,
            }),
            "antecedencia_reagendamento_horas": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "max": 168,
            }),
            "antecedencia_agendamento_minutos": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
                "max": 10080,
            }),
            "dias_futuros_agendamento": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "max": 365,
            }),
            "permitir_agendamento_mesmo_dia": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }


class HorarioFuncionamentoForm(forms.ModelForm):
    class Meta:
        model = HorarioFuncionamento

        fields = [
            "hora_inicio",
            "hora_fim",
            "intervalo_minutos",
            "ativo",
        ]

        widgets = {
            "hora_inicio": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "hora_fim": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),
            "intervalo_minutos": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 5,
                "max": 240,
                "step": 5,
            }),
            "ativo": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }