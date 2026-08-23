// =================================================================
// 🌲 Forest WorkFlow System - Client JS (Flask Integration Version)
// =================================================================

// 状態管理 (State)
let currentUser = null;
let currentView = 'pending';
let masterForms = [];
let allUsers = [];
let currentActiveForm = null;
let userBuiltRoutes = []; 
let applicationsList = [];

let adminActiveForm = null;
let adminTableRows = [];

// ページ読み込み時にログインカードをシュワっと浮き出させる & 初期化
window.addEventListener("DOMContentLoaded", async () => {
  gsap.fromTo("#auth-card", 
    { scale: 0.9, opacity: 0, y: 30 }, 
    { scale: 1, opacity: 1, y: 0, duration: 0.8, ease: "power4.out" }
  );
  
  // ログイン状態および初期マスタデータのロード
  await checkLoginAndInitialize();
});

// =================================================================
// 🔑 認証 & 接続初期化
// =================================================================
async function checkLoginAndInitialize() {
  try {
    const res = await fetch('/api/profile');
    if (res.status === 401) {
      // 未認証時はFlask側でリダイレクトされますが、念のためJS側でもログイン画面表示
      document.getElementById("auth-container").classList.remove("hidden");
      return;
    }
    
    currentUser = await res.json();
    document.getElementById("auth-container").classList.add("hidden");
    document.getElementById("user-name").textContent = currentUser.name;
    document.getElementById("user-avatar").textContent = currentUser.name.substring(0, 1);
    document.getElementById("user-dept").textContent = `${currentUser.dept} / ${currentUser.title || "一般"}`;
    
    if (currentUser.isAdmin) {
      document.getElementById('menu-admin-settings').classList.remove('hidden');
    }
    
    // マスタロード
    await loadInitialData();
    
    // ダッシュボード初期化
    switchMenu('pending');
    
    // 定期的なデータ更新 (ポーリング: 8秒おき)
    setInterval(() => {
      refreshApplicationsListSilently();
    }, 8000);
    
  } catch (e) {
    console.error("初期化エラー:", e);
  }
}

// ログアウトボタン
document.getElementById("btn-logout").addEventListener("click", () => {
  window.location.href = "/auth/logout";
});

// ログインボタン (Mock / Flaskログインへ転送)
document.getElementById("btn-login").addEventListener("click", () => {
  window.location.href = "/login";
});

async function loadInitialData() {
  try {
    const res = await fetch('/api/initial-data');
    const data = await res.json();
    masterForms = data.forms || [];
    allUsers = data.users || [];
  } catch (e) {
    console.error("マスタデータの読み込みに失敗しました:", e);
  }
}

// =================================================================
// 🏠 画面操作 & GSAP トランジション
// =================================================================
window.switchMenu = function(menuKey) {
  currentView = menuKey;
  
  const sections = ["section-dashboard", "section-form-selector", "section-form-submitter", "section-form-confirmation", "section-admin-panel"];
  
  // 現在表示されている要素を特定し、シュワっとフェードアウトさせる
  sections.forEach(s => {
    const el = document.getElementById(s);
    if (el && !el.classList.contains("hidden")) {
      gsap.to(el, {
        opacity: 0,
        y: -10,
        duration: 0.25,
        ease: "power2.in",
        onComplete: () => {
          el.classList.add("hidden");
        }
      });
    }
  });

  const menus = ['pending', 'sent', 'received', 'returned', 'admin-settings'];
  menus.forEach(m => {
    const btn = document.getElementById('menu-' + m);
    if (btn) {
      if (m === menuKey) {
        btn.className = "w-full text-left flex items-center justify-between px-3.5 py-2.5 rounded-xl font-bold text-white bg-slate-900";
      } else {
        btn.className = "w-full text-left flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-slate-400 hover:bg-slate-900 hover:text-white transition-colors";
      }
    }
  });

  // 遅延を入れて新しい画面をヌルっと登場させる
  setTimeout(async () => {
    let activeSecId = "section-dashboard";
    if (menuKey === 'admin-settings') {
      activeSecId = "section-admin-panel";
      switchAdminTab('storage');
    } else {
      const titles = {
        pending: "未処理一覧（受信）",
        sent: "送信一覧 (マイ申請)",
        received: "受信履歴 (処理済)",
        returned: "差し戻し・却下一覧"
      };
      document.getElementById("view-title").textContent = titles[menuKey] || "ワークフロー";
      await fetchAndBindApplications(menuKey);
    }

    const activeSec = document.getElementById(activeSecId);
    activeSec.classList.remove("hidden");
    gsap.fromTo(activeSec, 
      { opacity: 0, y: 15 }, 
      { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" }
    );
  }, 300);
};

// 申請一覧データの取得とレンダリング
async function fetchAndBindApplications(type) {
  try {
    const res = await fetch('/api/applications');
    applicationsList = await res.json();
    
    updateBadges();
    
    let filtered = filterApplicationsByType(applicationsList, type);
    renderTableRows(filtered);
  } catch (e) {
    console.error("申請一覧の取得失敗:", e);
  }
}

// バックグラウンドでのサイレント更新
async function refreshApplicationsListSilently() {
  try {
    const res = await fetch('/api/applications');
    applicationsList = await res.json();
    updateBadges();
    
    // 現在ダッシュボード一覧画面が表示されている場合のみ、テーブルを再描画
    const dashboardSec = document.getElementById("section-dashboard");
    if (dashboardSec && !dashboardSec.classList.contains("hidden")) {
      let filtered = filterApplicationsByType(applicationsList, currentView);
      renderTableRows(filtered);
    }
  } catch (e) {
    console.error("サイレント更新失敗:", e);
  }
}

function filterApplicationsByType(list, type) {
  if (!currentUser) return [];
  const emailLower = currentUser.email.toLowerCase();
  let filtered = [];
  
  list.forEach(app => {
    if (type === 'pending') {
      const activeRoute = app.routes.find(r => r.step === app.currentStep && r.status === "進行中");
      if (activeRoute && activeRoute.approver.toLowerCase() === emailLower) filtered.push(app);
    } else if (type === 'sent') {
      if (app.applicant.toLowerCase() === emailLower) filtered.push(app);
    } else if (type === 'received') {
      const myPastRoute = app.routes.find(r => r.approver.toLowerCase() === emailLower && (r.status === "承認" || r.status === "決裁" || r.status === "確認"));
      if (myPastRoute) filtered.push(app);
    } else if (type === 'returned') {
      if (app.applicant.toLowerCase() === emailLower && (app.globalStatus === "差し戻し" || app.globalStatus === "却下")) filtered.push(app);
    }
  });
  return filtered;
}

function updateBadges() {
  if (!currentUser) return;
  const emailLower = currentUser.email.toLowerCase();
  
  // 未処理バッジ
  const pBadge = document.getElementById("badge-pending");
  const pendingCount = applicationsList.filter(app => {
    const activeRoute = app.routes.find(r => r.step === app.currentStep && r.status === "進行中");
    return activeRoute && activeRoute.approver.toLowerCase() === emailLower && app.globalStatus === "進行中";
  }).length;
  pBadge.textContent = pendingCount;
  pBadge.className = pendingCount > 0 ? "bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold" : "hidden";

  // 差し戻しバッジ
  const rBadge = document.getElementById("badge-returned");
  const returnedCount = applicationsList.filter(app => app.applicant.toLowerCase() === emailLower && (app.globalStatus === "差し戻し" || app.globalStatus === "却下")).length;
  rBadge.textContent = returnedCount;
  rBadge.className = returnedCount > 0 ? "bg-amber-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold" : "hidden";
}

function renderTableRows(list) {
  const tbody = document.getElementById("data-tbody");
  tbody.innerHTML = "";
  
  if (list.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="py-12 text-center text-slate-400 font-medium">該当データはありません。</td></tr>';
    return;
  }
  
  list.forEach((app, idx) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition-colors border-b border-slate-100 opacity-0";
    
    // 日時のフォーマット
    const createdDate = app.date || "-";
    
    let statusClass = "bg-blue-50 text-blue-700 border-blue-200";
    if (app.globalStatus === "決裁") statusClass = "bg-green-50 text-green-700 border-green-200";
    else if (app.globalStatus === "差し戻し") statusClass = "bg-amber-50 text-amber-700 border-amber-200";
    else if (app.globalStatus === "却下") statusClass = "bg-red-50 text-red-700 border-red-200";
    
    const num = app.appNumber || app.id;
    
    tr.innerHTML = `
      <td class="py-3 px-3 font-mono font-bold text-slate-900">${num}</td>
      <td class="py-3 px-3">${app.formName}</td>
      <td class="py-3 px-3 font-bold">${app.title}</td>
      <td class="py-3 px-3 text-slate-500">${app.applicantName || app.applicant}</td>
      <td class="py-3 px-3 text-slate-400">${createdDate}</td>
      <td class="py-3 px-3"><span class="px-2.5 py-0.5 rounded-full font-bold border text-[10px] ${statusClass}">${app.globalStatus}</span></td>
      <td class="py-3 px-3 text-center"><button onclick="viewDetails('${num}')" class="text-emerald-600 hover:text-emerald-700 font-bold hover:underline">表示</button></td>
    `;
    tbody.appendChild(tr);
    
    gsap.to(tr, { opacity: 1, delay: idx * 0.03, duration: 0.3, ease: "power2.out" });
  });
}

// =================================================================
// 📝 新規申請画面
// =================================================================
window.startNewWorkflow = function() {
  gsap.to("#section-dashboard", {
    opacity: 0,
    y: -10,
    duration: 0.25,
    onComplete: () => {
      document.getElementById("section-dashboard").classList.add("hidden");
      const target = document.getElementById("section-form-selector");
      target.classList.remove("hidden");
      gsap.fromTo(target, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
      renderFormSelectorList();
    }
  });
};

function renderFormSelectorList() {
  const container = document.getElementById("master-form-selector-list");
  container.innerHTML = "";
  
  masterForms.forEach((form, idx) => {
    const div = document.createElement("div");
    div.className = "p-4 hover:bg-slate-50 flex justify-between items-center transition-colors border-b border-slate-100 opacity-0";
    div.innerHTML = `
      <div>
        <h4 class="font-bold text-slate-800 text-sm">${form.name}</h4>
        <p class="text-xs text-slate-400 mt-0.5">${form.description || "説明なし"}</p>
      </div>
      <button onclick="selectFormForApply('${form.id}')" class="bg-emerald-600 text-white font-bold px-4 py-2 rounded-lg text-xs hover:bg-emerald-700 shadow-sm">選択</button>
    `;
    container.appendChild(div);
    gsap.to(div, { opacity: 1, delay: idx * 0.05, duration: 0.35, ease: "power2.out" });
  });
}

window.selectFormForApply = function(formId) {
  const form = masterForms.find(f => f.id === formId);
  if (!form) return;
  
  currentActiveForm = form;
  
  gsap.to("#section-form-selector", {
    opacity: 0,
    y: -10,
    duration: 0.25,
    onComplete: () => {
      document.getElementById("section-form-selector").classList.add("hidden");
      const target = document.getElementById("section-form-submitter");
      target.classList.remove("hidden");
      gsap.fromTo(target, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
      
      document.getElementById("submit-form-name").textContent = form.name;
      document.getElementById("submit-form-desc").textContent = form.description;
      
      userBuiltRoutes = JSON.parse(JSON.stringify(form.routes));
      renderUserRouteBuilder();
      renderUserSelectionPool();
    }
  });
};

window.backToFormSelector = function() {
  gsap.to("#section-form-submitter", {
    opacity: 0,
    y: -10,
    duration: 0.25,
    onComplete: () => {
      document.getElementById("section-form-submitter").classList.add("hidden");
      const target = document.getElementById("section-form-selector");
      target.classList.remove("hidden");
      gsap.fromTo(target, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
    }
  });
};

function renderUserRouteBuilder() {
  const tbody = document.getElementById("user-route-build-tbody");
  tbody.innerHTML = "";
  
  userBuiltRoutes.forEach((route, idx) => {
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-100";
    
    // Firestore の approvers 構造から初期表示用名簿をフォーマット
    const defaultApprovers = route.defaultApprovers || [];
    const approversList = route.approvers || [];
    
    const displayList = approversList.length > 0 
      ? approversList.map(a => `${a.name} (${a.email})`)
      : (defaultApprovers.length > 0 ? defaultApprovers : ["未定"]);
      
    const names = displayList.join(", ");
    
    tr.innerHTML = `
      <td class="p-3 border-r font-bold text-slate-600 bg-slate-50/50">${route.type}</td>
      <td class="p-3 border-r font-bold text-slate-700">${route.role}</td>
      <td class="p-3 font-mono text-slate-500 flex justify-between items-center">
        <span class="max-w-[400px] truncate">${names}</span>
        <button type="button" onclick="editRouteStepApprovers(${idx})" class="text-[10px] text-blue-600 font-bold border border-blue-200 px-2 py-0.5 rounded bg-blue-50">変更</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.editRouteStepApprovers = function(idx) {
  const select = document.getElementById("ins-user-pool-select");
  const selectedOptions = Array.from(select.selectedOptions);
  
  if (selectedOptions.length === 0) {
    alert("右側の「社員名簿プール」から名前を選んだ状態で、変更ボタンを押してください。");
    return;
  }
  
  // 選択された社員情報でルートノードを更新
  userBuiltRoutes[idx].approvers = selectedOptions.map(opt => {
    const userObj = allUsers.find(u => u.email === opt.value);
    return {
      email: opt.value,
      name: userObj ? userObj.name : opt.textContent.split(" ")[0]
    };
  });
  
  // フラグ更新
  userBuiltRoutes[idx].defaultApprovers = selectedOptions.map(opt => opt.value);
  
  renderUserRouteBuilder();
};

function renderUserSelectionPool() {
  const select = document.getElementById("ins-user-pool-select");
  select.innerHTML = "";
  allUsers.forEach(u => {
    const opt = document.createElement("option");
    opt.value = u.email;
    opt.textContent = `${u.name} [${u.dept} - ${u.title || "一般"}]`;
    select.appendChild(opt);
  });
}

// 社員名簿プール検索フィルター
window.filterApplicantUserPool = function() {
  const val = document.getElementById("ins-user-filter").value.toLowerCase();
  const select = document.getElementById("ins-user-pool-select");
  
  Array.from(select.options).forEach(opt => {
    const visible = opt.textContent.toLowerCase().includes(val);
    opt.style.display = visible ? "" : "none";
  });
};

// 申請前確認へ
window.proceedToConfirmationStep = function(event) {
  event.preventDefault();
  const title = document.getElementById("ins-title").value;
  const pdfFile = document.getElementById("ins-pdf").files[0];
  
  document.getElementById("conf-title").textContent = title;
  document.getElementById("conf-applicant").textContent = currentUser.name;
  document.getElementById("conf-file-name").textContent = pdfFile ? pdfFile.name : "未添付 (PDF)";
  
  const tbody = document.getElementById("conf-route-tbody");
  tbody.innerHTML = "";
  userBuiltRoutes.forEach(r => {
    const displayList = r.approvers 
      ? r.approvers.map(a => `${a.name} [${r.role}]`)
      : (r.defaultApprovers || ["未定"]);
    const names = displayList.join(", ");
    
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-100 text-xs";
    tr.innerHTML = `
      <td class="p-2.5 border-r border-slate-200 text-center font-bold text-slate-500 bg-slate-50/50">ステップ ${r.step}</td>
      <td class="p-2.5 border-r border-slate-200 font-bold">${r.role}</td>
      <td class="p-2.5 font-mono text-slate-700">${names}</td>
    `;
    tbody.appendChild(tr);
  });
  
  gsap.to("#section-form-submitter", {
    opacity: 0,
    y: -10,
    duration: 0.25,
    onComplete: () => {
      document.getElementById("section-form-submitter").classList.add("hidden");
      const target = document.getElementById("section-form-confirmation");
      target.classList.remove("hidden");
      gsap.fromTo(target, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
    }
  });
};

window.backToInputForm = function() {
  gsap.to("#section-form-confirmation", {
    opacity: 0,
    y: -10,
    duration: 0.25,
    onComplete: () => {
      document.getElementById("section-form-confirmation").classList.add("hidden");
      const target = document.getElementById("section-form-submitter");
      target.classList.remove("hidden");
      gsap.fromTo(target, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.45, ease: "power2.out" });
    }
  });
};

// 申請送信処理 (Flask API 連携)
window.executeWorkflowSubmission = function() {
  const title = document.getElementById("conf-title").textContent;
  const fileName = document.getElementById("conf-file-name").textContent;
  
  showLoadingOverlay("申請書を作成中...", "データをサーバーへ書き込み保存しています。");
  
  // Submit routes payload
  const submitRoutes = userBuiltRoutes.map((r) => {
    // 最初の担当者を決定 (決裁/承認者は、設定されたプール内の最初の1人とする)
    const firstApprover = r.approvers && r.approvers.length > 0 
      ? r.approvers[0].email 
      : (r.defaultApprovers && r.defaultApprovers.length > 0 ? r.defaultApprovers[0] : "未定");
      
    return {
      step: r.step,
      role: r.role,
      type: r.type,
      approver: firstApprover,
      approverName: r.approvers && r.approvers.length > 0 ? r.approvers[0].name : "未定",
      status: "未到達", // 後ほど backend 側で step1/step2 の進行中が設定されます
      actionAt: "-",
      comment: "-"
    };
  });
  
  fetch('/api/applications/submit', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      formId: currentActiveForm.id,
      formName: currentActiveForm.name,
      title: title,
      pdfName: fileName,
      routes: submitRoutes
    })
  })
  .then(res => res.json())
  .then(data => {
    hideLoadingOverlay();
    if (data.success) {
      alert(`稟議申請が完了しました！\n申請番号: No.${data.appNumber}`);
      switchMenu('sent');
    } else {
      alert(`申請エラー: ${data.error}`);
    }
  })
  .catch(err => {
    hideLoadingOverlay();
    alert(`通信エラーが発生しました: ${err.message}`);
  });
};

// =================================================================
// 📄 詳細モーダル
// =================================================================
let activeDetailedAppNumber = null;

window.viewDetails = function(appNumber) {
  activeDetailedAppNumber = appNumber;
  let app = applicationsList.find(a => a.appNumber === appNumber);
  if (!app) return;
  
  document.getElementById("det-applicant").textContent = app.applicantName || app.applicant;
  document.getElementById("det-date").textContent = app.date || "-";
  document.getElementById("det-type").textContent = app.formName;
  document.getElementById("det-title").textContent = app.title;
  
  const fileContainer = document.getElementById("det-pdf-link");
  fileContainer.innerHTML = `<a href="${app.pdfUrl}" class="text-blue-600 hover:underline font-bold font-mono text-[11px]">📄 ${app.pdfName}</a>`;
  
  const timelineTbody = document.getElementById("modal-timeline-tbody");
  timelineTbody.innerHTML = "";
  
  app.routes.forEach(r => {
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-100 text-xs";
    
    let statusBadge = `<span class="bg-slate-50 text-slate-500 border border-slate-200 px-2 py-0.5 rounded-full font-bold">${r.status}</span>`;
    if (r.status === "承認") statusBadge = `<span class="bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full font-bold">承認</span>`;
    else if (r.status === "決裁") statusBadge = `<span class="bg-green-100 text-green-800 border border-green-300 px-2 py-0.5 rounded-full font-bold">決裁</span>`;
    else if (r.status === "確認") statusBadge = `<span class="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full font-bold">確認</span>`;
    else if (r.status === "進行中") statusBadge = `<span class="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-bold animate-pulse">進行中</span>`;
    else if (r.status === "差し戻し") statusBadge = `<span class="bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-bold">差し戻し</span>`;
    else if (r.status === "却下") statusBadge = `<span class="bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full font-bold">却下</span>`;
    
    const dispName = r.name || r.approverName || r.approver;
    
    tr.innerHTML = `
      <td class="p-2 border-r text-center font-bold text-slate-500">${r.step}</td>
      <td class="p-2 border-r font-bold">${r.role}</td>
      <td class="p-2 border-r font-medium">${dispName}</td>
      <td class="p-2 border-r text-center">${statusBadge}</td>
      <td class="p-2 border-r">${r.comment || "-"}</td>
      <td class="p-2 text-slate-400 font-mono">${r.time || r.actionAt || "-"}</td>
    `;
    timelineTbody.appendChild(tr);
  });
  
  const buttonsContainer = document.getElementById("modal-buttons-container");
  buttonsContainer.innerHTML = "";
  document.getElementById("modal-comment-area").classList.add("hidden");
  
  const activeStep = app.routes.find(r => r.step === app.currentStep && r.status === "進行中");
  const emailLower = currentUser.email.toLowerCase();
  
  if (activeStep && activeStep.approver.toLowerCase() === emailLower && app.globalStatus === "進行中") {
    document.getElementById("modal-comment-area").classList.remove("hidden");
    document.getElementById("modal-comment").value = "";
    
    const isKessai = activeStep.role.includes("決裁");
    const label = isKessai ? "決裁する" : "承認する";
    
    buttonsContainer.innerHTML = `
      <button onclick="executeAction('reject')" class="bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 font-bold px-4 py-2 rounded-lg text-xs">却下</button>
      <button onclick="executeAction('return')" class="bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 font-bold px-4 py-2 rounded-lg text-xs">差し戻し</button>
      <button onclick="executeAction('approve')" class="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-2 rounded-lg text-xs shadow-md">${label}</button>
    `;
  }
  
  document.getElementById("action-modal").classList.remove("hidden");
  gsap.fromTo("#action-modal-card", 
    { scale: 0.95, opacity: 0, y: 15 }, 
    { scale: 1, opacity: 1, y: 0, duration: 0.45, ease: "back.out(1.5)" }
  );
};

window.closeActionModal = function() {
  gsap.to("#action-modal-card", {
    scale: 0.95,
    opacity: 0,
    y: 15,
    duration: 0.3,
    ease: "power2.in",
    onComplete: () => {
      document.getElementById("action-modal").classList.add("hidden");
    }
  });
};

// 承認アクション送信
window.executeAction = function(actionType) {
  const comment = document.getElementById("modal-comment").value.trim();
  if ((actionType === 'reject' || actionType === 'return') && !comment) {
    alert("差し戻し・却下時には、コメント（理由）を入力してください。");
    return;
  }
  
  showLoadingOverlay("データを更新中...", "変更をデータベースに書き込んでいます。");
  
  fetch('/api/applications/action', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      appNumber: activeDetailedAppNumber,
      action: actionType,
      comment: comment
    })
  })
  .then(res => res.json())
  .then(data => {
    hideLoadingOverlay();
    closeActionModal();
    if (data.success) {
      alert("処理が完了しました！");
      fetchAndBindApplications(currentView);
    } else {
      alert(`処理エラー: ${data.error}`);
    }
  })
  .catch(err => {
    hideLoadingOverlay();
    closeActionModal();
    alert(`通信エラー: ${err.message}`);
  });
};

// =================================================================
// ⚙️ 管理者パネル
// =================================================================
window.switchAdminTab = function(tabKey) {
  document.getElementById("tab-adm-storage").classList.remove("tab-active");
  document.getElementById("tab-adm-route").classList.remove("tab-active");
  document.getElementById("sub-panel-storage").classList.add("hidden");
  document.getElementById("sub-panel-route").classList.add("hidden");
  
  const contentEl = tabKey === 'storage' ? document.getElementById("sub-panel-storage") : document.getElementById("sub-panel-route");
  
  if (tabKey === 'storage') {
    document.getElementById("tab-adm-storage").classList.add("tab-active");
    renderAdminStorageLogs();
  } else {
    document.getElementById("tab-adm-route").classList.add("tab-active");
    renderAdminFormList();
  }
  
  contentEl.classList.remove("hidden");
  gsap.fromTo(contentEl, { opacity: 0, x: 15 }, { opacity: 1, x: 0, duration: 0.35, ease: "power2.out" });
};

function renderAdminStorageLogs() {
  const tbody = document.getElementById("storage-meta-tbody");
  tbody.innerHTML = "";
  
  // 静的履歴ログ (モック)
  const logs = [
    { month: "2026年07月度", fileName: "202607_稟議データ", fileUrl: "#", pdfFolderName: "202607", pdfFolderUrl: "#", applicationCount: applicationsList.length, updated: new Date().toLocaleString() }
  ];
  
  logs.forEach(l => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 border-b border-slate-100 text-xs";
    tr.innerHTML = `
      <td class="p-3 font-bold text-slate-800">${l.month}</td>
      <td class="p-3 border-l"><a href="${l.fileUrl}" class="text-blue-600 hover:underline font-bold">📈 ${l.fileName} ➔</a></td>
      <td class="p-3 border-l"><a href="${l.pdfFolderUrl}" class="text-indigo-600 hover:underline font-bold">📁 02_Attachments/${l.pdfFolderName} ➔</a></td>
      <td class="p-3 border-l text-center font-black text-blue-800 bg-blue-50/50">${l.applicationCount} 件</td>
      <td class="p-3 border-l text-slate-400">${l.updated}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderAdminFormList() {
  const container = document.getElementById("admin-form-list");
  container.innerHTML = "";
  
  masterForms.forEach((form, idx) => {
    const div = document.createElement("div");
    div.className = "p-3 hover:bg-white flex justify-between items-center transition-colors border-b border-slate-150 cursor-pointer opacity-0";
    div.onclick = () => selectFormForAdminEdit(form.id);
    div.innerHTML = `
      <div class="min-w-0 flex-1">
        <h5 class="font-bold text-slate-800 text-xs truncate">${form.name}</h5>
        <p class="text-[10px] text-slate-400 truncate">${form.description || "説明なし"}</p>
      </div>
      <button onclick="event.stopPropagation(); deleteFormFromAdmin('${form.id}')" class="text-red-500 hover:text-red-700 font-bold text-[10px] px-2 py-1">削除</button>
    `;
    container.appendChild(div);
    gsap.to(div, { opacity: 1, delay: idx * 0.03, duration: 0.25, ease: "power2.out" });
  });
}

window.selectFormForAdminEdit = function(formId) {
  const form = masterForms.find(f => f.id === formId);
  if (!form) return;
  
  adminActiveForm = form;
  document.getElementById("adm-form-id").value = form.id;
  document.getElementById("adm-form-name").value = form.name;
  document.getElementById("adm-form-desc").value = form.description || "";
  
  adminTableRows = JSON.parse(JSON.stringify(form.routes));
  renderAdminTableRows();
};

function renderAdminTableRows() {
  const tbody = document.getElementById("adm-table-rows-tbody");
  tbody.innerHTML = "";
  
  adminTableRows.forEach((r, idx) => {
    const tr = document.createElement("tr");
    tr.className = "border-b border-slate-200 text-[10px]";
    
    // Firestore の内部構造に合わせて初期表示
    const displayList = r.approvers 
      ? r.approvers.map(a => a.email)
      : (r.defaultApprovers || []);
    const approversText = displayList.join(", ");
    
    tr.innerHTML = `
      <td class="p-1.5"><input type="text" class="w-full border p-1 rounded" value="${r.type}" onchange="updateAdminRowValue(${idx}, 'type', this.value)"></td>
      <td class="p-1.5"><input type="text" class="w-full border p-1 rounded" value="${r.role}" onchange="updateAdminRowValue(${idx}, 'role', this.value)"></td>
      <td class="p-1.5"><input type="text" class="w-full border p-1 rounded font-mono" value="${approversText}" onchange="updateAdminRowApprovers(${idx}, this.value)"></td>
      <td class="p-1.5 text-center"><button onclick="deleteAdminRow(${idx})" class="text-red-500 hover:text-red-700 font-bold">❌</button></td>
    `;
    tbody.appendChild(tr);
  });
}

window.updateAdminRowValue = function(idx, field, val) {
  adminTableRows[idx][field] = val;
};

window.updateAdminRowApprovers = function(idx, val) {
  const emails = val.split(",").map(s => s.trim()).filter(Boolean);
  adminTableRows[idx].defaultApprovers = emails;
  adminTableRows[idx].approvers = emails.map(email => {
    const userObj = allUsers.find(u => u.email === email);
    return {
      email: email,
      name: userObj ? userObj.name : email.split("@")[0]
    };
  });
};

window.deleteAdminRow = function(idx) {
  adminTableRows.splice(idx, 1);
  renderAdminTableRows();
};

window.addNewRowToAdminEditor = function() {
  const nextStep = adminTableRows.length + 1;
  adminTableRows.push({
    step: nextStep,
    role: "新規審査役",
    type: "承認（全員）",
    defaultApprovers: [],
    approvers: []
  });
  renderAdminTableRows();
};

window.executeSaveMasterForm = function() {
  const formId = document.getElementById("adm-form-id").value.trim();
  const formName = document.getElementById("adm-form-name").value.trim();
  const formDesc = document.getElementById("adm-form-desc").value.trim();
  
  if (!formId || !formName) {
    alert("フォームIDおよびフォーム名称を入力してください。");
    return;
  }
  
  showLoadingOverlay("マスターを更新中...", "変更を保存しています。");
  
  fetch('/api/admin/forms/save', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      id: formId,
      name: formName,
      description: formDesc,
      routes: adminTableRows,
      sortOrder: adminActiveForm ? adminActiveForm.sortOrder : masterForms.length + 1
    })
  })
  .then(res => res.json())
  .then(data => {
    hideLoadingOverlay();
    if (data.success) {
      alert("申請フォーム設定を保存しました！");
      loadInitialData().then(() => renderAdminFormList());
    } else {
      alert(`保存エラー: ${data.error}`);
    }
  })
  .catch(err => {
    hideLoadingOverlay();
    alert(`通信エラー: ${err.message}`);
  });
};

window.createNewFormInEditor = function() {
  adminActiveForm = null;
  document.getElementById("adm-form-id").value = "";
  document.getElementById("adm-form-name").value = "";
  document.getElementById("adm-form-desc").value = "";
  adminTableRows = [];
  renderAdminTableRows();
};

window.deleteFormFromAdmin = function(formId) {
  if (!confirm("この申請フォームを完全に削除しますか？")) return;
  
  showLoadingOverlay("フォームを削除中...", "データベースから削除しています。");
  
  fetch(`/api/admin/forms/delete/${formId}`, {
    method: 'POST'
  })
  .then(res => res.json())
  .then(data => {
    hideLoadingOverlay();
    if (data.success) {
      alert("削除しました。");
      loadInitialData().then(() => renderAdminFormList());
    } else {
      alert(`削除エラー: ${data.error}`);
    }
  })
  .catch(err => {
    hideLoadingOverlay();
    alert(`通信エラー: ${err.message}`);
  });
};

// =================================================================
// ⚙️ 共通ローディング制御
// =================================================================
function showLoadingOverlay(title, desc) {
  document.getElementById('loading-title').textContent = title;
  document.getElementById('loading-desc').textContent = desc;
  
  const overlay = document.getElementById('loading-overlay');
  overlay.classList.remove('hidden');
  gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.3 });
}

function hideLoadingOverlay() {
  const overlay = document.getElementById('loading-overlay');
  gsap.to(overlay, { 
    opacity: 0, 
    duration: 0.25, 
    onComplete: () => overlay.classList.add('hidden') 
  });
}
