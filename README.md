# Portal de Gerenciamento de Horários Escolares

**Status do Projeto:** Fase 1 Concluída

## Sobre o Projeto

Este projeto é um sistema web completo para a gestão de horários escolares, desenvolvido para otimizar e organizar a alocação de aulas, turmas, professores e salas. A aplicação conta com um portal de administração robusto para o gerenciamento dos dados e um painel público para a visualização dos horários finalizados.

A transição de um aplicativo desktop para uma solução totalmente web foi feita para garantir acesso centralizado, facilidade de manutenção e uma experiência de usuário moderna e responsiva.

## Principais Funcionalidades

- **Portal de Administração Web:** Uma interface segura e intuitiva para gerenciar todos os aspectos do horário escolar.
- **Importação Inteligente via CSV:** Capacidade de popular toda a base de dados (turmas, professores, disciplinas, matriz curricular) a partir de um único arquivo CSV, com validação de dados e regras de negócio específicas.
- **Gerenciamento CRUD Completo:** Interface para Criar, Ler, Atualizar e Excluir (CRUD) as entidades do sistema:
    - Turmas (com nome, apelido, período e categoria)
    - Disciplinas
    - Professores
    - Salas de Aula
- **Interface de Alocação Visual:** Uma tela interativa que permite alocar as aulas da matriz curricular em uma grade de horários semanal.
    - Exibição de aulas restantes a alocar.
    - Verificação de disponibilidade de salas em tempo real.
    - Suporte para divisão de turmas (múltiplas aulas no mesmo horário).
    - Validação de conflitos de sala.
- **Painel Público:** Uma página de visualização (`frontend`) para que alunos e professores possam consultar os horários finalizados.
- **Design Responsivo:** Tanto o painel público quanto o portal de administração se adaptam a diferentes tamanhos de tela, como celulares e tablets, com um menu lateral retrátil no admin.
- **Identidade Visual Personalizada:** O design do sistema foi customizado para seguir o guia de estilo do Centro Paula Souza (CPS).

## Tecnologias Utilizadas

- **Backend:** Python 3 com o micro-framework Flask.
- **Frontend:** HTML5, CSS3 e JavaScript (Vanilla JS).
- **Banco de Dados:** Um arquivo `JSON` (`horarios_v2.json`) atua como uma base de dados simples e de fácil manipulação.
- **Bibliotecas Python:**
    - `Flask`: Para o servidor web e gerenciamento de rotas.
    - `Werkzeug`: Para o processamento seguro de uploads de arquivos.

## Estrutura do Projeto
/PortalHorarios
|
|-- web_server.py             # Arquivo principal do servidor Flask com toda a lógica
|-- horarios_v2.json          # O "banco de dados" do projeto
|-- requirements.txt          # Dependências do Python para instalação
|
|-- /templates/               # Contém os arquivos HTML renderizados pelo Flask
|   |-- admin_layout.html       # Layout base para todas as páginas do admin
|   |-- admin_dashboard.html    # Página inicial do admin com a função de importação
|   |-- admin_alocacao.html     # Interface visual para alocar horários
|   |-- admin_salas.html        # Página dedicada para gerenciar salas
|   |-- admin_turma_form.html   # Formulário específico para adicionar/editar turmas
|   |-- admin_view_data.html    # Template genérico para listar dados (prof, disc, etc.)
|   |-- admin_import_report.html # Template para exibir o relatório pós-importação
|   |-- index.html              # A página do painel público
|
|-- /static/                  # Contém arquivos estáticos (CSS, JS, Imagens)
|   |-- admin_style.css         # Folha de estilos para o portal de administração
|   |-- style.css               # Folha de estilos para o painel público
|   |-- /images/
|       |-- logo_cps.svg        # Logotipo usado no frontend
|
|-- /uploads/                 # Pasta temporária para os arquivos CSV enviados

## Instalação e Execução

Para rodar este projeto localmente, siga os passos abaixo:

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-seu-repositorio>
    cd <pasta-do-projeto>
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Crie um arquivo `requirements.txt` com o conteúdo abaixo e depois execute o comando `pip install`.
    ```
    # requirements.txt
    Flask
    Werkzeug
    ```
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute o servidor:**
    ```bash
    python web_server.py
    ```

5.  **Acesse a aplicação:**
    - **Painel Público:** Abra seu navegador e acesse `http://127.0.0.1:5000/`
    - **Portal de Administração:** Acesse `http://127.0.0.1:5000/admin`

## Como Usar

1.  Acesse o portal de administração (`/admin`).
2.  Na página **Dashboard & Importar**, envie o seu arquivo `QUADRO-AULAS.csv` para popular o sistema com os dados mais recentes.
3.  Use os links na barra lateral ("Turmas", "Disciplinas", "Professores", "Salas") para visualizar, adicionar, editar ou excluir registros manualmente.
4.  Acesse a página **"Alocação de Horários"** para montar a grade horária de cada turma de forma visual e interativa.
5.  Visualize o resultado final no **Painel Público** (`/`).

## Próximos Passos (Fase 2)

- [ ] Implementar um sistema de login e autenticação de usuários para o portal de administração.
- [ ] Criar uma funcionalidade para exportar os horários prontos para PDF.
- [ ] Desenvolver um sistema de verificação de conflitos de horários para professores.
- [ ] Adicionar um painel de visualização de horários por professor e por sala.

---
