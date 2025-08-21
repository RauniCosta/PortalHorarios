// portal/static/js/admin_dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    const geradorContainer = document.getElementById('gerador-horarios-container');
    if (!geradorContainer) return;

    const btnIniciar = document.getElementById('btn-iniciar-geracao');
    const statusDiv = document.getElementById('gerador-status');
    let intervalId = null;

    const validarUrl = geradorContainer.dataset.validarUrl;
    const gerarUrl = geradorContainer.dataset.gerarUrl;
    const statusUrlBase = geradorContainer.dataset.statusUrlBase;
    const sugestoesUrl = geradorContainer.dataset.sugestoesUrl;
    const disponibilidadeUrlBase = geradorContainer.dataset.disponibilidadeUrlBase;

    btnIniciar.addEventListener('click', function() {
        if (confirm('Iniciar verificação e geração de sugestão de horário?')) {
            iniciarValidacao();
        }
    });

    function iniciarValidacao() {
        btnIniciar.disabled = true;
        btnIniciar.innerHTML = '<i class="fas fa-check-circle"></i> Validando dados...';
        statusDiv.innerHTML = '<p class="text-info">Executando pré-verificação de consistência dos dados...</p>';

        fetch(validarUrl, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                statusDiv.innerHTML = '<p class="text-success">Validação concluída com sucesso! Iniciando geração do horário...</p>';
                iniciarGeracao();
            } else {
                mostrarRelatorioDeConflitos(data.conflitos);
            }
        })
        .catch(err => {
            console.error('Erro na validação:', err);
            mostrarErro('Ocorreu um erro de comunicação ao validar os dados.');
        });
    }

    function iniciarGeracao() {
        btnIniciar.disabled = true;
        btnIniciar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando, por favor aguarde...';
        statusDiv.innerHTML = '<p style="color: #007bff;">Iniciando processo no servidor...</p>';
        
        fetch(gerarUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
        .then(response => response.json())
        .then(data => {
            if (data.task_id) {
                statusDiv.innerHTML = `<p style="color: #17a2b8;">Tarefa <strong>${data.task_id}</strong> iniciada. Verificando status...</p>`;
                intervalId = setInterval(() => verificarStatus(data.task_id), 3000);
            } else {
                mostrarErro(data.error || 'Não foi possível iniciar a tarefa de geração.');
            }
        })
        .catch(err => {
            console.error('Erro ao iniciar geração:', err);
            mostrarErro('Ocorreu um erro de comunicação com o servidor.');
        });
    }
    
    function verificarStatus(taskId) {
        const finalStatusUrl = statusUrlBase.replace('__TASK_ID__', taskId);
        fetch(finalStatusUrl)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'completed') {
                clearInterval(intervalId);
                statusDiv.innerHTML = `
                    <div style="border: 1px solid #28a745; padding: 15px; border-radius: 5px; background-color: #d4edda;">
                        <h4 style="color: #155724;">Geração Concluída!</h4>
                        <p>Uma nova sugestão de horário foi gerada com sucesso.</p>
                        <a href="${sugestoesUrl}" class="btn btn-primary" style="background-color: #28a745;">Ver Sugestões</a>
                    </div>
                `;
                btnIniciar.disabled = false;
                btnIniciar.innerHTML = '<i class="fas fa-play-circle"></i> Iniciar Nova Geração';
            } else if (data.status === 'failed') {
                clearInterval(intervalId);
                mostrarErro(`A geração falhou. Motivo: ${data.result || 'Erro desconhecido.'}`);
            }
        })
        .catch(err => {
            console.error('Erro ao verificar status:', err);
        });
    }
    
    function mostrarRelatorioDeConflitos(conflitos) {
        let rowsHtml = conflitos.map(conflito => {
            const linkDisponibilidade = disponibilidadeUrlBase.replace('__PROF_ID__', conflito.id);
            
            return `
                <tr>
                    <td>${conflito.nome}</td>
                    <td class="text-center"><strong>${conflito.aulas_atribuidas}</strong></td>
                    <td class="text-center"><strong>${conflito.horarios_disponiveis}</strong></td>
                    <td>
                        <a href="${linkDisponibilidade}" class="btn btn-sm btn-secondary" target="_blank">
                            <i class="fas fa-edit"></i> Corrigir Disponibilidade
                        </a>
                    </td>
                </tr>
            `;
        }).join('');

        statusDiv.innerHTML = `
            <div class="alert alert-danger">
                <h4><i class="fas fa-exclamation-triangle"></i> Conflitos de Dados Encontrados!</h4>
                <p>A geração não pode continuar. Corrija a disponibilidade dos professores abaixo e tente novamente.</p>
            </div>
            <table class="table table-bordered" style="background: white;">
                <thead class="thead-dark"><tr><th>Professor</th><th>Aulas Atribuídas</th><th>Horários Disponíveis</th><th>Ação</th></tr></thead>
                <tbody>${rowsHtml}</tbody>
            </table>
        `;
        btnIniciar.disabled = false;
        btnIniciar.innerHTML = '<i class="fas fa-redo"></i> Validar Novamente';
    }

    function mostrarErro(mensagem) {
        statusDiv.innerHTML = `<div class="alert alert-danger"><h4>Erro!</h4><p>${mensagem}</p></div>`;
        btnIniciar.disabled = false;
        btnIniciar.innerHTML = '<i class="fas fa-redo"></i> Tentar Novamente';
    }
});