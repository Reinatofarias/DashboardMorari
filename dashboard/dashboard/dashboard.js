let trendChart = null;
let spendChart = null;
let ctrChart = null;
let conversionsChart = null;
let dashboardData = [];

const chartColors = {
    gold: "#d9b44a",
    goldStrong: "#ffd66b",
    green: "#34d399",
    blue: "#60a5fa",
    red: "#f87171",
    text: "#d7c27a",
    grid: "rgba(215, 194, 122, 0.12)"
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

async function fetchCachedData() {
    return requestJson("/api/data");
}

function numberValue(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : 0;
}

function formatNumber(value) {
    return Math.round(numberValue(value)).toLocaleString("pt-BR");
}

function formatCompactNumber(value) {
    const num = numberValue(value);
    if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1).replace(".", ",") + "M";
    if (Math.abs(num) >= 1000) return (num / 1000).toFixed(1).replace(".", ",") + "K";
    return formatNumber(num);
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

function calculateKPIs(data) {
    const totals = data.reduce(
        (acc, row) => {
            acc.impressions += numberValue(row.impressions);
            acc.clicks += numberValue(row.clicks);
            acc.reach += numberValue(row.reach);
            acc.purchases += numberValue(row.website_purchases);
            acc.spend += numberValue(row.spend);
            acc.inlineClicks += numberValue(row.inline_link_clicks);
            return acc;
        },
        { impressions: 0, clicks: 0, reach: 0, purchases: 0, spend: 0, inlineClicks: 0 }
    );

    const ctr = totals.impressions ? (totals.clicks / totals.impressions) * 100 : 0;
    const cpa = totals.purchases ? totals.spend / totals.purchases : 0;
    const connectRate = totals.clicks ? (totals.inlineClicks / totals.clicks) * 100 : 0;

    return {
        impressions: totals.impressions,
        clicks: totals.clicks,
        reach: totals.reach,
        purchases: totals.purchases,
        cpa,
        costPerResult: cpa,
        spend: totals.spend,
        ctr,
        connectRate
    };
}

function updateKPIs(kpis) {
    setText("kpiImpressions", formatCompactNumber(kpis.impressions));
    setText("kpiClicks", formatCompactNumber(kpis.clicks));
    setText("kpiReach", formatCompactNumber(kpis.reach));
    setText("kpiPurchases", formatNumber(kpis.purchases));
    setText("kpiCPA", formatCurrency(kpis.cpa));
    setText("kpiCostPerResult", formatCurrency(kpis.costPerResult));
    setText("kpiSpend", formatCurrency(kpis.spend));
    setText("kpiCTR", formatPercent(kpis.ctr));
    setText("kpiConnectRate", formatPercent(kpis.connectRate));
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
                labels: {
                    color: chartColors.text,
                    boxWidth: 12,
                    usePointStyle: true
                }
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
            x: {
                ticks: { color: chartColors.text, maxRotation: 0 },
                grid: { color: chartColors.grid }
            },
            y: {
                beginAtZero: true,
                ticks: { color: chartColors.text },
                grid: { color: chartColors.grid }
            }
        }
    };
}

function updateCharts(data) {
    const sorted = sortedByDate(data);
    const labels = sorted.map((row) => formatDate(row.date_start).slice(0, 5));
    const impressions = sorted.map((row) => numberValue(row.impressions));
    const clicks = sorted.map((row) => numberValue(row.clicks));
    const spend = sorted.map((row) => numberValue(row.spend));
    const ctr = sorted.map((row) => numberValue(row.ctr));
    const addToCart = sorted.map((row) => numberValue(row.add_to_cart));
    const checkout = sorted.map((row) => numberValue(row.initiate_checkout));
    const purchases = sorted.map((row) => numberValue(row.website_purchases));
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
                        label: "Add to Cart",
                        data: addToCart,
                        backgroundColor: "rgba(96, 165, 250, 0.7)",
                        borderRadius: 5
                    },
                    {
                        label: "Checkout",
                        data: checkout,
                        backgroundColor: "rgba(217, 180, 74, 0.72)",
                        borderRadius: 5
                    },
                    {
                        label: "Compras",
                        data: purchases,
                        backgroundColor: "rgba(52, 211, 153, 0.72)",
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
            <td>${formatNumber(row.impressions)}</td>
            <td>${formatNumber(row.clicks)}</td>
            <td>${formatNumber(row.reach)}</td>
            <td>${formatCurrency(row.spend)}</td>
            <td>${formatPercent(row.ctr)}</td>
            <td>${formatNumber(row.website_purchases)}</td>
            <td>${formatCurrency(row.cpa)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDashboard(data, sourceMessage) {
    dashboardData = Array.isArray(data) ? data : [];

    if (!dashboardData.length) {
        setStatus("Selecione um periodo e clique em Atualizar Dados para carregar os dados da API.");
        updateKPIs(calculateKPIs([]));
        destroyCharts();
        updateTable([]);
        return;
    }

    updateKPIs(calculateKPIs(dashboardData));
    updateCharts(dashboardData);
    updateTable(dashboardData);
    setStatus(sourceMessage || "");
    updateLastUpdate();
}

async function loadDashboard() {
    try {
        const result = await fetchCachedData();
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
        const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
        const result = await requestJson("/api/update?" + params.toString(), { method: "POST" });
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
    loadDashboard();
});
