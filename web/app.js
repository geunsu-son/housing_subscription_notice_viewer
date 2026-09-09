const PYEONG = 3.305785;
const DEPOSIT_STEP = 10_000_000;

const yearSelect = document.getElementById("year-select");
const companySelect = document.getElementById("company-select");
const regionSelect = document.getElementById("region-select");
const noticeBoardList = document.getElementById("notice-board-list");
const noticeDetailEl = document.getElementById("notice-detail");
const viewBoard = document.getElementById("view-board");
const viewDetail = document.getElementById("view-detail");
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
const boardSortSelect = document.getElementById("board-sort");
const boardPageSizeSelect = document.getElementById("board-page-size");
const boardPaginationEl = document.getElementById("board-pagination");
const housingPageSizeSelect = document.getElementById("housing-page-size");
const housingPaginationEl = document.getElementById("housing-pagination");

let notices = [];
let currentNotice = null;
let currentData = null;
let selectedNoticeId = "";
let currentView = "board";
let boardFilteredList = [];
let boardPage = 1;
let housingFilteredRows = [];
let housingVisibleCols = [];
let housingPage = 1;
let housingSortCol = "";
let housingSortDir = "asc";

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

function compareText(a, b, dir = 1) {
  return String(a ?? "").localeCompare(String(b ?? ""), "ko") * dir;
}

function compareNumber(a, b, dir = 1) {
  const av = Number(a);
  const bv = Number(b);
  if (Number.isNaN(av) && Number.isNaN(bv)) return 0;
  if (Number.isNaN(av)) return 1;
  if (Number.isNaN(bv)) return -1;
  return (av - bv) * dir;
}

function compareDateValue(a, b, dir = 1) {
  const av = parseDateValue(a)?.getTime();
  const bv = parseDateValue(b)?.getTime();
  if (av == null && bv == null) return 0;
  if (av == null) return 1;
  if (bv == null) return -1;
  return (av - bv) * dir;
}

function paginateList(items, page, pageSize) {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize) || 1);
  const safePage = Math.min(Math.max(1, page), totalPages);
  const startIndex = (safePage - 1) * pageSize;
  const pageItems = items.slice(startIndex, startIndex + pageSize);
  return {
    items: pageItems,
    page: safePage,
    pageSize,
    total,
    totalPages,
    rangeStart: total ? startIndex + 1 : 0,
    rangeEnd: total ? startIndex + pageItems.length : 0,
  };
}

function renderPaginationControls(container, meta, onPageChange) {
  if (!container) return;
  if (!meta.total) {
    container.innerHTML = `<span class="pagination-summary">0건</span>`;
    return;
  }

  container.innerHTML = `
    <span class="pagination-summary">${meta.total.toLocaleString("ko-KR")}건 중 ${meta.rangeStart.toLocaleString("ko-KR")}-${meta.rangeEnd.toLocaleString("ko-KR")}</span>
    <div class="pagination-nav">
      <button type="button" class="btn-secondary pagination-btn" data-page="${meta.page - 1}" ${meta.page <= 1 ? "disabled" : ""}>이전</button>
      <span class="pagination-page">${meta.page} / ${meta.totalPages}</span>
      <button type="button" class="btn-secondary pagination-btn" data-page="${meta.page + 1}" ${meta.page >= meta.totalPages ? "disabled" : ""}>다음</button>
    </div>
  `;

  for (const button of container.querySelectorAll(".pagination-btn")) {
    button.addEventListener("click", () => {
      const nextPage = Number(button.dataset.page);
      if (!Number.isFinite(nextPage)) return;
      onPageChange(nextPage);
    });
  }
}

function sortNotices(list, sortKey) {
  const sorted = [...list];
  sorted.sort((a, b) => {
    switch (sortKey) {
      case "company-asc":
        return compareText(a.company, b.company) || compareText(a.title, b.title);
      case "region-asc":
        return compareText(a.regions, b.regions) || compareText(a.title, b.title);
      case "title-asc":
        return compareText(a.title, b.title);
      case "title-desc":
        return compareText(b.title, a.title);
      case "apply-asc":
        return compareDateValue(a.applyStart, b.applyStart) || compareText(a.title, b.title);
      case "apply-desc":
        return compareDateValue(b.applyStart, a.applyStart) || compareText(a.title, b.title);
      case "posted-asc":
        return (
          compareDateValue(a.postedOn || a.sourceFile, b.postedOn || b.sourceFile) ||
          compareText(a.title, b.title)
        );
      case "posted-desc":
      default:
        return (
          compareDateValue(b.postedOn || b.sourceFile, a.postedOn || a.sourceFile) ||
          compareText(a.title, b.title)
        );
    }
  });
  return sorted;
}

function sortRows(rows, col, dir) {
  if (!col || !rows.length) return rows;
  const multiplier = dir === "desc" ? -1 : 1;
  return [...rows].sort((a, b) => {
    const av = a[col];
    const bv = b[col];
    if (typeof av === "number" || typeof bv === "number") {
      return compareNumber(av, bv, multiplier);
    }
    const numeric = compareNumber(av, bv, 0);
    if (numeric !== 0 && !Number.isNaN(Number(av)) && !Number.isNaN(Number(bv))) {
      return numeric * multiplier;
    }
    return compareText(av, bv, multiplier);
  });
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
  const applyPeriod = formatApplyPeriod(notice) || "신청기간 정보 없음";
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

function formatApplyPeriod(notice, { fallbackPostedOn = true } = {}) {
  const applyStart = notice.applyStart || (fallbackPostedOn ? notice.postedOn : "");
  if (!applyStart && !notice.applyEnd) return "";
  return `${formatDateLabel(applyStart)} ~ ${formatDateLabel(notice.applyEnd)}`;
}

function renderNoticeBoard(list) {
  noticeBoardList.innerHTML = "";
  if (!list.length) {
    noticeBoardList.innerHTML = `<p class="notice-board-empty">선택한 조건에 맞는 공고가 없습니다.</p>`;
    return;
  }

  for (const notice of list) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "notice-board-item";
    if (notice.id === selectedNoticeId) button.classList.add("is-selected");
    button.dataset.id = notice.id;
    button.setAttribute("role", "option");
    button.innerHTML = `
      <span class="notice-board-company">${escapeHtml(notice.company || "")}</span>
      <span class="notice-board-region">${escapeHtml(notice.regions || "")}</span>
      <span class="notice-board-title">${escapeHtml(notice.title)}</span>
      <span class="notice-board-period">${escapeHtml(formatApplyPeriod(notice, { fallbackPostedOn: false }))}</span>
    `;
    button.addEventListener("click", () => openNotice(notice.id));
    noticeBoardList.appendChild(button);
  }
}

function renderBoardList() {
  const sortKey = boardSortSelect.value;
  const pageSize = Number(boardPageSizeSelect.value) || 20;
  boardFilteredList = sortNotices(boardFilteredList, sortKey);
  const meta = paginateList(boardFilteredList, boardPage, pageSize);
  boardPage = meta.page;
  renderNoticeBoard(meta.items);
  renderPaginationControls(boardPaginationEl, meta, (nextPage) => {
    boardPage = nextPage;
    renderBoardList();
  });
}

function showView(view) {
  currentView = view;
  viewBoard.hidden = view !== "board";
  viewDetail.hidden = view !== "detail";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function noticeRegions(notice) {
  if (!notice.regions) return [];
  return notice.regions
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

function companies(year) {
  return unique(notices.filter((n) => n.year === year).map((n) => n.company));
}

function regionsFor(year, company) {
  const values = new Set();
  for (const notice of notices.filter((n) => n.year === year && n.company === company)) {
    for (const region of noticeRegions(notice)) {
      values.add(region);
    }
  }
  return sortValues([...values]);
}

function noticesFor(year, company, region = "전체") {
  const activeStatuses = selectedStatusFilters();
  return notices
    .filter((n) => n.year === year && n.company === company)
    .filter((n) => region === "전체" || noticeRegions(n).includes(region))
    .filter((n) => activeStatuses.has(computeScheduleStatus(n)));
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

    const details = document.createElement("details");
    details.className = "collapsible-filter";
    details.open = values.length <= 4;

    const summary = document.createElement("summary");
    summary.className = "collapsible-filter-summary";
    summary.textContent = `${col} (${values.length})`;
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "collapsible-filter-body";

    for (const value of sortValues(values)) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.name = `filter-${index}`;
      input.value = String(value);
      input.checked = true;
      input.addEventListener("change", () => {
        housingPage = 1;
        renderTable();
      });
      label.appendChild(input);
      label.appendChild(document.createTextNode(String(value)));
      body.appendChild(label);
    }

    details.appendChild(body);
    typeFilters.appendChild(details);
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

function renderTableHead(cols) {
  tableHead.innerHTML = `<tr>${cols
    .map((col) => {
      const isSorted = housingSortCol === col;
      const sortClass = isSorted ? ` sorted-${housingSortDir}` : "";
      return `<th class="sortable${sortClass}" data-col="${escapeHtml(col)}" scope="col">${escapeHtml(col)}${isSorted ? (housingSortDir === "asc" ? " ▲" : " ▼") : ""}</th>`;
    })
    .join("")}</tr>`;

  for (const th of tableHead.querySelectorAll("th.sortable")) {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (housingSortCol === col) {
        housingSortDir = housingSortDir === "asc" ? "desc" : "asc";
      } else {
        housingSortCol = col;
        housingSortDir = "asc";
      }
      housingPage = 1;
      renderTable();
    });
  }
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
  housingVisibleCols = filtered.length ? Object.keys(filtered[0]) : hidden.visibleCols;
  if (dedupToggle.checked) {
    filtered = dedupRows(filtered, filterCols);
    housingVisibleCols = filtered.length ? Object.keys(filtered[0]) : housingVisibleCols;
  }

  if (housingSortCol && housingVisibleCols.includes(housingSortCol)) {
    filtered = sortRows(filtered, housingSortCol, housingSortDir);
  } else if (housingSortCol && !housingVisibleCols.includes(housingSortCol)) {
    housingSortCol = "";
    housingSortDir = "asc";
  }

  housingFilteredRows = filtered;
  const pageSize = Number(housingPageSizeSelect.value) || 20;
  const meta = paginateList(housingFilteredRows, housingPage, pageSize);
  housingPage = meta.page;

  resultHeading.textContent = `주택 리스트 조회 (총 ${meta.total.toLocaleString("ko-KR")}건)`;
  renderTableHead(housingVisibleCols);
  tableBody.innerHTML = meta.items
    .map(
      (row) =>
        `<tr>${housingVisibleCols.map((col) => `<td>${cellHtml(col, row[col])}</td>`).join("")}</tr>`,
    )
    .join("");
  renderPaginationControls(housingPaginationEl, meta, (nextPage) => {
    housingPage = nextPage;
    renderTable();
  });
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
  housingPage = 1;
  housingSortCol = "";
  housingSortDir = "asc";
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

  const regionOptions = regionsFor(year, companySelect.value);
  const previousRegion = regionSelect.value;
  const region = previousRegion === "전체" || regionOptions.includes(previousRegion)
    ? previousRegion
    : "전체";
  fillSelect(regionSelect, ["전체", ...regionOptions], region);

  boardFilteredList = noticesFor(year, companySelect.value, regionSelect.value);
  boardPage = 1;
  renderBoardList();

  if (!boardFilteredList.length && currentView === "board") {
    showStatus("선택한 조건에 맞는 공고가 없습니다.", true);
  } else if (currentView === "board") {
    showStatus("");
  }
}

function bindEvents() {
  boardSortSelect.addEventListener("change", () => {
    boardPage = 1;
    renderBoardList();
  });
  boardPageSizeSelect.addEventListener("change", () => {
    boardPage = 1;
    renderBoardList();
  });
  housingPageSizeSelect.addEventListener("change", () => {
    housingPage = 1;
    renderTable();
  });
  yearSelect.addEventListener("change", refreshBoard);
  companySelect.addEventListener("change", refreshBoard);
  regionSelect.addEventListener("change", refreshBoard);
  backToBoardBtn.addEventListener("click", () => {
    showView("board");
    showStatus("");
  });

  sidoSelect.addEventListener("change", () => {
    if (!currentData) return;
    housingPage = 1;
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
  sigunguSelect.addEventListener("change", () => {
    housingPage = 1;
    renderTable();
  });
  areaMinInput.addEventListener("input", () => {
    housingPage = 1;
    renderTable();
  });
  areaMaxInput.addEventListener("input", () => {
    housingPage = 1;
    renderTable();
  });
  depositMinInput.addEventListener("input", () => {
    housingPage = 1;
    renderTable();
  });
  depositMaxInput.addEventListener("input", () => {
    housingPage = 1;
    renderTable();
  });
  dedupToggle.addEventListener("change", () => {
    housingPage = 1;
    renderTable();
  });
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
