let trendChart, spendChart, ctrChart, conversionsChart;
let dashboardData = [];

async function fetchData() {
    try {
        const response = await fetch('/api/data');
        const result = await response.json();
        if (result.status === 'error') {
            throw new Error(result.message);
        }
        return result;
    } catch (error) {
        console.error('Erro ao buscar dados:', error);
        showError('Erro ao carregar dados: ' + error.message);
        return null;
    }
}

function formatNumber(num) {
    const n = parseInt(num) || 0;
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toLocaleString('pt-BR');
}

function formatCurrency(value) {
    const num = parseFloat(value) || 0;
    return 'R$ ' + num.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatPercent(value) {
    const num = parseFloat(value) || 0;
    return num.toFixed(2).replace('.', ',') + '%';
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
        return parts[2] + '/' + parts[1] + '/' + parts[0];
    }
    return dateStr;
}

function calculateKPIs(data) {
    if (!data || data.length === 0) return null;
    
    const aggregated = data.reduce((acc, row) => {
        acc.impressions += parseInt(row.impressions || 0);
        acc.clicks += parseInt(row.clicks || 0);
        acc.reach += parseInt(row.reach || 0);
        acc.spend += parseFloat(row.spend || 0);
        acc.purchases += parseInt(row.website_purchases || 0);
        acc.inline_clicks += parseInt(row.inline_link_clicks || 0);
        return acc;
    }, { impressions: 0, clicks: 0, reach: 0, spend: 0, purchases: 0, inline_clicks: 0 });
    
    const ctr = aggregated.impressions > 0 ? (aggregated.clicks / aggregated.impressions * 100) : 0;
    const cpa = aggregated.purchases > 0 ? aggregated.spend / aggregated.purchases : 0;
    const connectRate = aggregated.clicks > 0 ? (aggregated.inline_clicks / aggregated.clicks * 100) : 0;
    
    return {
        impressions: aggregated.impressions,
        clicks: aggregated.clicks,
        reach: aggregated.reach,
        results: aggregated.purchases,
        cpa: cpa,
        costPerResult: cpa,
        spend: aggregated.spend,
        ctr: ctr,
        connectRate: connectRate,
        purchases: aggregated.purchases
    };
}

function updateKPIs(kpis) {
    if (!kpis) return;
    document.getElementById('kpiImpressions').textContent = formatNumber(kpis.impressions);
    document.getElementById('kpiClicks').textContent = formatNumber(kpis.clicks);
    document.getElementById('kpiReach').textContent = formatNumber(kpis.reach);
    document.getElementById('kpiPurchases').textContent = formatNumber(kpis.purchases);
    document.getElementById('kpiCPA').textContent = formatCurrency(kpis.cpa);
    document.getElementById('kpiCostPerResult').textContent = formatCurrency(kpis.costPerResult);
    document.getElementById('kpiSpend').textContent = formatCurrency(kpis.spend);
    document.getElementById('kpiCTR').textContent = formatPercent(kpis.ctr);
    document.getElementById('kpiConnectRate').textContent = formatPercent(kpis.connectRate);
}

function destroyChart(chart) {
    if (chart) {
        chart.destroy();
        chart = null;
    }
}

function updateCharts(data) {
    if (!data || data.length === 0) return;
    
    const sortedData = [...data].sort((a, b) => new Date(a.date_start) - new Date(b.date_start));
    
    const labels = sortedData.map(d => {
        const date = new Date(d.date_start);
        return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    });
    
    const impressions = sortedData.map(d => parseInt(d.impressions || 0));
    const clicks = sortedData.map(d => parseInt(d.clicks || 0));
    const spend = sortedData.map(d => parseFloat(d.spend || 0));
    const ctr = sortedData.map(d => parseFloat(d.ctr || 0));
    const addToCart = sortedData.map(d => parseInt(d.add_to_cart || 0));
    const checkout = sortedData.map(d => parseInt(d.initiate_checkout || 0));
    const purchases = sortedData.map(d => parseInt(d.website_purchases || 0));
    
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#C5A028' }
            }
        },
        scales: {
            x: {
                ticks: { color: '#C5A028' },
                grid: { color: '#333333' }
            },
            y: {
                ticks: { color: '#C5A028' },
                grid: { color: '#333333' }
            }
        }
    };
    
    const trendCtx = document.getElementById('chartTrend');
    if (trendCtx) {
        destroyChart(trendChart);
        trendChart = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Impressoes',
                        data: impressions,
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Cliques',
                        data: clicks,
                        borderColor: '#C5A028',
                        backgroundColor: 'rgba(197, 160, 40, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: chartOptions
        });
    }
    
    const spendCtx = document.getElementById('chartSpend');
    if (spendCtx) {
        destroyChart(spendChart);
        spendChart = new Chart(spendCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Gasto (R$)',
                    data: spend,
                    backgroundColor: 'rgba(255, 215, 0, 0.6)',
                    borderColor: '#FFD700',
                    borderWidth: 1
                }]
            },
            options: chartOptions
        });
    }
    
    const ctrCtx = document.getElementById('chartCTR');
    if (ctrCtx) {
        destroyChart(ctrChart);
        ctrChart = new Chart(ctrCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CTR (%)',
                    data: ctr,
                    borderColor: '#FFD700',
                    backgroundColor: 'rgba(255, 215, 0, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: chartOptions
        });
    }
    
    const convCtx = document.getElementById('chartConversions');
    if (convCtx) {
        destroyChart(conversionsChart);
        conversionsChart = new Chart(convCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Add to Cart',
                        data: addToCart,
                        backgroundColor: 'rgba(197, 160, 40, 0.6)'
                    },
                    {
                        label: 'Checkout',
                        data: checkout,
                        backgroundColor: 'rgba(255, 215, 0, 0.6)'
                    },
                    {
                        label: 'Compras',
                        data: purchases,
                        backgroundColor: 'rgba(255, 215, 0, 0.8)'
                    }
                ]
            },
            options: chartOptions
        });
    }
}

function updateTable(data) {
    const tbody = document.getElementById('tableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    const sortedData = [...data].sort((a, b) => new Date(b.date_start) - new Date(a.date_start));
    
    sortedData.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDate(row.date_start)}</td>
            <td>${formatNumber(parseInt(row.impressions || 0))}</td>
            <td>${formatNumber(parseInt(row.clicks || 0))}</td>
            <td>${formatNumber(parseInt(row.reach || 0))}</td>
            <td>${formatCurrency(row.spend || 0)}</td>
            <td>${formatPercent(row.ctr || 0)}</td>
            <td>${formatNumber(parseInt(row.website_purchases || 0))}</td>
            <td>${formatCurrency(row.cpa || 0)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => { errorDiv.style.display = 'none'; }, 5000);
    }
}

function showInfo(message) {
    const infoDiv = document.getElementById('infoMessage');
    if (infoDiv) {
        infoDiv.textContent = message;
        infoDiv.style.display = 'block';
    }
}

function updateLastUpdate() {
    const now = new Date();
    const formatted = now.toLocaleString('pt-BR');
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) {
        lastUpdate.textContent = 'Última atualização: ' + formatted;
    }
}

async function refreshData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    
    if (!startDate || !endDate) {
        showInfo('Por favor, selecione as datas de início e fim antes de atualizar os dados.');
        return;
    }
    
    const btnRefresh = document.getElementById('btnRefresh');
    const loading = document.getElementById('loading');
    
    if (btnRefresh) btnRefresh.disabled = true;
    if (loading) loading.style.display = 'flex';
    
    try {
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        
        const url = '/api/update?' + params.toString();
        const response = await fetch(url, { method: 'POST' });
        const result = await response.json();
        
        if (result.status === 'success') {
            await loadDashboard();
            updateLastUpdate();
            const infoDiv = document.getElementById('infoMessage');
            if (infoDiv) infoDiv.style.display = 'none';
        } else {
            throw new Error(result.message || 'Erro ao atualizar');
        }
    } catch (error) {
        showError('Erro ao atualizar dados: ' + error.message);
    } finally {
        if (btnRefresh) btnRefresh.disabled = false;
        if (loading) loading.style.display = 'none';
    }
}

async function loadDashboard() {
    const data = await fetchData();
    
    if (data && data.status === 'success' && data.data && data.data.length > 0) {
        dashboardData = data.data;
        const kpis = calculateKPIs(dashboardData);
        updateKPIs(kpis);
        updateCharts(dashboardData);
        updateTable(dashboardData);
    } else {
        showInfo('Selecione um período e clique em "Atualizar Dados" para carregar os dados da API.');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    showInfo('Selecione um período e clique em "Atualizar Dados" para carregar os dados da API.');
});
