/**
 * TaskMining Dashboard - API通信・フィルター共通処理
 * js/api.js
 * 用途: fetch呼び出し、URLパラメータ操作、日付フィルター管理
 */

'use strict';

// =============================================
// URLパラメータユーティリティ
// =============================================

/** 現在のURLパラメータから user_id を取得する */
function getCurrentUserId() {
    const params = new URLSearchParams(window.location.search);
    return params.get('user_id') || 'ALL';
}

/** フィルター用の開始・終了日時をAPIパラメータ形式で返す */
function getFilterParams() {
    const filterDate = document.getElementById('filterDate')?.value;
    const start = document.getElementById('filterStart')?.value;
    const end   = document.getElementById('filterEnd')?.value;
    const params = new URLSearchParams();
    params.append('user_id', getCurrentUserId());
    
    if (filterDate) {
        // filterDate is "YYYY-MM-DD"
        // generate start_date: YYYY-MM-DDT00:00:00
        // generate end_date: YYYY-MM-DDT23:59:59
        params.append('start_date', new Date(`${filterDate}T00:00:00`).toISOString());
        params.append('end_date',   new Date(`${filterDate}T23:59:59`).toISOString());
    } else {
        if (start) params.append('start_date', new Date(start).toISOString());
        if (end)   params.append('end_date',   new Date(end).toISOString());
    }
    return params;
}

// =============================================
// API fetch ラッパー
// =============================================

/**
 * ダッシュボードデータ（部門/全社集計）を取得する
 * @returns {Promise<Object>} dataMacro
 */
async function fetchDashboardData() {
    const params = getFilterParams();
    const cacheBuster = `&_t=${Date.now()}`;
    const token = localStorage.getItem('admin_token');
    const headers = token ? { 'X-Admin-Token': `Bearer ${token}` } : {};
    const res = await fetch(`/api/dashboard/data?${params.toString()}${cacheBuster}`, { headers });
    if (!res.ok) throw new Error(`dashboard/data: ${res.status}`);
    return res.json();
}

/**
 * ユーザー別データ（タイムライン・予測・トレンド）を取得する
 * @returns {Promise<Object>} dataUser
 */
async function fetchUserData() {
    const params = getFilterParams();
    const cacheBuster = `&_t=${Date.now()}`;
    const token = localStorage.getItem('admin_token');
    const headers = token ? { 'X-Admin-Token': `Bearer ${token}` } : {};
    const res = await fetch(`/api/dashboard/user_data?${params.toString()}${cacheBuster}`, { headers });
    if (!res.ok) throw new Error(`dashboard/user_data: ${res.status}`);
    return res.json();
}

// =============================================
// フィルター操作
// =============================================

/** 絞り込みを適用してページを再読み込みする */
function applyFilters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    const filterDateEl = document.getElementById('filterDate');
    if (filterDateEl) {
        const filterDate = filterDateEl.value;
        if (filterDate) {
            urlParams.set('start_date', filterDate + 'T00:00:00');
            urlParams.set('end_date', filterDate + 'T23:59:59');
        } else {
            urlParams.delete('start_date');
            urlParams.delete('end_date');
        }
    } else {
        const start = document.getElementById('filterStart')?.value;
        const end   = document.getElementById('filterEnd')?.value;
        if (start) urlParams.set('start_date', start); else urlParams.delete('start_date');
        if (end)   urlParams.set('end_date', end);     else urlParams.delete('end_date');
    }
    
    urlParams.set('_t', Date.now()); // キャッシュバスター
    window.location.href = window.location.pathname + '?' + urlParams.toString();
}

/** フィルターをリセットしてページを再読み込みする */
function resetUserFilters() {
    window.location.href = window.location.pathname;
}

/**
 * URLパラメータから日付フィルターを復元し、未設定なら本日の範囲をデフォルト設定する
 */
function setDefaultDates() {
    const urlParams = new URLSearchParams(window.location.search);
    const urlStart  = urlParams.get('start_date');
    const urlEnd    = urlParams.get('end_date');

    const filterDateEl = document.getElementById('filterDate');
    const elStart = document.getElementById('filterStart');
    const elEnd   = document.getElementById('filterEnd');
    
    if (filterDateEl) {
        if (urlStart) {
            filterDateEl.value = urlStart.substring(0, 10);
        } else if (!filterDateEl.value) {
            const now = new Date();
            filterDateEl.value = now.toISOString().substring(0, 10);
        }
    } else if (elStart && elEnd) {
        if (urlStart) elStart.value = urlStart;
        if (urlEnd)   elEnd.value   = urlEnd;
    
        if (!elStart.value && !elEnd.value) {
            const now   = new Date();
            const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(),  0,  0,  0);
            const end   = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59);
            const fmt   = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            elStart.value = fmt(start);
            elEnd.value   = fmt(end);
        }
    }
}

// =============================================
// CSV出力
// =============================================

/** ログデータをCSVファイルとしてダウンロードする */
async function downloadCsv() {
    const params = getFilterParams();
    const res = await fetch(`/api/dashboard/export_csv?${params.toString()}`);
    if (res.ok) {
        const blob = await res.blob();
        const url  = window.URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.style.display = 'none';
        a.href     = url;
        a.download = `taskmining_user_report_${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
    } else {
        alert('CSVのエクスポートに失敗しました。');
    }
}

// =============================================
// 時間軸ラベル生成（KPIカードホバー用）
// =============================================

/** 直近8時間の時刻ラベルを .time-labels 要素に設定する */
function setTimeLabels() {
    const now = new Date();
    document.querySelectorAll('.time-labels').forEach(el => {
        let html = '';
        for (let i = 7; i >= 0; i--) {
            const d = new Date(now.getTime() - i * 60 * 60 * 1000);
            html += `<span class="flex-1 text-center">${d.getHours()}</span>`;
        }
        el.innerHTML = html;
    });
}
