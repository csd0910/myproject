import sys

try:
    with open('static/user_dashboard.html', 'r', encoding='utf-8') as f:
        content = f.read()

    replacements = {
        'bg-slate-50': 'bg-slate-900',
        'bg-white': 'bg-slate-800',
        'text-slate-700': 'text-slate-300',
        'text-slate-800': 'text-slate-200',
        'text-slate-500': 'text-slate-400',
        'border-slate-200': 'border-slate-700',
        'bg-indigo-50': 'bg-slate-800',
        'text-indigo-800': 'text-indigo-300',
        'bg-indigo-200': 'bg-indigo-900',
        'bg-slate-200': 'bg-slate-700',
        'text-indigo-700': 'text-indigo-400',
        'text-teal-800': 'text-teal-300',
        'border-teal-500': 'border-teal-400',
        'bg-rose-200': 'bg-rose-900',
        'text-rose-700': 'text-rose-400',
        'text-rose-800': 'text-rose-300',
        '🌐 詳細DX抽出レポート (ミクロビュー)': '🌐 詳細DX抽出レポート',
        '部門マクロビューへ戻る': '部門データ参照',
        '<span>🌐</span> 部門データ参照': '<span>🏢</span> 部門データ参照',
        '<div class="ml-auto flex gap-2">': '<div class="flex gap-2">',
        'bg-slate-900 p-8': 'bg-slate-800 p-8', # Adjust if bg-white became bg-slate-800
        'bg-[#0f172a]': 'bg-slate-900', # To match dashboard.html body
        'bg-[rgba(30,41,59,0.7)]': 'bg-slate-800/80',
    }

    for old, new in replacements.items():
        content = content.replace(old, new)
        
    with open('static/user_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print('Replaced colors and text in user_dashboard.html')
except Exception as e:
    print("Error:", e)
