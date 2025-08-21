// portal/static/js/admin_disponibilidade.js
document.addEventListener('DOMContentLoaded', function() {
    const gridContainer = document.getElementById('disponibilidade-grid');
    const saveButton = document.getElementById('save-disponibilidade-btn');
    if (!gridContainer || !saveButton) return;

    const professorId = gridContainer.dataset.professorId;
    
    // Mapeamento de status para classes CSS e texto
    const statusMap = {
        'disponivel': { text: 'Disponível', class: 'status-disponivel' },
        'indisponivel': { text: 'Indisponível', class: 'status-indisponivel' },
        'externo': { text: 'Externo', class: 'status-externo' }
    };
    const statusCycle = ['disponivel', 'indisponivel', 'externo'];

    // Adiciona o evento de clique na grade (delegação de evento)
    gridContainer.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('grid-cell')) {
            const cell = e.target;
            const currentStatus = cell.dataset.status || 'disponivel';
            const nextIndex = (statusCycle.indexOf(currentStatus) + 1) % statusCycle.length;
            const nextStatus = statusCycle[nextIndex];
            
            // Atualiza o atributo de dados e as classes da célula
            cell.dataset.status = nextStatus;
            Object.values(statusMap).forEach(s => cell.classList.remove(s.class));
            cell.classList.add(statusMap[nextStatus].class);
            cell.textContent = statusMap[nextStatus].text;
        }
    });

    // Adiciona o evento de clique ao botão de salvar
    saveButton.addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        const novaDisponibilidade = {};
        const cells = gridContainer.querySelectorAll('.grid-cell');
        
        cells.forEach(cell => {
            const dia = cell.dataset.dia;
            const horario = cell.dataset.horario;
            const status = cell.dataset.status;

            // Apenas adiciona ao JSON se o status não for 'disponivel' (o padrão)
            if (status && status !== 'disponivel') {
                if (!novaDisponibilidade[dia]) {
                    novaDisponibilidade[dia] = {};
                }
                novaDisponibilidade[dia][horario] = status;
            }
        });

        // Envia os dados para o backend via API
        fetch(`/admin/professores/disponibilidade/${professorId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(novaDisponibilidade)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Disponibilidade salva com sucesso!'); // Pode substituir por um flash message mais elegante
            } else {
                alert('Erro ao salvar: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Ocorreu um erro de comunicação ao salvar.');
        })
        .finally(() => {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-save"></i> Salvar Disponibilidade';
        });
    });
});