# LB Finanças — Sistema de Gestão de Vendas e Estoque

---

## Sobre o Projeto

O LB Finanças é um sistema de gerenciamento voltado para pequenos negócios de revenda, permitindo o controle completo de compras, estoque, clientes, provas, vendas e despesas. A aplicação foi desenvolvida aplicando conceitos de arquitetura de software em camadas e padrões de projeto (Design Patterns).

A ideia surgiu de uma necessidade real de uma microempreendedora familiar de um dos integrantes do grupo, com o objetivo de que o sistema seja efetivamente utilizado por ela após a conclusão do projeto.

---

## Tecnologias Utilizadas

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.13 |
| Framework Web | Django |
| Banco de Dados | PostgreSQL |
| Front-end | Django Templates + Bootstrap |
| Exportação | openpyxl |
| Variáveis de Ambiente | python-dotenv |

---

## Arquitetura

O projeto segue o padrão **MVC/MTV** do Django, com separação de responsabilidades em camadas:

- **Models** — mapeamento das entidades e relacionamentos com o banco de dados
- **Views** — lógica de controle e resposta às requisições HTTP
- **Templates** — camada de apresentação (HTML + Bootstrap)
- **Service Layer** — camada de serviço responsável pelas regras de negócio, desacoplada das views
- **Repository** — abstração do acesso aos dados, separando as queries das regras de negócio

---

## Design Patterns Aplicados

| Padrão | Onde foi aplicado |
|---|---|
| **Repository** | Abstração das queries de banco de dados por entidade |
| **Service Layer** | Camada de serviços concentrando as regras de negócio |
| **MVC/MTV** | Arquitetura geral do projeto via Django |

---

## Funcionalidades

- Cadastro e controle de produtos e estoque
- Registro de compras (lotes)
- Gerenciamento de clientes
- Controle de provas (em prova / devolvida / convertida)
- Registro de vendas diretas e vendas originadas de provas
- Controle de pagamentos (incluindo pagamentos parciais e fiado)
- Registro de despesas
- Exportação de extrato de clientes em Excel
- Backup e restauração de dados (exportar/importar)
- Cálculo dinâmico de saldo devedor e total anual por cliente

---


## Como Rodar Localmente

### Pré-requisitos

- Python 3.13+
- PostgreSQL
- Git
- Demais dependências em `requirements.txt`

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/JoaoPbz/SistemaGestaoProgIII.git

# 2. Entre na pasta do projeto
cd SistemaGestaoProgIII

# 3. Crie e ative o ambiente virtual
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure as variáveis de ambiente
cp .env.example .env
# Abra o arquivo .env e preencha com seus dados (veja seção abaixo)

# 6. Crie o banco de dados no PostgreSQL
# CREATE DATABASE nome_do_banco;

# 7. Execute as migrações
python manage.py migrate

# 8. Inicie o servidor
python manage.py runserver
```

Acesse em: http://127.0.0.1:8000

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com base no `.env.example`:

```
# Pode usar qualquer string longa para desenvolvimento local
SECRET_KEY=coloque-qualquer-string-longa-aqui-para-dev

DB_NAME=nome_do_banco
DB_USER=seu_user
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
DEBUG=True
```

### Observação — Windows (PowerShell)

Se aparecer erro ao ativar o ambiente virtual, rode antes:

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Estrutura do Banco de Dados

| Tabela | Descrição |
|---|---|
| `Compra` | Registro de lotes de compra |
| `Produto` | Produtos com marca, tamanho, cor, preços, estoque e status ativo/inativo |
| `Cliente` | Cadastro de clientes |
| `Prova` | Controle de provas (em prova / devolvida / convertida) |
| `ItemProva` | Produtos vinculados a uma prova |
| `Venda` | Vendas diretas ou originadas de provas |
| `ItemVenda` | Produtos vendidos em cada venda |
| `Pagamento` | Pagamentos realizados (suporta parcial e fiado) |
| `Despesa` | Registro de despesas por categoria |

---

## Integrantes

- João Pedro Pereira Barpp
- Everton Nathan Dias De Oliveira
- Rafael Gustavo Vivian
- Mauricio Campanholo Bairos
- Thiago Da Luz
- Gabriel Morin Werner


---

