import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import threading
import os
import sys
from google.oauth2 import service_account
import google.auth.transport.requests

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

SERVER_URL = "https://task-mining-server-1097969102143.asia-northeast1.run.app"
# client-key.json は実行ファイルと同じか上の階層にあると想定
KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "client-key.json")

def get_headers():
    try:
        credentials = service_account.IDTokenCredentials.from_service_account_file(
            KEY_PATH, target_audience=SERVER_URL
        )
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {credentials.token}'
        }
    except Exception as e:
        print(f"Auth error: {e}")
        return {}

class DashboardWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ForestTaskMiningSystem - NEXUS DASHBOARD")
        self.geometry("850x600")
        self.configure(fg_color="#0a0a0a")
        
        # Header
        self.header = ctk.CTkLabel(
            self, text="NEXUS INTELLIGENCE", 
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color="#00e5ff"
        )
        self.header.pack(pady=20)
        
        # Stats Frame
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=30, pady=10)
        
        self.lbl_logs = self.create_stat_card("TOTAL LOGS", "0", 0)
        self.lbl_users = self.create_stat_card("ACTIVE USERS", "0", 1)
        self.lbl_clients = self.create_stat_card("CLIENTS (1H)", "0", 2)
        
        self.stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Chart Frame
        self.chart_frame = ctk.CTkFrame(self, fg_color="#111111", corner_radius=10, border_color="#333", border_width=1)
        self.chart_frame.pack(fill="both", expand=True, padx=30, pady=20)
        
        self.canvas_widget = None
        
        self.btn_refresh = ctk.CTkButton(
            self, text="REFRESH DATA", command=self.load_data,
            fg_color="#00e5ff", text_color="#000", hover_color="#00b3cc",
            font=ctk.CTkFont(family="Consolas", weight="bold")
        )
        self.btn_refresh.pack(pady=(0, 20))
        
        # Load data on start
        self.after(100, self.load_data)

    def create_stat_card(self, title, value, col):
        frame = ctk.CTkFrame(self.stats_frame, fg_color="#1a1a1a", border_color="#00e5ff", border_width=1, corner_radius=8)
        frame.grid(row=0, column=col, padx=10, sticky="ew")
        
        lbl_title = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(family="Consolas", size=12), text_color="#888888")
        lbl_title.pack(pady=(15, 0))
        
        lbl_val = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(family="Consolas", size=32, weight="bold"), text_color="#ffffff")
        lbl_val.pack(pady=(0, 15))
        return lbl_val

    def load_data(self):
        self.btn_refresh.configure(text="LOADING...", state="disabled")
        threading.Thread(target=self._fetch_data, daemon=True).start()
        
    def _fetch_data(self):
        try:
            headers = get_headers()
            url = f"{SERVER_URL}/api/settings/system_status"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                self.after(0, self._update_ui, data)
            else:
                self.after(0, self._show_error, f"Error: {res.status_code}")
        except Exception as e:
            self.after(0, self._show_error, str(e))
            
    def _update_ui(self, data):
        self.lbl_logs.configure(text=f"{data.get('total_logs', 0):,}")
        self.lbl_users.configure(text=f"{data.get('total_users', 0):,}")
        self.lbl_clients.configure(text=f"{data.get('active_clients', 0):,}")
        
        labels = data.get("chart_labels", [])
        values = data.get("chart_data", [])
        
        if self.canvas_widget:
            self.canvas_widget.destroy()
            
        fig, ax = plt.subplots(figsize=(8, 3.5), facecolor='#111111')
        ax.set_facecolor('#111111')
        
        ax.plot(labels, values, color='#00e5ff', linewidth=2.5, marker='o', markersize=5, markerfacecolor='#111', markeredgecolor='#00e5ff')
        
        # Styling
        ax.spines['bottom'].set_color('#444')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#444')
        ax.tick_params(axis='x', colors='#aaa', rotation=45)
        ax.tick_params(axis='y', colors='#aaa')
        ax.grid(True, linestyle='--', alpha=0.15, color='#00e5ff')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas_widget = canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.btn_refresh.configure(text="REFRESH DATA", state="normal")

    def _show_error(self, msg):
        self.lbl_logs.configure(text="ERR")
        print(f"Dashboard fetch error: {msg}")
        self.btn_refresh.configure(text="RETRY", state="normal")

if __name__ == "__main__":
    app = DashboardWindow()
    app.mainloop()
