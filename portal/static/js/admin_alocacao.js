// portal/static/js/admin_alocacao.js
document.addEventListener("DOMContentLoaded", function () {
  // --- 1. MAPEAMENTO DOS ELEMENTOS DA UI ---
  const turmaSelect = document.getElementById("turma_select");
  const matrizResumoPanel = document.getElementById("matriz_resumo_panel");
  const matrizList = document.getElementById("matriz_list");
  const horarioGrid = document.getElementById("horario_grid");
  const horarioTitle = document.getElementById("horario_title");
  const instrucaoPasso2 = document.getElementById("instrucao_passo2");

  // Loaders
  const matrizLoader = document.getElementById("matriz_loader");
  const gridLoader = document.getElementById("grid_loader");

  // Modal de Disciplina (Novo)
  const disciplinaModal = document.getElementById("disciplina_modal");
  const disciplinaModalInfo = document.getElementById("disciplina_modal_info");
  const disciplinasListModal = document.getElementById(
    "disciplinas_list_modal"
  );
  const noDisciplinasMessage = document.getElementById(
    "no_disciplinas_message"
  );
  const cancelDisciplinaSelectionBtn = document.getElementById(
    "cancel_disciplina_selection"
  );
  const disciplinaSearchInput = document.getElementById(
    "disciplinaSearchInput"
  );

  // Modal de Sala (Existente)
  const salaModal = document.getElementById("sala_modal");
  const salaModalInfo = document.getElementById("sala_modal_info");
  const salasListModal = document.getElementById("salas_list_modal");
  const noSalasMessage = document.getElementById("no_salas_message");
  const cancelSalaSelectionBtn = document.getElementById(
    "cancel_sala_selection"
  );

  // --- 2. VARIÁVEIS DE ESTADO ---
  let matrizDaTurma = [];
  let activeMatrizItem = null;
  let activeCell = null;

  // --- FUNÇÕES AUXILIARES ---
  const showLoader = (loader) => {
    if (loader) loader.style.display = "flex";
  };
  const hideLoader = (loader) => {
    if (loader) loader.style.display = "none";
  };
  const showDisciplinaModal = () => disciplinaModal.classList.remove("hidden");
  const hideDisciplinaModal = () => disciplinaModal.classList.add("hidden");
  const showSalaModal = () => salaModal.classList.remove("hidden");
  const hideSalaModal = () => salaModal.classList.add("hidden");

  // --- 3. LÓGICA DE EVENTOS ---
  turmaSelect.addEventListener("change", function () {
    const turmaId = this.value;
    if (turmaId) {
      matrizResumoPanel.classList.remove("hidden");
      instrucaoPasso2.classList.remove("hidden");
      carregarDadosDaTurma(turmaId);
    } else {
      matrizResumoPanel.classList.add("hidden");
      instrucaoPasso2.classList.add("hidden");
      horarioGrid.innerHTML =
        '<div class="grid-placeholder"><p><i class="fas fa-arrow-left"></i> Selecione uma turma para começar.</p></div>';
      horarioTitle.innerHTML = `<i class="fas fa-th"></i> Grade de Horários`;
    }
  });

  disciplinaSearchInput.addEventListener("input", function () {
    const searchTerm = this.value.toLowerCase();
    disciplinasListModal
      .querySelectorAll(".disciplina-item")
      .forEach((item) => {
        const isVisible = item.textContent.toLowerCase().includes(searchTerm);
        item.style.display = isVisible ? "flex" : "none";
      });
  });

  // --- 4. FUNÇÕES DE RENDERIZAÇÃO ---
  function renderizarResumoMatriz(matriz) {
    matrizList.innerHTML = "";
    if (!matriz || matriz.length === 0) return;

    matriz.forEach((item) => {
      const div = document.createElement("div");
      div.className = "matriz-item";
      const aulasRestantes = item.aulas_necessarias - item.alocadas;
      if (aulasRestantes <= 0) div.classList.add("alocado");

      const progresso =
        item.aulas_necessarias > 0
          ? (item.alocadas / item.aulas_necessarias) * 100
          : 0;
      div.innerHTML = `
                <div class="matriz-item-header"><strong>${
                  item.sigla || item.disciplina
                }</strong></div>
                <p class="matriz-item-subheader">${item.professor}</p>
                <div class="progress-bar-container">
                    <div class="progress-bar"><div class="progress-bar-fill" style="width: ${progresso}%;"></div></div>
                    <span class="progress-bar-label">${item.alocadas}/${
        item.aulas_necessarias
      }</span>
                </div>`;
      matrizList.appendChild(div);
    });
  }

  function renderizarGrade(grade, alocacoes) {
    horarioGrid.innerHTML = "";
    if (!grade || Object.keys(grade).length === 0) {
      horarioGrid.innerHTML =
        '<div class="info-message"><p>Grade de horários não definida.</p></div>';
      return;
    }

    const table = document.createElement("table");
    table.className = "table table-bordered text-center";
    const dias = [
      "segunda-feira",
      "terca-feira",
      "quarta-feira",
      "quinta-feira",
      "sexta-feira",
    ];
    table.innerHTML = `<thead><tr><th>Horário</th>${dias
      .map((d) => `<th>${d.charAt(0).toUpperCase() + d.slice(1, 3)}</th>`)
      .join("")}</tr></thead>`;

    const tbody = document.createElement("tbody");
    Object.entries(grade).forEach(([horario, apelido]) => {
      const row = document.createElement("tr");
      row.innerHTML = `<th>${apelido}<br><small>${horario}</small></th>`;
      dias.forEach((diaKey) => {
        const cell = document.createElement("td");
        if (
          String(apelido).toUpperCase().includes("INTERVALO") ||
          String(apelido).toUpperCase().includes("ALMOÇO")
        ) {
          cell.className = "intervalo-cell";
        } else {
          cell.className = "horario-cell";
          cell.dataset.dia = diaKey;
          cell.dataset.horario = horario;

          const aulasNesteSlot = alocacoes[diaKey]?.[horario] || [];
          aulasNesteSlot.forEach((aula) => {
            cell.innerHTML += `
                            <div class="aula-bloco" title="${aula.disciplina}">
                                <strong>${aula.disciplina}</strong>
                                <small>${aula.professor}</small>
                                <small class="sala-info">Sala: ${aula.sala}</small>
                                <button class="remover-btn" data-matriz-id="${aula.matriz_id}" title="Remover"><i class="fas fa-times"></i></button>
                            </div>`;
          });
          cell.addEventListener("click", () => handleCellClick(cell));
        }
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    horarioGrid.appendChild(table);

    horarioGrid.querySelectorAll(".remover-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        removerAula(e.target.closest(".horario-cell"), btn.dataset.matrizId);
      });
    });
  }

  function renderizarDisciplinasNoModal(cell) {
    disciplinasListModal.innerHTML = "";
    noDisciplinasMessage.classList.add("hidden");

    const disciplinasPendentes = matrizDaTurma.filter(
      (item) => item.alocadas < item.aulas_necessarias
    );

    if (disciplinasPendentes.length === 0) {
      noDisciplinasMessage.classList.remove("hidden");
    } else {
      disciplinasPendentes.forEach((item) => {
        const button = document.createElement("button");
        button.className = "disciplina-item";
        button.innerHTML = `<strong>${item.sigla}</strong> <small>${item.professor}</small>`;
        button.addEventListener("click", () => {
          activeMatrizItem = item;
          hideDisciplinaModal();
          abrirModalDeSalas(cell);
        });
        disciplinasListModal.appendChild(button);
      });
    }
  }

  async function renderizarSalasNoModal(dia, horario) {
    salasListModal.innerHTML = '<div class="loader-small"></div>';
    noSalasMessage.classList.add("hidden");
    try {
      const response = await fetch("/admin/api/salas-disponiveis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dia, horario }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error("Falha ao buscar salas.");

      salasListModal.innerHTML = "";
      if (data.available_rooms.length === 0) {
        noSalasMessage.classList.remove("hidden");
      } else {
        data.available_rooms.forEach((sala) => {
          const button = document.createElement("button");
          button.className = "sala-item";
          button.textContent = sala;
          button.addEventListener("click", () => alocarAula(sala));
          salasListModal.appendChild(button);
        });
      }
    } catch (error) {
      salasListModal.innerHTML = `<p class="info-message error">${error.message}</p>`;
    }
  }

  // --- 5. LÓGICA DE INTERAÇÃO ---
  function handleCellClick(cell) {
    activeCell = cell;
    disciplinaModalInfo.innerHTML = `Alocando para <strong>${cell.dataset.dia.replace(
      "-feira",
      ""
    )} às ${cell.dataset.horario}</strong>.`;
    disciplinaSearchInput.value = ""; // Limpa a busca
    renderizarDisciplinasNoModal(cell);
    showDisciplinaModal();
    setTimeout(() => disciplinaSearchInput.focus(), 100); // Foca no campo de busca
  }

  function abrirModalDeSalas(cell) {
    salaModalInfo.innerHTML = `Alocando <strong>${
      activeMatrizItem.disciplina
    }</strong> para <strong>${cell.dataset.dia.replace("-feira", "")} às ${
      cell.dataset.horario
    }</strong>.`;
    renderizarSalasNoModal(cell.dataset.dia, cell.dataset.horario);
    showSalaModal();
  }

  // --- 6. FUNÇÕES DE API ---
  async function carregarDadosDaTurma(turmaId) {
    showLoader(matrizLoader);
    showLoader(gridLoader);
    horarioTitle.innerHTML = `<i class="fas fa-th"></i> Horário: ${
      turmaSelect.options[turmaSelect.selectedIndex].text
    }`;

    try {
      const response = await fetch(`/admin/api/dados_alocacao/${turmaId}`);
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error || "Falha ao carregar dados.");

      matrizDaTurma = data.matriz_turma;
      renderizarResumoMatriz(data.matriz_turma);
      renderizarGrade(data.horarios_grade, data.horarios_alocados || {});
    } catch (error) {
      horarioGrid.innerHTML = `<div class="grid-placeholder error"><p><strong>Erro:</strong> ${error.message}</p></div>`;
      matrizList.innerHTML = "";
      console.error(error);
    } finally {
      hideLoader(matrizLoader);
      hideLoader(gridLoader);
    }
  }

  async function alocarAula(sala) {
    hideSalaModal();
    showLoader(gridLoader);
    try {
      const response = await fetch("/admin/api/alocar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dia: activeCell.dataset.dia,
          horario: activeCell.dataset.horario,
          sala: sala,
          matriz_id: activeMatrizItem.matriz_id,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Erro desconhecido.");
      await carregarDadosDaTurma(turmaSelect.value);
    } catch (error) {
      alert(`Erro ao alocar: ${error.message}`);
      hideLoader(gridLoader);
    } finally {
      activeMatrizItem = null;
    }
  }

  async function removerAula(cell, matrizId) {
    if (!confirm("Tem certeza que deseja remover esta aula?")) return;
    showLoader(gridLoader);
    try {
      const response = await fetch("/admin/api/remover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dia: cell.dataset.dia,
          horario: cell.dataset.horario,
          matriz_id: parseInt(matrizId),
        }),
      });
      const data = await response.json();
      if (data.status !== "success") throw new Error(data.message);
      await carregarDadosDaTurma(turmaSelect.value);
    } catch (error) {
      alert(`Erro ao remover: ${error.message}`);
      hideLoader(gridLoader);
    }
  }

  // --- MANIPULADORES DOS MODAIS ---
  cancelDisciplinaSelectionBtn.addEventListener("click", hideDisciplinaModal);
  disciplinaModal.addEventListener("click", (e) => {
    if (e.target === disciplinaModal) hideDisciplinaModal();
  });
  cancelSalaSelectionBtn.addEventListener("click", hideSalaModal);
  salaModal.addEventListener("click", (e) => {
    if (e.target === salaModal) hideSalaModal();
  });
});
