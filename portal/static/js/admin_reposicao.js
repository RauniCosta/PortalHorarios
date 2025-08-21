// portal/static/js/admin_reposicao.js
document.addEventListener("DOMContentLoaded", function () {
  // --- MAPEAMENTO DOS ELEMENTOS DA UI ---
  const sabadoSelect = document.getElementById("sabado_select");
  const turmaSelect = document.getElementById("turma_select");
  const matrizResumoPanel = document.getElementById("matriz_resumo_panel");
  const matrizList = document.getElementById("matriz_list");
  const horarioGrid = document.getElementById("horario_grid");
  const horarioTitle = document.getElementById("horario_title");
  const instrucaoPasso3 = document.getElementById("instrucao_passo3");

  // Loaders
  const matrizLoader = document.getElementById("matriz_loader");
  const gridLoader = document.getElementById("grid_loader");

  // Modals
  const disciplinaModal = document.getElementById("disciplina_modal");
  const disciplinaModalInfo = document.getElementById("disciplina_modal_info");
  const disciplinasListModal = document.getElementById(
    "disciplinas_list_modal"
  );
  const disciplinaSearchInput = document.getElementById(
    "disciplinaSearchInput"
  );
  const cancelDisciplinaSelectionBtn = document.getElementById(
    "cancel_disciplina_selection"
  );

  const salaModal = document.getElementById("sala_modal");
  const salaModalInfo = document.getElementById("sala_modal_info");
  const salasListModal = document.getElementById("salas_list_modal");
  const cancelSalaSelectionBtn = document.getElementById(
    "cancel_sala_selection"
  );

  // --- VARIÁVEIS DE ESTADO ---
  let matrizDaTurma = [];
  let activeMatrizItem = null;
  let activeCell = null;
  // --- FUNÇÕES AUXILIARES ---
  const showLoader = (loader) => {
    if (loader) loader.classList.add("active");
  };
  const hideLoader = (loader) => {
    if (loader) loader.classList.remove("active");
  };
  const showDisciplinaModal = () => disciplinaModal.classList.remove("hidden");
  const hideDisciplinaModal = () => disciplinaModal.classList.add("hidden");
  const showSalaModal = () => salaModal.classList.remove("hidden");
  const hideSalaModal = () => salaModal.classList.add("hidden");

  // --- LÓGICA DE EVENTOS ---
  function handleSelectionChange() {
    const sabadoId = sabadoSelect.value;
    const turmaId = turmaSelect.value;

    turmaSelect.disabled = !sabadoId;

    if (sabadoId && turmaId) {
      matrizResumoPanel.classList.remove("hidden");
      instrucaoPasso3.classList.remove("hidden");
      carregarDadosDaTurma(sabadoId, turmaId);
    } else {
      resetUI();
    }
  }

  sabadoSelect.addEventListener("change", handleSelectionChange);
  turmaSelect.addEventListener("change", handleSelectionChange);

  function resetUI() {
    matrizResumoPanel.classList.add("hidden");
    instrucaoPasso3.classList.add("hidden");
    horarioGrid.innerHTML =
      '<div class="grid-placeholder"><p><i class="fas fa-arrow-left"></i> Selecione um sábado e uma turma.</p></div>';
  }

  disciplinaSearchInput.addEventListener("input", function () {
    const searchTerm = this.value.toLowerCase();
    disciplinasListModal
      .querySelectorAll(".disciplina-item")
      .forEach((item) => {
        const isVisible = item.textContent.toLowerCase().includes(searchTerm);
        item.style.display = isVisible ? "flex" : "none";
      });
  });

  // --- FUNÇÕES DE RENDERIZAÇÃO (Idênticas às da Alocação Semanal) ---
  function renderizarResumoMatriz(matriz) {
    matrizList.innerHTML = "";
    if (!matriz || matriz.length === 0) return;
    matriz.forEach((item) => {
      const div = document.createElement("div");
      div.className = "matriz-item";
      if (item.aulas_necessarias - item.alocadas <= 0)
        div.classList.add("alocado");
      const progresso =
        item.aulas_necessarias > 0
          ? (item.alocadas / item.aulas_necessarias) * 100
          : 0;
      div.innerHTML = `<div class="matriz-item-header"><strong>${
        item.sigla || item.disciplina
      }</strong></div><p class="matriz-item-subheader">${
        item.professor
      }</p><div class="progress-bar-container"><div class="progress-bar"><div class="progress-bar-fill" style="width: ${progresso}%;"></div></div><span class="progress-bar-label">${
        item.alocadas
      }/${item.aulas_necessarias}</span></div>`;
      matrizList.appendChild(div);
    });
  }
  // --- FUNÇÕES DE RENDERIZAÇÃO ---
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
      div.innerHTML = `<div class="matriz-item-header"><strong>${
        item.sigla || item.disciplina
      }</strong></div><p class="matriz-item-subheader">${
        item.professor
      }</p><div class="progress-bar-container"><div class="progress-bar"><div class="progress-bar-fill" style="width: ${progresso}%;"></div></div><span class="progress-bar-label">${
        item.alocadas
      }/${item.aulas_necessarias}</span></div>`;
      matrizList.appendChild(div);
    });
  }

  function renderizarGrade(grade, alocacoes) {
    horarioGrid.innerHTML = "";
    if (!grade || Object.keys(grade).length === 0) {
      horarioGrid.innerHTML =
        '<div class="info-message"><p>Grade não definida para este sábado.</p></div>';
      return;
    }
    const table = document.createElement("table");
    table.className = "table table-bordered text-center";
    const diaKey = "sabado";
    table.innerHTML = `<thead><tr><th>Horário</th><th>${
      diaKey.charAt(0).toUpperCase() + diaKey.slice(1)
    }</th></tr></thead>`;
    const tbody = document.createElement("tbody");
    Object.entries(grade).forEach(([horario, apelido]) => {
      const row = document.createElement("tr");
      row.innerHTML = `<th>${apelido}<br><small>${horario}</small></th>`;
      const cell = document.createElement("td");
      if (String(apelido).toUpperCase().includes("INTERVALO")) {
        cell.className = "intervalo-cell";
      } else {
        cell.className = "horario-cell";
        cell.dataset.dia = diaKey;
        cell.dataset.horario = horario;
        const aulasNesteSlot = alocacoes[diaKey]?.[horario] || [];
        aulasNesteSlot.forEach((aula) => {
          cell.innerHTML += `<div class="aula-bloco" title="${aula.disciplina}"><strong>${aula.disciplina}</strong><small>${aula.professor}</small><small class="sala-info">Sala: ${aula.sala}</small><button class="remover-btn" data-matriz-id="${aula.matriz_id}" title="Remover"><i class="fas fa-times"></i></button></div>`;
        });
        cell.addEventListener("click", () => handleCellClick(cell));
      }
      row.appendChild(cell);
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
    const disciplinasPendentes = matrizDaTurma;
    if (disciplinasPendentes.length === 0) {
      disciplinasListModal.innerHTML = "<p>Nenhuma disciplina encontrada.</p>";
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
    try {
      const response = await fetch("/admin/api/reposicao/salas-disponiveis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sabado_id: sabadoSelect.value,
          horario: horario,
        }),
      });
      const data = await response.json();
      salasListModal.innerHTML = "";
      if (data.available_rooms.length > 0) {
        data.available_rooms.forEach((sala_nome) => {
          const button = document.createElement("button");
          button.className = "sala-item";
          button.textContent = sala_nome;
          button.addEventListener("click", () => alocarAula(sala_nome));
          salasListModal.appendChild(button);
        });
      } else {
        salasListModal.innerHTML = "<p>Nenhuma sala livre encontrada.</p>";
      }
    } catch (error) {
      salasListModal.innerHTML = `<p class="info-message error">${error.message}</p>`;
    }
  }
  // --- LÓGICA DE INTERAÇÃO E API ---
  function handleCellClick(cell) {
    activeCell = cell;
    disciplinaModalInfo.innerHTML = `Alocando para <strong>${cell.dataset.dia.replace(
      "-feira",
      ""
    )} às ${cell.dataset.horario}</strong>.`;
    disciplinaSearchInput.value = "";
    renderizarDisciplinasNoModal(cell);
    showDisciplinaModal();
    setTimeout(() => disciplinaSearchInput.focus(), 100);
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

  async function carregarDadosDaTurma(sabadoId, turmaId) {
    showLoader(matrizLoader);
    showLoader(gridLoader);
    horarioTitle.innerHTML = `<i class="fas fa-th"></i> Horário: ${
      turmaSelect.options[turmaSelect.selectedIndex].text
    }`;
    try {
      const response = await fetch(
        `/admin/api/dados_reposicao/${sabadoId}/${turmaId}`
      );
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

  // --- FUNÇÃO CORRIGIDA ---
  async function alocarAula(salaNome) {
    hideSalaModal();
    showLoader(gridLoader);
    try {
      // Monta o corpo da requisição com as variáveis corretas do JavaScript
      const payload = {
        sabado_id: sabadoSelect.value,
        turma_id: turmaSelect.value,
        matriz_id: activeMatrizItem.matriz_id,
        horario: activeCell.dataset.horario,
        sala_nome: salaNome, // O nome da sala que foi clicada
      };

      const response = await fetch("/admin/api/reposicao/alocar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok || data.status !== "success") {
        throw new Error(data.message || "Ocorreu um erro desconhecido.");
      }

      // Recarrega os dados para mostrar a nova aula na grade
      await carregarDadosDaTurma(sabadoSelect.value, turmaSelect.value);
    } catch (error) {
      alert(`Erro ao alocar: ${error.message}`);
    } finally {
      hideLoader(gridLoader);
    }
  }

  async function removerAula(cell, matrizId) {
    if (!confirm("Tem certeza que deseja remover esta aula?")) return;
    showLoader(gridLoader);
    try {
      const response = await fetch("/admin/api/reposicao/remover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sabado_id: sabadoSelect.value,
          quadro_aula_id: parseInt(matrizId),
          horario: cell.dataset.horario,
        }),
      });
      const data = await response.json();
      if (data.status !== "success") throw new Error(data.message);
      await carregarDadosDaTurma(sabadoSelect.value, turmaSelect.value);
    } catch (error) {
      alert(`Erro ao remover: ${error.message}`);
    } finally {
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
