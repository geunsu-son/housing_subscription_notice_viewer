const PYEONG = 3.305785;
const DEPOSIT_STEP = 10_000_000;

const yearSelect = document.getElementById("year-select");
const companySelect = document.getElementById("company-select");
const noticeSelect = document.getElementById("notice-select");
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
  return unique(notices.map((n) => n.year));
}

function companies(year) {
  return unique(notices.filter((n) => n.year === year).map((n) => n.company));
}

function noticesFor(year, company) {
  return notices.filter((n) => n.year === year && n.company === company);
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
  depositMinInput.max = String(maxDeposit);
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

async function loadNotice() {
  const id = noticeSelect.value;
  currentNotice = notices.find((n) => n.id === id);
  if (!currentNotice) {
    currentData = null;
    showStatus("해당 연도의 청약 공고가 없습니다.", true);
    return;
  }
  showStatus("공고 데이터를 불러오는 중입니다.");
  try {
    const res = await fetch(encodeURI(currentNotice.dataFile));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    currentData = await res.json();
    showStatus("");
    renderRegionFilters(currentData.rows);
    renderTypeFilters(currentData.rows, currentData.filterCols);
    setupRangeFilters(currentData.rows);
    dedupToggle.checked = false;
    renderTable();
  } catch (err) {
    currentData = null;
    tableHead.innerHTML = "";
    tableBody.innerHTML = "";
    resultHeading.textContent = "주택 리스트 조회 (총 0건)";
    showStatus(`공고 데이터를 불러오지 못했습니다. ${err.message}`, true);
  }
}

function refreshNoticeOptions({ keepNotice = false } = {}) {
  const year = yearSelect.value;
  const companyOptions = companies(year);
  const previousCompany = companySelect.value;
  const company = companyOptions.includes(previousCompany)
    ? previousCompany
    : companyOptions[0];
  fillSelect(companySelect, companyOptions, company);

  const list = noticesFor(year, companySelect.value);
  const previousNotice = keepNotice ? noticeSelect.value : "";
  const selected = list.some((n) => n.id === previousNotice) ? previousNotice : list[0]?.id;
  noticeSelect.innerHTML = "";
  for (const notice of list) {
    const option = document.createElement("option");
    option.value = notice.id;
    option.textContent = notice.title;
    if (notice.id === selected) option.selected = true;
    noticeSelect.appendChild(option);
  }
  loadNotice();
}

function bindEvents() {
  yearSelect.addEventListener("change", () => refreshNoticeOptions());
  companySelect.addEventListener("change", () => refreshNoticeOptions());
  noticeSelect.addEventListener("change", () => loadNotice());
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
}

async function init() {
  bindEvents();
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
    refreshNoticeOptions();
  } catch (err) {
    showStatus(`공고 목록을 불러오지 못했습니다. ${err.message}`, true);
  }
}

init();
