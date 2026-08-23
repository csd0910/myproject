/**
 * TaskMining - 個人ダッシュボード メインロジック
 * js/user_dashboard.js
 * 用途: user_dashboard.html 専用の初期化・KPI更新・UI制御
 * 依存: api.js, charts.js, Chart.js, mermaid, marked
 */

'use strict';

// =============================================
// グローバル状態
// =============================================
let dynamicFlowData = null;
let appChartInstance, taskChartInstance, breakdownChartInstance;

// =============================================
// メインデータ読み込み
// =============================================

/** APIからデータを取得し、全UIを更新する */
async function loadDynamicCharts() {
    try {
        // ユーザー名表示
        const uid = getCurrentUserId();
        const nameEl = document.getElementById('displayUserName');
        if (nameEl) nameEl.textContent = (uid !== 'ALL' && uid !== 'CURRENT_USER') ? uid : '自分のみ';

        const trendParams = getFilterParams();
        const trendRes = await fetch(`/api/dashboard/trend_data?${trendParams.toString()}`);
        const dataTrend = await trendRes.json();

        const [dataMacro, dataUser] = await Promise.all([fetchDashboardData(), fetchUserData()]);

        // --- KPI カード更新 ---
        updateKpiCards(dataMacro.kpi, dataUser.benchmarks);

        // --- 円グラフ ---
        if (appChartInstance)       appChartInstance.destroy();
        if (taskChartInstance)      taskChartInstance.destroy();
        if (breakdownChartInstance) breakdownChartInstance.destroy();

        const hoverHandler = buildChartHoverHandler(dataMacro);
        if (dataMacro.work_breakdown) breakdownChartInstance = drawBreakdownChart(dataMacro.work_breakdown, hoverHandler('work_breakdown'));
        if (dataMacro.apps)           appChartInstance       = drawAppChart(dataMacro.apps, hoverHandler('apps'));
        if (dataMacro.kpi)            taskChartInstance      = drawTaskChart(dataMacro.kpi, hoverHandler('ops'));

        // ホバーが外れたときに確実にモーダルを隠す
        ['breakdownChart', 'appChart', 'taskChart'].forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                canvas.addEventListener('mouseleave', () => {
                    const modal = document.getElementById('chartModal');
                    if (modal) modal.classList.add('hidden');
                });
            }
        });

        // --- その他グラフ ---
        drawScatterChart(dataMacro.scatter, dynamicFlowData);
        drawForecastChart(dataUser.forecast_steps);
        drawResultTrendChart(dataUser.result_trend);

        // --- タイムライン ---
        if (dataUser.timeline) updateTimeline(dataUser.timeline);

        // --- フロー図 ---
        if (dataUser.dynamic_flows) {
            dynamicFlowData = dataUser.dynamic_flows;
            populateFlowSelect(dynamicFlowData);
            updateFlows();
        }

        // --- トレンドチャート描画 ---
        if (dataTrend && dataTrend.labels && dataTrend.labels.length > 0) {
            renderTrendCharts(dataTrend);
        }

    } catch (e) {
        console.error('Chart data loading failed:', e);
    }
}

// グラフのインスタンス保持用
let trendAppsChart, trendBreakdownChart, operationTypesChart, shortcutRateChart, clicksChart, mouseDistChart, switchesChart;

function renderTrendCharts(data) {
    const labels = data.labels;
    
    const baseOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } };
    
    // 1. 利用アプリ推移 (積み上げ棒)
    if (trendAppsChart) trendAppsChart.destroy();
    if (document.getElementById('trendApps')) {
        const appDatasets = [];
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b'];
        let colorIdx = 0;
        for (const [app, values] of Object.entries(data.apps_trend || {})) {
            appDatasets.push({ label: app, data: values, backgroundColor: colors[colorIdx % colors.length] });
            colorIdx++;
        }
        trendAppsChart = new Chart(document.getElementById('trendApps'), {
            type: 'bar',
            data: { labels: labels, datasets: appDatasets },
            options: { ...baseOptions, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.1)' } } } }
        });
    }

    // 2. 業務内訳推移 (積み上げ棒)
    if (trendBreakdownChart) trendBreakdownChart.destroy();
    if (document.getElementById('trendBreakdown')) {
        const bdDatasets = [];
        const bdColors = { '基幹業務': '#ef4444', 'メール(外部連絡)': '#f59e0b', 'チャット(内部連絡)': '#10b981', 'Web会議': '#3b82f6', 'AIツール操作': '#8b5cf6', 'アイドル(操作なし)': '#64748b', '通常作業': '#94a3b8' };
        for (const [cat, values] of Object.entries(data.breakdown_trend || {})) {
            bdDatasets.push({ label: cat, data: values, backgroundColor: bdColors[cat] || '#ccc' });
        }
        trendBreakdownChart = new Chart(document.getElementById('trendBreakdown'), {
            type: 'bar',
            data: { labels: labels, datasets: bdDatasets },
            options: { ...baseOptions, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, grid: { color: 'rgba(255, 255, 255, 0.1)' } } } }
        });
    }

    // 3. 操作種類の割合推移
    if (operationTypesChart) operationTypesChart.destroy();
    if (document.getElementById('trendOperationTypes')) {
        operationTypesChart = new Chart(document.getElementById('trendOperationTypes'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: '手入力 (%)', data: data.type_input, backgroundColor: '#14b8a6' },
                    { label: 'コピペ (%)', data: data.type_copy, backgroundColor: '#f59e0b' },
                    { label: '閲覧・その他 (%)', data: data.type_view, backgroundColor: '#94a3b8' }
                ]
            },
            options: { ...baseOptions, scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, max: 100, grid: { color: 'rgba(255, 255, 255, 0.1)' } } } }
        });
    }

    // 4. ショートカットキー利用率推移
    if (shortcutRateChart) shortcutRateChart.destroy();
    if (document.getElementById('trendShortcutRate')) {
        shortcutRateChart = new Chart(document.getElementById('trendShortcutRate'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ label: 'ショートカット利用率 (%)', data: data.shortcut_rate, borderColor: '#06b6d4', backgroundColor: 'rgba(6, 182, 212, 0.2)', borderWidth: 2, fill: true, tension: 0.4 }]
            },
            options: { ...baseOptions, scales: { x: { grid: { display: false } }, y: { max: 100, min: 0, grid: { color: 'rgba(255, 255, 255, 0.1)' } } } }
        });
    }

    // 5. 守れた集中時間推移
    if (clicksChart) clicksChart.destroy(); // using the old variable name to avoid global let changes or we can just use focusedChart
    if (document.getElementById('trendFocused')) {
        clicksChart = new Chart(document.getElementById('trendFocused'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{ label: '集中時間 (h)', data: data.focused_time, borderColor: '#14b8a6', backgroundColor: 'rgba(20, 184, 166, 0.2)', borderWidth: 2, fill: true, tension: 0.4 }]
            },
            options: { ...baseOptions, scales: { x: { grid: { display: false } }, y: { min: 0, grid: { color: 'rgba(255, 255, 255, 0.1)' } } } }
        });
    }
}

// =============================================
// KPI カード
// =============================================

/**
 * KPIカードの数値を更新する
 * @param {Object} kpi - /api/dashboard/data の kpi フィールド
 * @param {Object} bm - /api/dashboard/user_data の benchmarks フィールド
 */
function updateKpiCards(kpi, bm) {
    if (!kpi) return;

    const fmt = hours => {
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        if (h === 0) return `${m}<span class="text-base font-normal ml-1">分</span>`;
        return `${h}<span class="text-base font-normal ml-1">時間</span>${m}<span class="text-base font-normal ml-1">分</span>`;
    };

    const setEl = (id, html, colorClass) => {
        const el = document.getElementById(id);
        if (!el) return;
        el.innerHTML = html;
        if (colorClass) el.querySelectorAll('span').forEach(s => s.classList.add(colorClass));
    };

    setEl('kpi-focused',          fmt((kpi.total_focused_time || 0) / 3600), 'text-teal-500');
    setEl('kpi-total-hours',      fmt(kpi.total_hours      || 0), 'text-slate-400');
    setEl('kpi-inefficient-time', fmt(kpi.inefficient_hours|| 0), 'text-red-400');
    setEl('kpi-meeting',          fmt(kpi.meeting_hours    || 0), 'text-purple-400');
    setEl('kpi-idle',             fmt(kpi.idle_hours       || 0), 'text-slate-400');

    // サイドバー詳細数値
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val; };
    set('sidebar-clicks',    `${kpi.total_clicks || 0} 回`);
    set('sidebar-copypaste', `${kpi.total_copy_paste || 0} 回`);
    set('sidebar-switches', `${kpi.total_context_switches || 0} 回`);
    


    // 自己改善ベンチマーク (バックエンドから取得した bm オブジェクトを使用)
    if (bm) {
        // --- ショートカット活用度 ---
        set('bm-my-shortcut', `${bm.my_shortcut_rate}%`);
        document.getElementById('bm-bar-shortcut').style.width = `${bm.my_shortcut_rate}%`;
        
        // ショートカット内訳リストの生成
        const shortcutList = document.getElementById('shortcut-details-list');
        if (shortcutList && kpi.shortcut_details) {
            shortcutList.innerHTML = '';
            const details = kpi.shortcut_details;
            let hasData = false;
            for (const [key, count] of Object.entries(details)) {
                if (count > 0) {
                    hasData = true;
                    const li = document.createElement('li');
                    li.textContent = `${key}: ${count}回`;
                    shortcutList.appendChild(li);
                }
            }
            if (!hasData) {
                shortcutList.innerHTML = '<li>データなし</li>';
            }
        }
        
        document.getElementById('bm-avg-shortcut').style.left = `${bm.avg_shortcut_rate}%`;
        set('bm-avg-shortcut-txt', `${bm.avg_shortcut_rate}%`);
    }

}

// =============================================
// グラフホバー詳細モーダル
// =============================================

/**
 * 円グラフのホバー時に詳細パネルを表示するハンドラーを生成する
 * @param {Object} dataMacro
 * @returns {Function} catKey => (event, elements, chart) => void
 */
function buildChartHoverHandler(dataMacro) {
    return catKey => (event, elements, chart) => {
        const modal = document.getElementById('chartModal');
        if (!modal) return;
        if (elements.length === 0) { modal.classList.add('hidden'); return; }

        const idx   = elements[0].index;
        const label = chart.data.labels[idx];
        const val   = chart.data.datasets[0].data[idx];
        const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
        const pct   = total > 0 ? Math.round((val / total) * 100) : 0;

        const fmtHMS = s => {
            const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
            return h > 0 ? `${h}時間${m}分${sec}秒` : m > 0 ? `${m}分${sec}秒` : `${sec}秒`;
        };

        const details = dataMacro.details?.[catKey]?.[label] || [];
        let html = `<div class="font-bold text-slate-400 text-center mb-2 border-b border-slate-700 pb-2">総計 ${fmtHMS(val)}</div>`;
        html += `<ul class="text-left text-sm space-y-3">`;
        if (details.length > 0) {
            details.forEach((d, i) => {
                html += `<li class="flex justify-between items-start gap-4">
                    <span class="truncate text-slate-300 font-medium" title="${d.file}">${i+1}. ${d.file}</span>
                    <span class="font-bold text-indigo-400 whitespace-nowrap">${fmtHMS(d.duration)}</span>
                </li>`;
            });
        } else {
            html += `<li class="text-slate-400 text-center">詳細データなし</li>`;
        }
        html += `</ul>`;

        document.getElementById('chartModalLabel').textContent   = label;
        document.getElementById('chartModalPercent').textContent = `${pct}%`;
        document.getElementById('chartModalValue').innerHTML     = html;

        const rect = chart.canvas.getBoundingClientRect();
        const mw   = 768;
        modal.style.left = (rect.right + 20 + mw > window.innerWidth)
            ? Math.max(20, rect.left - mw - 20) + 'px'
            : (rect.right + 20) + 'px';
        modal.style.top  = Math.max(20, rect.top - 20) + 'px';
        modal.classList.remove('hidden');
    };
}

// =============================================
// タイムライン表示
// =============================================

/**
 * 時系列ログリストをHTMLに変換してタイムラインコンテナに挿入する
 * @param {Array} timelineData
 */
function updateTimeline(timelineData) {
    const container = document.getElementById('timelineContainer');
    if (!container) return;
    if (!timelineData || timelineData.length === 0) {
        container.innerHTML = '<div class="text-slate-400 text-center py-4">データがありません</div>';
        return;
    }
    container.innerHTML = timelineData.map(item => {
        const bg    = item.inefficient_flag ? 'bg-amber-50 border-amber-400'
                    : item.description.includes('離席') ? 'bg-slate-100 border-slate-300'
                    : 'bg-white border-slate-200 shadow-sm';
        const color = item.inefficient_flag ? 'text-amber-800'
                    : item.description.includes('離席') ? 'text-slate-600' : 'text-blue-600';
        return `
        <div class="p-3 rounded-md text-sm border-l-4 ${bg}">
            <div class="font-bold ${color} mb-1">
                ${item.start}〜${item.end} <span class="text-xs text-slate-500 font-normal">(${item.duration_sec}秒)</span>
                <span class="text-slate-600 ml-2">[${item.app}]</span>
                ${item.inefficient_flag ? '<span class="text-teal-400 text-xs ml-2 font-bold bg-teal-900/50 px-2 py-1 rounded">💡 自動化のチャンス</span>' : ''}
            </div>
            <div class="text-slate-700">
                ${item.file ? `<span class="font-semibold text-slate-800">${item.file}</span> - ` : ''}${item.description}
            </div>
        </div>`;
    }).join('');
}

// =============================================
// フロー図（Mermaid）
// =============================================

/** フロー選択セレクトボックスをデータで埋める */
function populateFlowSelect(flows) {
    const select = document.getElementById('flowSelect');
    if (!select) return;
    select.innerHTML = '';
    for (const key in flows) {
        const opt = document.createElement('option');
        opt.value = key;
        opt.textContent = flows[key].label;
        select.appendChild(opt);
    }
}

/** 選択されたフロー図をMermaidでレンダリングする */
async function updateFlows() {
    if (!dynamicFlowData) return;
    const val  = document.getElementById('flowSelect')?.value;
    const data = dynamicFlowData[val];
    if (!data) return;

    const manualContainer = document.getElementById('flowManualContainer');
    const autoContainer   = document.getElementById('flowAutoContainer');
    const manualHeader    = document.getElementById('flowManualHeader');
    const autoHeader      = document.getElementById('flowAutoHeader');

    if (manualHeader) manualHeader.textContent = data.manual_time ? `手動所要時間 (現状): ${data.manual_time}` : '手動所要時間 (現状)';
    if (autoHeader)   autoHeader.textContent   = data.auto_time   ? `自動化後 (予想): ${data.auto_time}`      : '自動化後 (予想)';

    try {
        const { svg: manualSvg } = await mermaid.render('mermaid-manual-' + Date.now(), data.manual);
        if (manualContainer) manualContainer.innerHTML = manualSvg;
    } catch (e) { console.error('Mermaid (manual):', e); }

    try {
        const { svg: autoSvg } = await mermaid.render('mermaid-auto-' + Date.now(), data.auto);
        if (autoContainer) autoContainer.innerHTML = autoSvg;
    } catch (e) { console.error('Mermaid (auto):', e); }
}

// =============================================
// AIレポート
// =============================================

/** ヘッダーボタンからモーダルでAIレポートを表示する */
async function generateAIReport(userId) {
    const btn = document.getElementById('aiReportBtn');
    const orig = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> 生成中...';
    btn.disabled  = true;
    try {
        const uid = (userId === 'CURRENT_USER') ? getCurrentUserId() : userId;
        let url   = '/api/dashboard/analyze?user_id=' + uid;

        const filterDate = document.getElementById('filterDate')?.value;
        const start = document.getElementById('filterStart')?.value;
        const end   = document.getElementById('filterEnd')?.value;
        const flow  = document.getElementById('flowSelect')?.value;
        if (filterDate) {
            url += '&start_date=' + encodeURIComponent(new Date(filterDate + 'T00:00:00').toISOString());
            url += '&end_date=' + encodeURIComponent(new Date(filterDate + 'T23:59:59').toISOString());
        } else {
            if (start && start !== 'all') url += '&start_date=' + encodeURIComponent(start);
            if (end) url += '&end_date=' + encodeURIComponent(end);
        }
        if (flow && flow !== 'all') url += '&file_name=' + encodeURIComponent(flow);


        const data = await (await fetch(url, { method: 'POST' })).json();
        const html = (data.report || '').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
        document.getElementById('aiModalContent').innerHTML = marked?.parse ? marked.parse(html) : html.replace(/\n/g, '<br>');
        document.getElementById('aiModal').classList.remove('hidden');
    } catch (err) {
        alert('AIレポートの生成に失敗しました: ' + err);
    } finally {
        btn.innerHTML = orig;
        btn.disabled  = false;
    }
}

/** インラインAIレポートエリアに分析結果を表示する */
async function generateAIReportInline(userId) {
    const btn = document.getElementById('inlineAiReportBtn');
    const div = document.getElementById('inlineAiReportContent');
    const orig = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> AIがデータを分析中...';
    btn.disabled  = true;
    div.innerHTML = '<div class="text-center py-12"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div><p class="text-indigo-600 font-bold">Gemini AIが分析中...</p></div>';
    try {
        const uid = (userId === 'CURRENT_USER') ? getCurrentUserId() : userId;
        let url   = '/api/dashboard/analyze?user_id=' + uid;

        const filterDate = document.getElementById('filterDate')?.value;
        const start = document.getElementById('filterStart')?.value;
        const end   = document.getElementById('filterEnd')?.value;
        const flow  = document.getElementById('flowSelect')?.value;
        if (filterDate) {
            url += '&start_date=' + encodeURIComponent(new Date(filterDate + 'T00:00:00').toISOString());
            url += '&end_date=' + encodeURIComponent(new Date(filterDate + 'T23:59:59').toISOString());
        } else {
            if (start && start !== 'all') url += '&start_date=' + encodeURIComponent(start);
            if (end) url += '&end_date=' + encodeURIComponent(end);
        }
        if (flow && flow !== 'all') url += '&file_name=' + encodeURIComponent(flow);


        const data = await (await fetch(url, { method: 'POST' })).json();
        if (data.report) {
            const html = data.report.replace(/&lt;/g, '<').replace(/&gt;/g, '>');
            div.innerHTML = marked?.parse ? marked.parse(html) : html.replace(/\n/g, '<br>');
        } else {
            div.innerHTML = '<p class="text-red-500">レポートの生成に失敗しました。</p>';
        }
    } catch (err) {
        div.innerHTML = `<p class="text-red-500">通信エラー: ${err}</p>`;
    } finally {
        btn.innerHTML = orig;
        btn.disabled  = false;
    }
}

/** AIレポートモーダルを閉じる */
function closeAIModal() {
    document.getElementById('aiModal').classList.add('hidden');
}

// =============================================
// 初期化（DOMContentLoaded）
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    setTimeLabels();
    setDefaultDates();
    loadDynamicCharts();
});
