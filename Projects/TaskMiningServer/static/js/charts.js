/**
 * TaskMining Dashboard - グラフ描画モジュール
 * js/charts.js
 * 用途: user_dashboard.html で使用するすべての Chart.js グラフ描画関数
 * 依存: Chart.js (CDN)
 */

'use strict';

// =============================================
// Chart.js グローバル設定 (ダークテーマ用)
// =============================================
Chart.defaults.color = '#cbd5e1'; // text-slate-300
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';

// =============================================
// カラーパレット
// =============================================
const CHART_COLORS = {
    scatter: {
        excel:  'rgba(16, 185, 129, 0.8)',
        browser:'rgba(59, 130, 246, 0.8)',
        other:  'rgba(168, 85, 247, 0.8)',
    },
    ops: {
        '文字手入力':      '#f97316',
        'マウス操作':      '#10b981',
        'マウス右メニュー':'#8b5cf6',
        'ショートカット':  '#eab308',
        'コピー＆ペースト':'#3b82f6',
        '画面切り替え':    '#ec4899',
    },
    breakdown: {
        '基幹業務':            '#ef4444',
        'メール(外部連絡)':     '#3b82f6',
        'チャット(内部連絡)':   '#8b5cf6',
        'Web会議':             '#64748b',
        'AIツール操作':         '#10b981',
        'アイドル(操作なし)':   '#f59e0b',
        '通常作業':             '#6366f1',
    },
    app: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
};

// =============================================
// 散布図 (作業時間 vs 単純作業回数)
// =============================================

/**
 * 散布図を描画する
 * @param {Array} scatterData - [{x, y, file, app, op}, ...]
 * @param {Object} dynamicFlowDataRef - フロー図連動用。グローバル変数への参照
 */
function drawScatterChart(scatterData, dynamicFlowDataRef) {
    if (!scatterData) return;
    const ctx = document.getElementById('scatterChart');

    const getColor = name => {
        name = (name || '').toLowerCase();
        if (name.includes('excel')) return CHART_COLORS.scatter.excel;
        if (name.includes('chrome') || name.includes('edge') || name.includes('explorer'))
            return CHART_COLORS.scatter.browser;
        return CHART_COLORS.scatter.other;
    };

    const chart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: '作業負荷',
                data: scatterData.map(d => ({ x: d.x, y: d.y, file: d.file, app: d.app, op: d.op })),
                backgroundColor: scatterData.map(d => getColor(d.app)),
                pointRadius: 5, pointHoverRadius: 8,
            }]
        },
        options: {
            maintainAspectRatio: false,
            onClick: (event, elements) => {
                if (elements.length === 0) return;
                const dp = chart.data.datasets[0].data[elements[0].index];
                const panel = document.getElementById('scatterDetail');
                panel.classList.remove('hidden');
                panel.innerHTML = `
                    <div class="font-bold text-lg mb-1">📁 ${dp.file}</div>
                    <div class="text-sm">
                        🖥️ アプリ: <span class="font-semibold text-blue-600">${dp.app}</span> |
                        ⚙️ 操作: <span class="font-semibold text-amber-600">${dp.op}</span> |
                        ⏱️ ${dp.x}秒 | 🔄 単純作業: ${dp.y}回
                    </div>`;

                // フロー図を連動更新
                if (dynamicFlowDataRef && dp.file) {
                    if (!dynamicFlowDataRef[dp.file]) {
                        dynamicFlowDataRef[dp.file] = {
                            label: dp.file.substring(0, 20) + (dp.file.length > 20 ? '...' : ''),
                            manual: `graph TD\n A["作業開始"] --> B["${dp.app}<br>で ${dp.op}"] --> Z["完了 (手作業: ${dp.x}秒)"]`,
                            auto:   `graph TD\n A["スクリプト自動起動"] --> B["${dp.app} 連携<br>で一括処理"] --> Z["完了 (自動: 数秒)"]`,
                            manual_time: `${dp.x}秒`,
                            auto_time:   `5秒 (－${Math.max(0, dp.x - 5)}秒)`,
                        };
                        const select = document.getElementById('flowSelect');
                        const opt = document.createElement('option');
                        opt.value = dp.file;
                        opt.textContent = dynamicFlowDataRef[dp.file].label;
                        select.appendChild(opt);
                    }
                    document.getElementById('flowSelect').value = dp.file;
                    updateFlows();
                    document.getElementById('flowSelect').scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            },
            scales: {
                x: { title: { display: true, text: '作業時間(秒)' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                y: { title: { display: true, text: 'コピー＆ペースト・手入力回数' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
            },
            plugins: { 
                legend: { display: false },
                tooltip: {
                    titleFont: { size: 14 },
                    bodyFont: { size: 16 },
                    padding: 12,
                    callbacks: {
                        label: function(ctx) {
                            const dp = ctx.raw;
                            return `📁 ${dp.file} [${dp.app}]`;
                        }
                    }
                }
            },
        }
    });
}

// =============================================
// 現状vs予想 比較横棒グラフ
// =============================================

/**
 * ファイル別の現状時間と自動化予想時間を比較する横棒グラフを描画する
 * @param {Array} steps - [{step_name, manual_sec, forecast_sec}, ...]
 */
function drawForecastChart(steps) {
    const ctx = document.getElementById('forecastBar');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: steps.map(s => s.step_name),
            datasets: [
                { label: '現状',  data: steps.map(s => s.manual_sec),   backgroundColor: '#eb6834', borderRadius: 4 },
                { label: '予想',  data: steps.map(s => s.forecast_sec), backgroundColor: '#eda100', borderRadius: 4 },
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { title: { display: true, text: '所要時間（秒）' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                y: { grid: { display: false } },
            }
        }
    });
}

// =============================================
// 個人改善トレンド 折れ線グラフ
// =============================================

/**
 * 個人の非効率操作の推移を折れ線グラフで描画する
 * @param {{period_labels: string[], cumulative_saved_min: number[]}} trend
 */
function drawResultTrendChart(trend) {
    const ctx = document.getElementById('resultLine');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: trend.period_labels,
            datasets: [{
                data: trend.cumulative_saved_min,
                borderColor: '#1baf7a',
                backgroundColor: 'rgba(27, 175, 122, 0.1)',
                fill: true, borderWidth: 2, pointRadius: 4, tension: 0.2,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { title: { display: true, text: '非効率操作（回）' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
            }
        }
    });
}

// =============================================
// 業務内訳ドーナツグラフ
// =============================================

/**
 * 業務区分（メール/会議/AIなど）ごとの時間内訳をドーナツで描画する
 * @param {Object} work_breakdown - {カテゴリ名: 秒数, ...}
 * @param {Function} onHover - ホバー時コールバック
 * @returns {Chart} チャートインスタンス
 */
function drawBreakdownChart(work_breakdown, onHover) {
    const labels = Object.keys(work_breakdown);
    const bg = labels.map(l => CHART_COLORS.breakdown[l] || '#94a3b8');
    const ctx = document.getElementById('breakdownChart').getContext('2d');
    return new Chart(ctx, {
        type: 'doughnut',
        data: { labels, datasets: [{ data: Object.values(work_breakdown), backgroundColor: bg, borderWidth: 0 }] },
        options: buildPieOptions(true, false, onHover),
    });
}

// =============================================
// アプリ別稼働時間 円グラフ
// =============================================

/**
 * アプリ別稼働時間の円グラフを描画する
 * @param {Object} apps - {アプリ名: 秒数, ...}
 * @param {Function} onHover - ホバー時コールバック
 * @returns {Chart} チャートインスタンス
 */
function drawAppChart(apps, onHover) {
    const ctx = document.getElementById('appChart').getContext('2d');
    return new Chart(ctx, {
        type: 'pie',
        data: { labels: Object.keys(apps), datasets: [{ data: Object.values(apps), backgroundColor: CHART_COLORS.app, borderWidth: 0 }] },
        options: buildPieOptions(false, false, onHover),
    });
}

// =============================================
// 操作種別 円グラフ
// =============================================

/**
 * 操作種別（手入力/ショートカット等）の円グラフを描画する
 * @param {Object} kpi - ダッシュボードKPIオブジェクト
 * @param {Function} onHover - ホバー時コールバック
 * @returns {Chart|null} チャートインスタンス、またはデータなしの場合null
 */
function drawTaskChart(kpi, onHover) {
    const opsCounts = {
        '文字手入力':      kpi.total_manual_typing  || 0,
        'マウス操作':      Math.max(0, (kpi.total_clicks || 0) - (kpi.total_right_clicks || 0) + (kpi.total_scrolls || 0)),
        'マウス右メニュー':kpi.total_right_clicks    || 0,
        'ショートカット':  kpi.total_shortcut_keys   || 0,
        'コピー＆ペースト':kpi.total_copy_paste      || 0,
        '画面切り替え':    kpi.total_context_switches|| 0,
    };
    const active = Object.keys(opsCounts).filter(k => opsCounts[k] > 0);
    if (active.length === 0) return null;

    const ctx = document.getElementById('taskChart').getContext('2d');
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: active,
            datasets: [{ data: active.map(k => opsCounts[k]), backgroundColor: active.map(k => CHART_COLORS.ops[k]), borderWidth: 0 }],
        },
        options: buildPieOptions(false, true, onHover),
    });
}

// =============================================
// 円グラフ共通オプション生成
// =============================================

/**
 * @param {boolean} isDoughnut - ドーナツ型か
 * @param {boolean} isCount    - 単位が「回」か（falseなら「秒」）
 * @param {Function} onHover   - ホバーコールバック
 */
function buildPieOptions(isDoughnut, isCount, onHover) {
    return {
        cutout: isDoughnut ? '50%' : '0%',
        plugins: {
            legend: { position: 'bottom', labels: { boxWidth: 12 } },
            tooltip: {
                callbacks: {
                    label(context) {
                        const val   = context.raw;
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const pct   = total > 0 ? Math.round((val / total) * 100) : 0;
                        const unit  = isCount ? '回' : '秒';
                        return `${context.label}: ${val}${unit} (${pct}%)`;
                    }
                }
            }
        },
        onHover: onHover || undefined,
    };
}
