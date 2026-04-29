let trendChart = null;
let spendChart = null;
let ctrChart = null;
let conversionsChart = null;
let dashboardData = [];
let selectedEntityId = "";
let selectedLevel = "campaign";

const chartColors = {
    gold: "#d9b44a",
    goldStrong: "#ffd66b",
    green: "#34d399",
    blue: "#60a5fa",
    red: "#f87171",
    text: "#d7c27a",
    grid: "rgba(215, 194, 122, 0.12)"
};

const levelLabels = {
    campaign: "Campanha",
    adset: "Conjunto de anuncio",
    ad: "Anuncio"
};

function getEl(id) {
    return document.getElementById(id);
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();

    if (!response.ok || result.status === "error") {
        throw new Error(result.message || "Erro ao comunicar com a API.");
    }

    return result;
}

function numberValue(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

function formatNumber(value) {
    return Math.round(numberValue(value)).toLocaleString("pt-BR");
}

function formatCurrency(value) {
    return numberValue(value).toLocaleString("pt-BR", {
        style: "currency",
        currency: "BRL",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatPercent(value) {
    return numberValue(value).toFixed(2).replace(".", ",") + "%";
}

function formatDecimal(value) {
    return numberValue(value).toFixed(2).replace(".", ",");
}

function formatDate(dateStr) {
    if (!dateStr) return "--";
    const [year, month, day] = dateStr.split("-");
    return year && month && day ? `${day}/${month}/${year}` : dateStr;
}

function setText(id, value) {
    const element = getEl(id);
    if (element) element.textContent = value;
}

function setStatus(message, type = "info") {
    const info = getEl("infoMessage");
    const error = getEl("errorMessage");

    if (error) {
        error.style.display = type === "error" ? "block" : "none";
        if (type === "error") error.textContent = message;
    }

    if (info) {
        info.style.display = type === "error" || !message ? "none" : "block";
        info.textContent = type === "error" ? "" : message;
    }
}

function setLoading(isLoading) {
    const btnRefresh = getEl("btnRefresh");
    const loading = getEl("loading");

    if (btnRefresh) btnRefresh.disabled = isLoading;
    if (loading) loading.style.display = isLoading ? "flex" : "none";
}

function entityKey(row) {
    if (selectedLevel === "ad") return row.ad_id || row.ad_name || "";
    if (selectedLevel === "adset") return row.adset_id || row.adset_name || "";
    return row.campaign_id || row.campaign_name || "";
}

function entityLabel(row) {
    if (selectedLevel === "ad") return row.ad_name || row.ad_id || "Sem anuncio";
    if (selectedLevel === "adset") return row.adset_name || row.adset_id || "Sem conjunto";
    return row.campaign_name || row.campaign_id || "Sem campanha";
}

function getFilteredData() {
    if (!selectedEntityId) return dashboardData;
    return dashboardData.filter((row) => entityKey(row) === selectedEntityId);
}

function calculateKPIs(data) {
    const totals = data.reduce(
        (acc, row) => {
            acc.impressions += numberValue(row.impressions);
            acc.clicks += numberValue(row.clicks);
            acc.spend += numberValue(row.spend);
            acc.leads += numberValue(row.lead);
            acc.landingPageViews += numberValue(row.landing_page_views);
            acc.purchases += numberValue(row.website_purchases);
            acc.conversionValue += numberValue(row.conversion_value);
            return acc;
        },
        {
            impressions: 0,
            clicks: 0,
            spend: 0,
            leads: 0,
            landingPageViews: 0,
            purchases: 0,
            conversionValue: 0
        }
    );

    return {
        cpm: totals.impressions ? (totals.spend / totals.impressions) * 1000 : 0,
        ctr: totals.impressions ? (totals.clicks / totals.impressions) * 100 : 0,
        cpc: totals.clicks ? totals.spend / totals.clicks : 0,
        cpl: totals.leads ? totals.spend / totals.leads : 0,
        costLandingPageView: totals.landingPageViews ? totals.spend / totals.landingPageViews : 0,
        cpa: totals.purchases ? totals.spend / totals.purchases : 0,
        roas: totals.spend ? totals.conversionValue / totals.spend : 0,
        conversionValue: totals.conversionValue,
        purchases: totals.purchases
    };
}

function updateKPIs(kpis) {
    setText("kpiCPM", formatCurrency(kpis.cpm));
    setText("kpiCTR", formatPercent(kpis.ctr));
    setText("kpiCPC", formatCurrency(kpis.cpc));
    setText("kpiCPL", formatCurrency(kpis.cpl));
    setText("kpiCostLPV", formatCurrency(kpis.costLandingPageView));
    setText("kpiCPA", formatCurrency(kpis.cpa));
    setText("kpiROAS", formatDecimal(kpis.roas));
    setText("kpiConversionValue", formatCurrency(kpis.conversionValue));
    setText("kpiPurchases", formatNumber(kpis.purchases));
}

function updateEntitySelect(data) {
    const select = getEl("entitySelect");
    if (!select) return;

    const previousValue = select.value || selectedEntityId;
    const entities = new Map();

    data.forEach((row) => {
        const key = entityKey(row);
        if (key) entities.set(key, entityLabel(row));
    });

    const sortedEntities = [...entities.entries()].sort((a, b) => a[1].localeCompare(b[1], "pt-BR"));
    select.innerHTML = `<option value="">Todos os ${levelLabels[selectedLevel].toLowerCase()}s</option>`;

    sortedEntities.forEach(([id, name]) => {
        const option = document.createElement("option");
        option.value = id;
        option.textContent = name;
        select.appendChild(option);
    });

    select.disabled = sortedEntities.length === 0;
    select.value = entities.has(previousValue) ? previousValue : "";
    selectedEntityId = select.value;
}

function sortedByDate(data, direction = "asc") {
    return [...data].sort((a, b) => {
        const left = new Date(a.date_start || 0).getTime();
        const right = new Date(b.date_start || 0).getTime();
        return direction === "asc" ? left - right : right - left;
    });
}

function destroyCharts() {
    [trendChart, spendChart, ctrChart, conversionsChart].forEach((chart) => {
        if (chart) chart.destroy();
    });
    trendChart = null;
    spendChart = null;
    ctrChart = null;
    conversionsChart = null;
}

function baseChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
            legend: {
                labels: { color: chartColors.text, boxWidth: 12, usePointStyle: true }
            },
            tooltip: {
                backgroundColor: "#111111",
                borderColor: "rgba(217, 180, 74, 0.35)",
                borderWidth: 1,
                titleColor: "#ffffff",
                bodyColor: "#f8e7a1"
            }
        },
        scales: {
            x: { ticks: { color: chartColors.text, maxRotation: 0 }, grid: { color: chartColors.grid } },
            y: { beginAtZero: true, ticks: { color: chartColors.text }, grid: { color: chartColors.grid } }
        }
    };
}

function aggregateByDate(data) {
    const daily = new Map();

    data.forEach((row) => {
        const date = row.date_start || "";
        if (!daily.has(date)) {
            daily.set(date, {
                date_start: date,
                impressions: 0,
                clicks: 0,
                spend: 0,
                purchases: 0,
                conversion_value: 0
            });
        }

        const current = daily.get(date);
        current.impressions += numberValue(row.impressions);
        current.clicks += numberValue(row.clicks);
        current.spend += numberValue(row.spend);
        current.purchases += numberValue(row.website_purchases);
        current.conversion_value += numberValue(row.conversion_value);
    });

    return [...daily.values()]
        .map((row) => ({
            ...row,
            ctr: row.impressions ? (row.clicks / row.impressions) * 100 : 0
        }))
        .sort((a, b) => new Date(a.date_start || 0) - new Date(b.date_start || 0));
}

function updateCharts(data) {
    const sorted = aggregateByDate(data);
    const labels = sorted.map((row) => formatDate(row.date_start).slice(0, 5));
    const impressions = sorted.map((row) => numberValue(row.impressions));
    const clicks = sorted.map((row) => numberValue(row.clicks));
    const spend = sorted.map((row) => numberValue(row.spend));
    const ctr = sorted.map((row) => numberValue(row.ctr));
    const purchases = sorted.map((row) => numberValue(row.purchases));
    const conversionValue = sorted.map((row) => numberValue(row.conversion_value));
    const options = baseChartOptions();

    destroyCharts();

    const trendCtx = getEl("chartTrend");
    if (trendCtx) {
        trendChart = new Chart(trendCtx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Impressoes",
                        data: impressions,
                        borderColor: chartColors.goldStrong,
                        backgroundColor: "rgba(255, 214, 107, 0.14)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 2
                    },
                    {
                        label: "Cliques",
                        data: clicks,
                        borderColor: chartColors.blue,
                        backgroundColor: "rgba(96, 165, 250, 0.12)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 2
                    }
                ]
            },
            options
        });
    }

    const spendCtx = getEl("chartSpend");
    if (spendCtx) {
        spendChart = new Chart(spendCtx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Valor usado",
                        data: spend,
                        backgroundColor: "rgba(217, 180, 74, 0.72)",
                        borderColor: chartColors.goldStrong,
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options
        });
    }

    const ctrCtx = getEl("chartCTR");
    if (ctrCtx) {
        ctrChart = new Chart(ctrCtx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "CTR",
                        data: ctr,
                        borderColor: chartColors.green,
                        backgroundColor: "rgba(52, 211, 153, 0.12)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 2
                    }
                ]
            },
            options
        });
    }

    const conversionsCtx = getEl("chartConversions");
    if (conversionsCtx) {
        conversionsChart = new Chart(conversionsCtx, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: "Compras",
                        data: purchases,
                        backgroundColor: "rgba(52, 211, 153, 0.72)",
                        borderRadius: 5
                    },
                    {
                        label: "Valor de conversao",
                        data: conversionValue,
                        backgroundColor: "rgba(96, 165, 250, 0.7)",
                        borderRadius: 5
                    }
                ]
            },
            options
        });
    }
}

function updateTable(data) {
    const tbody = getEl("tableBody");
    if (!tbody) return;

    tbody.innerHTML = "";
    sortedByDate(data, "desc").forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${formatDate(row.date_start)}</td>
            <td title="${entityLabel(row)}">${entityLabel(row)}</td>
            <td>${formatCurrency(row.cpm)}</td>
            <td>${formatPercent(row.ctr)}</td>
            <td>${formatCurrency(row.cpc)}</td>
            <td>${formatCurrency(row.cpl)}</td>
            <td>${formatCurrency(row.cost_per_landing_page_view)}</td>
            <td>${formatCurrency(row.cpa)}</td>
            <td>${formatDecimal(row.roas)}</td>
            <td>${formatCurrency(row.conversion_value)}</td>
            <td>${formatNumber(row.website_purchases)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderVisibleData() {
    const visibleData = getFilteredData();
    updateKPIs(calculateKPIs(visibleData));
    updateCharts(visibleData);
    updateTable(visibleData);
}

function renderDashboard(data, sourceMessage) {
    dashboardData = Array.isArray(data) ? data : [];
    updateEntitySelect(dashboardData);

    if (!dashboardData.length) {
        setStatus("Selecione um periodo e clique em Atualizar Dados para carregar os dados da API.");
        renderVisibleData();
        return;
    }

    renderVisibleData();
    setStatus(sourceMessage || "");
    updateLastUpdate();
}

async function loadDashboard() {
    try {
        const result = await requestJson("/api/data");
        renderDashboard(result.data || [], result.data && result.data.length ? "" : null);
    } catch (error) {
        setStatus("Erro ao carregar dados: " + error.message, "error");
    }
}

async function refreshData() {
    const startDate = getEl("startDate")?.value;
    const endDate = getEl("endDate")?.value;

    if (!startDate || !endDate) {
        setStatus("Selecione as datas de inicio e fim antes de atualizar os dados.", "error");
        return;
    }

    setLoading(true);
    setStatus("Atualizando dados da Meta...");

    try {
        const params = new URLSearchParams({ start_date: startDate, end_date: endDate, level: selectedLevel });
        const result = await requestJson("/api/update?" + params.toString(), { method: "POST" });
        selectedEntityId = "";
        renderDashboard(result.data || [], result.message || "Dados atualizados.");
    } catch (error) {
        setStatus("Erro ao atualizar dados: " + error.message, "error");
    } finally {
        setLoading(false);
    }
}

function updateLastUpdate() {
    const now = new Date();
    setText("lastUpdate", "Ultima atualizacao: " + now.toLocaleString("pt-BR"));
}

function setDefaultDateRange() {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 29);

    const toInputDate = (date) => date.toISOString().slice(0, 10);
    if (getEl("startDate") && !getEl("startDate").value) getEl("startDate").value = toInputDate(start);
    if (getEl("endDate") && !getEl("endDate").value) getEl("endDate").value = toInputDate(end);
}

document.addEventListener("DOMContentLoaded", () => {
    setDefaultDateRange();

    const levelSelect = getEl("levelSelect");
    if (levelSelect) {
        selectedLevel = levelSelect.value;
        levelSelect.addEventListener("change", () => {
            selectedLevel = levelSelect.value;
            selectedEntityId = "";
            dashboardData = [];
            updateEntitySelect([]);
            renderVisibleData();
            setStatus("Nivel alterado. Clique em Atualizar Dados para carregar os dados.");
        });
    }

    const entitySelect = getEl("entitySelect");
    if (entitySelect) {
        entitySelect.addEventListener("change", () => {
            selectedEntityId = entitySelect.value;
            renderVisibleData();
        });
    }

    loadDashboard();
});
