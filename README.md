# 💈 Barbearia

Sistema web de **agendamento para barbearias**, com áreas separadas para clientes e barbeiros. O cliente agenda, reagenda e cancela horários; o barbeiro gerencia serviços, regras e acompanha a agenda.

## Funcionalidades

**Cliente**
- Cadastro, login e logout
- Agendamento de serviços em horários disponíveis
- Lista de "Meus agendamentos", com reagendamento e cancelamento
- Notificações dentro do sistema (com marcação de lida)

**Barbeiro**
- Dashboard de atendimentos
- Cadastro, edição e ativação/desativação de serviços
- Configurações de antecedência mínima para cancelamento e reagendamento
- Horários de funcionamento
- Consulta de dados do cliente

## Tecnologias

- Python 3 e Django 6
- HTML e CSS
- SQLite no desenvolvimento (suporte a PostgreSQL via variáveis de ambiente)
- Gunicorn e WhiteNoise para deploy

## Como rodar localmente

1. Clone o repositório e entre na pasta do projeto.
2. Crie e ative um ambiente virtual: python -m venv venv
3. Instale as dependências: pip install -r requirements.txt
4. Copie .env.example para .env e defina os seus próprios valores (nunca use chaves reais no exemplo).
5. Aplique as migrações: python manage.py migrate
6. Inicie o servidor: python manage.py runserver

Acesse http://127.0.0.1:8000.

## Estrutura

- core/: configurações do projeto Django
- agendamentos/: app principal (models, views, forms, templates e notificações)

## Modelagem

Cliente, Barbeiro, ConfiguracaoBarbeiro, HorarioFuncionamento, Servico, Agendamento e Notificacao.
