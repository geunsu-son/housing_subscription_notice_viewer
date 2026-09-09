const PYEONG = 3.305785;
const DEPOSIT_STEP = 10_000_000;

const yearSelect = document.getElementById("year-select");
const companySelect = document.getElementById("company-select");
const noticeBoardList = document.getElementById("notice-board-list");
const noticeDetailEl = document.getElementById("notice-detail");
const viewBoard = document.getElementById("view-board");
const viewDetail = document.getElementById("view-detail");
const appNav = document.getElementById("app-nav");
const backToBoardBtn = document.getElementById("back-to-board");
const sidoSelect = document.getElementById("sido-select");
const sigunguSelect = document.getElementById("sigungu-select");
const typeFilters = document.getElementById("type-filters");
const areaMinInput = document.getElementById("area-min");
const areaMaxInput = document.getElementById("area-max");
const depositMinInput = document.getElementById("deposit-min");
const depositMaxInput = document.getElementById("deposit-max");
const areaValues = document.getElementById("area-values");
const depositValues = document.getElementById("deposit-values");
const dedupToggle = document.getElementById("dedup-toggle");
const resultHeading = document.getElementById("result-heading");
const tableHead = document.querySelector("#result-table thead");
const tableBody = document.querySelector("#result-table tbody");
const statusEl = document.getElementById("status");

let notices = [];
let currentNotice = null;
let currentData = null;
let selectedNoticeId = "";
let currentView = "board";

function showStatus(message, isError = false) {
  statusEl.hidden = !message;
  statusEl.textContent = message || "";
  statusEl.classList.toggle("error", Boolean(isError));
}

function unique(values) {
  const seen = new Set();
  const out = [];
  for (const value of values) {
    const key = value === null || value === undefined ? "__null__" : String(value);
    if (!seen.has(key)) {
      seen.add(key);
      out.push(value);
    }
  }
  return out;
}

function sortValues(values) {
  return [...values].sort((a, b) => {
    if (typeof a === "number" && typeof b === "number") return a - b;
    return String(a ?? "").localeCompare(String(b ?? ""), "ko");
  });
}

function fillSelect(select, values, selected) {
  select.innerHTML = "";
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    if (value === selected) option.selected = true;
    select.appendChild(option);
  }
}

function years() {
  return unique(notices.map((n) => n.year)).sort((a, b) => Number(b) - Number(a));
}

function parseDateValue(value) {
  if (!value) return null;
  const match = String(value).match(/^(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})/);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function formatDateLabel(value) {
  if (!value) return "-";
  const date = parseDateValue(value);
  if (!date) return value;
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}.${m}.${d}`;
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function computeScheduleStatus(notice) {
  const today = startOfDay(new Date());
  const posted = parseDateValue(notice.postedOn);
  const applyStart = parseDateValue(notice.applyStart || notice.postedOn);
  const applyEnd = parseDateValue(notice.applyEnd);
  const noticeStatus = notice.noticeStatus || "";

  if (noticeStatus.includes("마감") || ["접수마감", "공고마감", "모집마감"].includes(noticeStatus)) {
    return "마감";
  }
  if (noticeStatus === "공고중" || noticeStatus === "접수중") {
    if (applyStart && today < applyStart) return "신청전";
    if (applyEnd && today > applyEnd) return "마감";
    return "진행중";
  }
  if (applyStart && today < applyStart) return "신청전";
  if (applyEnd && today > applyEnd) return "마감";
  if (applyStart || applyEnd) return "진행중";
  if (posted) {
    const days = (today - posted) / (1000 * 60 * 60 * 24);
    if (days > 90) return "마감";
    if (today < posted) return "신청전";
  }
  return "진행중";
}

function selectedStatusFilters() {
  return new Set(
    [...document.querySelectorAll('input[name="status-filter"]:checked')].map((el) => el.value),
  );
}

function noticeDetailHtml(notice) {
  const status = computeScheduleStatus(notice);
  const applyStart = notice.applyStart || notice.postedOn;
  const applyPeriod =
    applyStart || notice.applyEnd
      ? `${formatDateLabel(applyStart)} ~ ${formatDateLabel(notice.applyEnd)}`
      : "신청기간 정보 없음";
  const detailLink = notice.detailUrl
    ? `<a class="notice-detail-link" href="${escapeHtml(notice.detailUrl)}" target="_blank" rel="noopener noreferrer">원문 보기</a>`
    : "";

  return `
    <div class="notice-detail-header">
      <span class="schedule-badge status-${status}">${status}</span>
      <h3 class="notice-detail-title">${escapeHtml(notice.title)}</h3>
    </div>
    <dl class="notice-detail-meta">
      <div><dt>공고일</dt><dd>${formatDateLabel(notice.postedOn)}</dd></div>
      <div><dt>신청기간</dt><dd>${escapeHtml(applyPeriod)}</dd></div>
      <div><dt>주택 수</dt><dd>${Number(notice.rowCount || 0).toLocaleString("ko-KR")}건</dd></div>
    </dl>
    ${detailLink}
  `;
}

function renderNoticeDetail(notice) {
  if (!notice) {
    noticeDetailEl.innerHTML = "";
    return;
  }
  noticeDetailEl.innerHTML = noticeDetailHtml(notice);
}

function renderNoticeBoard(list) {
  noticeBoardList.innerHTML = "";
  if (!list.length) {
    noticeBoardList.innerHTML = `<p class="notice-board-empty">선택한 조건에 맞는 공고가 없습니다.</p>`;
    return;
  }

  for (const notice of list) {
    const status = computeScheduleStatus(notice);
    const applyStart = notice.applyStart || notice.postedOn;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "notice-board-item";
    button.dataset.id = notice.id;
    button.setAttribute("role", "option");
    button.innerHTML = `
      <span class="schedule-badge status-${status}">${status}</span>
      <span class="notice-board-date">${formatDateLabel(notice.postedOn)}</span>
      <span class="notice-board-date">${formatDateLabel(applyStart)}</span>
      <span class="notice-board-date">${formatDateLabel(notice.applyEnd)}</span>
      <span class="notice-board-count">${Number(notice.rowCount || 0).toLocaleString("ko-KR")}</span>
      <span class="notice-board-title">${escapeHtml(notice.title)}</span>
    `;
    button.addEventListener("click", () => openNotice(notice.id));
    noticeBoardList.appendChild(button);
  }
}

function updateAppNav(view) {
  currentView = view;
  for (const step of appNav.querySelectorAll(".app-step")) {
    const stepName = step.dataset.step;
    step.classList.toggle("is-current", stepName === view);
    step.classList.toggle("is-done", stepName === "board" && view === "detail");
  }
}

function showView(view) {
  viewBoard.hidden = view !== "board";
  viewDetail.hidden = view !== "detail";
  updateAppNav(view);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function companies(year) {
  return unique(notices.filter((n) => n.year === year).map((n) => n.company));
}

function noticesFor(year, company) {
  const activeStatuses = selectedStatusFilters();
  return notices
    .filter((n) => n.year === year && n.company === company)
    .filter((n) => activeStatuses.has(computeScheduleStatus(n)))
    .sort((a, b) => {
      const aDate = parseDateValue(a.postedOn || a.sourceFile)?.getTime() || 0;
      const bDate = parseDateValue(b.postedOn || b.sourceFile)?.getTime() || 0;
      return bDate - aDate;
    });
}

function formatPyeong(x) {
  if (x % PYEONG === 0) return `${Math.trunc(x / PYEONG)}평`;
  return `${(x / PYEONG).toFixed(1)}평`;
}

function formatDeposit(x) {
  const eok = x >= 100_000_000 ? `${Math.trunc(x / 100_000_000)}억` : "";
  const man = Math.trunc((x / 10_000) % 10_000);
  const rest = man > 0 ? ` ${man}만원` : "원";
  return `${eok}${rest}`;
}

function formatRent(x) {
  const man = x >= 10_000 ? `${Math.trunc(x / 10_000)}만` : "";
  const rest = Math.trunc(x % 10_000) > 0 ? ` ${Math.trunc(x % 10_000)}원` : "원";
  return `${man}${rest}`;
}

function formatWon(n) {
  return `${Number(n).toLocaleString("ko-KR")}원`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function selectedCheckboxValues(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
}

function renderTypeFilters(rows, filterCols) {
  typeFilters.innerHTML = "";
  filterCols.forEach((col, index) => {
    const values = unique(rows.map((row) => row[col]));
    if (values.length <= 1) return;
    const group = document.createElement("div");
    group.className = "checkbox-group";
    const title = document.createElement("span");
    title.textContent = col;
    group.appendChild(title);
    for (const value of sortValues(values)) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = `filter-${index}`;
      input.value = String(value);
      input.checked = true;
      input.addEventListener("change", renderTable);
      label.appendChild(input);
      label.appendChild(document.createTextNode(String(value)));
      group.appendChild(label);
    }
    typeFilters.appendChild(group);
  });
}

function activeFilterValues(rows, filterCols, index) {
  const values = unique(rows.map((row) => row[colName(filterCols, index)]));
  if (values.length <= 1) return values.map((v) => String(v));
  return selectedCheckboxValues(`filter-${index}`);
}

function colName(filterCols, index) {
  return filterCols[index];
}

function syncRangePair(minInput, maxInput) {
  let minVal = Number(minInput.value);
  let maxVal = Number(maxInput.value);
  if (minVal > maxVal) {
    const prev = minVal;
    minVal = maxVal;
    maxVal = prev;
    minInput.value = String(minVal);
    maxInput.value = String(maxVal);
  }
  return [minVal, maxVal];
}

function setupRangeFilters(rows) {
  const areas = rows.map((row) => Number(row["전용면적"]));
  const deposits = rows.map((row) => Number(row["보증금"]));
  const minArea = Math.floor(Math.min(...areas));
  const maxArea = Math.ceil(Math.max(...areas));
  const minDeposit = Math.floor(Math.min(...deposits) / DEPOSIT_STEP) * DEPOSIT_STEP;
  const maxDeposit = Math.ceil(Math.max(...deposits) / DEPOSIT_STEP) * DEPOSIT_STEP;

  areaMinInput.min = String(minArea);
  areaMaxInput.min = String(minArea);
  areaMinInput.max = String(maxArea);
  areaMaxInput.max = String(maxArea);
  areaMinInput.value = String(minArea);
  areaMaxInput.value = String(maxArea);

  depositMinInput.min = String(minDeposit);
  depositMaxInput.min = String(minDeposit);
  depositMaxInput.max = String(maxDeposit);
  depositMaxInput.max = String(maxDeposit);
  depositMinInput.value = String(minDeposit);
  depositMaxInput.value = String(maxDeposit);

  updateRangeLabels();
}

function updateRangeLabels() {
  const [areaMin, areaMax] = syncRangePair(areaMinInput, areaMaxInput);
  const [depositMin, depositMax] = syncRangePair(depositMinInput, depositMaxInput);
  areaValues.textContent = `${areaMin.toFixed(1)} ~ ${areaMax.toFixed(1)}`;
  depositValues.textContent = `${formatWon(depositMin)} ~ ${formatWon(depositMax)}`;
}

function decorateRows(rows, showCols) {
  return rows.map((row) => {
    const next = { ...row };
    next["전용면적(평)"] = formatPyeong(Number(row["전용면적"]));
    next["보증금(억원)"] = formatDeposit(Number(row["보증금"]));
    if ("월임대료" in row) next["월임대료(만원)"] = formatRent(Number(row["월임대료"]));
    const extra =
      "월임대료" in row
        ? ["전용면적(평)", "보증금(억원)", "월임대료(만원)", "네이버지도"]
        : ["전용면적(평)", "보증금(억원)", "네이버지도"];
    const ordered = {};
    for (const col of [...showCols.slice(0, -1), ...extra]) {
      if (col in next) ordered[col] = next[col];
    }
    return ordered;
  });
}

function hideUniqueColumns(rows, showCols) {
  if (!rows.length) return { rows, visibleCols: [] };
  const drop = new Set();
  for (const col of showCols) {
    const values = unique(rows.map((row) => row[col]));
    if (values.length === 1) drop.add(col);
  }
  const visibleCols = Object.keys(rows[0]).filter((col) => !drop.has(col));
  const nextRows = rows.map((row) => {
    const out = {};
    for (const col of visibleCols) out[col] = row[col];
    return out;
  });
  return { rows: nextRows, visibleCols };
}

function dedupRows(rows, filterCols) {
  if (!rows.length) return rows;
  const columns = Object.keys(rows[0]);
  const keyCols = ["시도", "시군구", "주소", "주택명", ...filterCols].filter((col) =>
    columns.includes(col),
  );
  const valueCols = ["전용면적", "보증금", "월임대료"].filter((col) => columns.includes(col));
  if (!keyCols.length || !valueCols.length) return rows;

  const groups = new Map();
  for (const row of rows) {
    const key = JSON.stringify(keyCols.map((col) => row[col]));
    if (!groups.has(key)) {
      groups.set(key, {
        sample: row,
        count: 0,
        min: Object.fromEntries(valueCols.map((col) => [col, Number(row[col])])),
        max: Object.fromEntries(valueCols.map((col) => [col, Number(row[col])])),
      });
    }
    const group = groups.get(key);
    group.count += 1;
    for (const col of valueCols) {
      const n = Number(row[col]);
      group.min[col] = Math.min(group.min[col], n);
      group.max[col] = Math.max(group.max[col], n);
    }
  }

  return [...groups.values()].map((group) => {
    const out = {};
    for (const col of keyCols) out[col] = group.sample[col];
    out["주택수"] = group.count;
    for (const col of valueCols) {
      const min = group.min[col];
      const max = group.max[col];
      out[col] = min !== max ? `${min} ~ ${max}` : `${min}`;
    }
    out["네이버지도"] = `https://map.naver.com/p/search/${group.sample["주소"]}`;
    return out;
  });
}

function cellHtml(col, value) {
  if (col === "네이버지도" && value) {
    return `<a href="${escapeHtml(value)}" target="_blank" rel="noopener noreferrer">지도로 보기</a>`;
  }
  if (col === "안심전세포털" && value) {
    return `<a href="${escapeHtml(value)}" target="_blank" rel="noopener noreferrer">안심전세포털로 보기</a>`;
  }
  return escapeHtml(value);
}

function renderTable() {
  if (!currentData) return;
  const { rows, showCols, filterCols } = currentData;
  const sido = sidoSelect.value;
  const sigungu = sigunguSelect.value;
  const sidoRows = sido === "전체" ? rows : rows.filter((row) => row["시도"] === sido);
  const sigunguOptions = ["전체", ...sortValues(unique(sidoRows.map((row) => row["시군구"])))];
  if (!sigunguOptions.includes(sigungu)) {
    fillSelect(sigunguSelect, sigunguOptions, "전체");
  }

  updateRangeLabels();
  const [areaMin, areaMax] = syncRangePair(areaMinInput, areaMaxInput);
  const [depositMin, depositMax] = syncRangePair(depositMinInput, depositMaxInput);
  const filter0 = new Set(activeFilterValues(rows, filterCols, 0));
  const filter1 = new Set(activeFilterValues(rows, filterCols, 1));

  let filtered = rows.filter((row) => {
    if (sido !== "전체" && row["시도"] !== sido) return false;
    if (sigunguSelect.value !== "전체" && row["시군구"] !== sigunguSelect.value) return false;
    if (!filter0.has(String(row[filterCols[0]]))) return false;
    if (!filter1.has(String(row[filterCols[1]]))) return false;
    if (Number(row["전용면적"]) < areaMin || Number(row["전용면적"]) > areaMax) return false;
    if (Number(row["보증금"]) < depositMin || Number(row["보증금"]) > depositMax) return false;
    return true;
  });

  filtered = decorateRows(filtered, showCols);
  const hidden = hideUniqueColumns(filtered, showCols);
  filtered = hidden.rows;
  if (dedupToggle.checked) {
    filtered = dedupRows(filtered, filterCols);
  }

  const cols = filtered.length ? Object.keys(filtered[0]) : hidden.visibleCols;
  resultHeading.textContent = `주택 리스트 조회 (총 ${filtered.length}건)`;
  tableHead.innerHTML = `<tr>${cols.map((col) => `<th>${escapeHtml(col)}</th>`).join("")}</tr>`;
  tableBody.innerHTML = filtered
    .map((row) => `<tr>${cols.map((col) => `<td>${cellHtml(col, row[col])}</td>`).join("")}</tr>`)
    .join("");
}

function renderRegionFilters(rows) {
  const sidoValues = ["전체", ...sortValues(unique(rows.map((row) => row["시도"])))];
  fillSelect(sidoSelect, sidoValues, "전체");
  const sigunguValues = ["전체", ...sortValues(unique(rows.map((row) => row["시군구"])))];
  fillSelect(sigunguSelect, sigunguValues, "전체");
}

async function fetchNoticeData(notice) {
  showStatus("공고 데이터를 불러오는 중입니다.");
  try {
    const res = await fetch(encodeURI(notice.dataFile));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentData = await res.json();
    showStatus("");
    return true;
  } catch (err) {
    currentData = null;
    showStatus(`공고 데이터를 불러오지 못했습니다. ${err.message}`, true);
    return false;
  }
}

function setupHousingView() {
  if (!currentData) return;
  renderRegionFilters(currentData.rows);
  renderTypeFilters(currentData.rows, currentData.filterCols);
  setupRangeFilters(currentData.rows);
  dedupToggle.checked = false;
  renderTable();
}

async function openNotice(id) {
  selectedNoticeId = id;
  currentNotice = notices.find((n) => n.id === id);
  if (!currentNotice) {
    showStatus("공고를 찾을 수 없습니다.", true);
    return;
  }

  currentData = null;
  renderNoticeDetail(currentNotice);
  showView("detail");
  tableHead.innerHTML = "";
  tableBody.innerHTML = "";
  resultHeading.textContent = "주택 리스트 조회 (총 0건)";

  const ok = await fetchNoticeData(currentNotice);
  if (ok) setupHousingView();
}

function refreshBoard() {
  const year = yearSelect.value;
  const companyOptions = companies(year);
  const previousCompany = companySelect.value;
  const company = companyOptions.includes(previousCompany)
    ? previousCompany
    : companyOptions[0];
  fillSelect(companySelect, companyOptions, company);

  const list = noticesFor(year, companySelect.value);
  renderNoticeBoard(list);

  if (!list.length && currentView === "board") {
    showStatus("선택한 상태 조건에 맞는 공고가 없습니다.", true);
  } else if (currentView === "board") {
    showStatus("");
  }
}

function bindEvents() {
  yearSelect.addEventListener("change", refreshBoard);
  companySelect.addEventListener("change", refreshBoard);
  backToBoardBtn.addEventListener("click", () => {
    showView("board");
    showStatus("");
  });

  for (const step of appNav.querySelectorAll(".app-step")) {
    step.addEventListener("click", () => {
      const target = step.dataset.step;
      if (target === "board") {
        showView("board");
        showStatus("");
        return;
      }
      if (target === "detail" && currentNotice && currentData) {
        renderNoticeDetail(currentNotice);
        setupHousingView();
        showView("detail");
        showStatus("");
      }
    });
  }

  sidoSelect.addEventListener("change", () => {
    if (!currentData) return;
    const sido = sidoSelect.value;
    const source =
      sido === "전체" ? currentData.rows : currentData.rows.filter((row) => row["시도"] === sido);
    fillSelect(
      sigunguSelect,
      ["전체", ...sortValues(unique(source.map((row) => row["시군구"])))],
      "전체",
    );
    renderTable();
  });
  sigunguSelect.addEventListener("change", renderTable);
  areaMinInput.addEventListener("input", renderTable);
  areaMaxInput.addEventListener("input", renderTable);
  depositMinInput.addEventListener("input", renderTable);
  depositMaxInput.addEventListener("input", renderTable);
  dedupToggle.addEventListener("change", renderTable);
  for (const input of document.querySelectorAll('input[name="status-filter"]')) {
    input.addEventListener("change", refreshBoard);
  }
}

async function init() {
  bindEvents();
  showView("board");
  try {
    const res = await fetch("data/index.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    notices = payload.notices || [];
    if (!notices.length) {
      showStatus("표시할 청약 공고가 없습니다.", true);
      return;
    }
    fillSelect(yearSelect, years(), years()[0]);
    refreshBoard();
  } catch (err) {
    showStatus(`공고 목록을 불러오지 못했습니다. ${err.message}`, true);
  }
}

init();
