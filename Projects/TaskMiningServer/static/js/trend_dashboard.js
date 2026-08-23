/**
 * trend_dashboard.js
 * トレンドダッシュボードの表示制御とグラフ描画
 */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
    // デフォルトで過去7日間をセット
    const today = new Date();
    const lastWeek = new Date();
    lastWeek.setDate(today.getDate() - 6); // 今日を含めて7日

    document.getElementById('filterStart').value = lastWeek.toISOString().split('T')[0];
    document.getElementById('filterEnd').value = today.toISOString().split('T')[0];
    
    // URLからuser_idを取得してセット
    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id');
    if (userId) {
        document.getElementById('filterUser').value = userId;
    }

    loadTrendData();
});

async function loadTrendData() {
    const start = document.getElementById('filterStart').value;
    const end = document.getElementById('filterEnd').value;
    const user = document.getElementById('filterUser').value;
    
    document.getElementById('trendContent').style.display = 'none';
    document.getElementById('errorMsg').style.display = 'none';
    document.getElementById('loading').style.display = 'block';
    
    try {
        const url = `/api/dashboard/trend_data?user_id=${user}&start_date=${start}T00:00:00&end_date=${end}T23:59:59`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('API通信エラー');
        const data = await res.json();
        
        renderTrendCharts(data);
        
        document.getElementById('loading').style.display = 'none';
        document.getElementById('trendContent').style.display = 'grid';
    } catch (e) {
        document.getElementById('loading').style.display = 'none';
        const errorEl = document.getElementById('errorMsg');
        errorEl.style.display = 'block';
        errorEl.textContent = 'データの取得に失敗しました。';
        console.error(e);
    }
}

// グラフのインスタンス保持用
let workHoursChart, inefficientChart, aiUsageChart, operationTypesChart, shortcutRateChart;

function renderTrendCharts(data) {
    const labels = data.labels; // 日付ラベル配列 ["08/01", "08/02", ...]

    // 1. 稼働時間の推移
    if (workHoursChart) workHoursChart.destroy();
    workHoursChart = new Chart(document.getElementById('trendWorkHours'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '稼働時間 (時間)',
                data: data.work_hours,
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.1)' } }
            }
        }
    });

    // 2. 非効率操作の推移 (複合グラフ: 棒グラフと折れ線グラフ)
    if (inefficientChart) inefficientChart.destroy();
    inefficientChart = new Chart(document.getElementById('trendInefficient'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'bar',
                    label: '非効率時間 (分)',
                    data: data.inefficient_time,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    yAxisID: 'y'
                },
                {
                    type: 'line',
                    label: '手入力・コピペ回数',
                    data: data.inefficient_ops,
                    borderColor: '#f59e0b',
                    backgroundColor: '#f59e0b',
                    borderWidth: 2,
                    tension: 0.1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { 
                    type: 'linear', position: 'left', 
                    title: { display: true, text: '時間(分)', color: '#ef4444' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' } 
                },
                y1: { 
                    type: 'linear', position: 'right', 
                    title: { display: true, text: '回数', color: '#f59e0b' },
                    grid: { display: false } 
                }
            }
        }
    });

    // 3. AIツール活用割合 (100%積み上げ棒グラフ想定だが、シンプルに積み上げ)
    if (aiUsageChart) aiUsageChart.destroy();
    aiUsageChart = new Chart(document.getElementById('trendAiUsage'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'AIツール (%)',
                    data: data.ai_ratio,
                    backgroundColor: '#8b5cf6'
                },
                {
                    label: '手作業・通常アプリ (%)',
                    data: data.manual_ratio,
                    backgroundColor: '#10b981'
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, max: 100 }
            }
        }
    });
    
    // 4. 操作種類の割合推移 (積み上げ棒)
    if (operationTypesChart) operationTypesChart.destroy();
    operationTypesChart = new Chart(document.getElementById('trendOperationTypes'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '手入力 (%)',
                    data: data.type_input,
                    backgroundColor: '#14b8a6'
                },
                {
                    label: 'コピペ (%)',
                    data: data.type_copy,
                    backgroundColor: '#f59e0b'
                },
                {
                    label: '閲覧・その他 (%)',
                    data: data.type_view,
                    backgroundColor: '#94a3b8'
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.1)' }, max: 100 }
            }
        }
    });

    // 5. ショートカットキー利用率推移 (折れ線)
    if (shortcutRateChart) shortcutRateChart.destroy();
    shortcutRateChart = new Chart(document.getElementById('trendShortcutRate'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'ショートカット利用率 (%)',
                data: data.shortcut_rate,
                borderColor: '#06b6d4',
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: 'rgba(255, 255, 255, 0.1)' }, max: 100, min: 0 }
            }
        }
    });
}
