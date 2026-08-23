import customtkinter as ctk
import webbrowser
import os
import sys

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def launch():
    app = ctk.CTk()
    app.title("ForestTaskMiningSystem")
    app.geometry("450x300")
    app.resizable(False, False)
    
    import json
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    user_id = ""
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                user_id = json.load(f).get("uuid", "")
    except:
        pass
    
    # ローカルのプロキシサーバーが提供するダッシュボードのURL
    base_url = "http://127.0.0.1:18080"
    
    lbl_title = ctk.CTkLabel(app, text="FOREST TASK MINING\nSYSTEM", font=("Consolas", 24, "bold"), text_color="#00e5ff")
    lbl_title.pack(pady=30)
    
    def open_dept_web():
        webbrowser.open(f"{base_url}/dashboard")
        app.destroy()

    def open_personal_web():
        import time
        t = int(time.time())
        url = f"{base_url}/user_dashboard?user_id={user_id}&_t={t}" if user_id else f"{base_url}/user_dashboard?_t={t}"
        webbrowser.open(url)
        app.destroy()
        
    def open_stream():
        stream_win = ctk.CTkToplevel(app)
        stream_win.title("ForestTaskMiningSystem - Live Stream")
        stream_win.geometry("800x500")
        stream_win.configure(fg_color="#000000")
        
        textbox = ctk.CTkTextbox(stream_win, font=("Consolas", 14), fg_color="#000000", text_color="#00ff00")
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stream.log")
        
        def update_log():
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                textbox.delete("1.0", "end")
                textbox.insert("end", content)
                textbox.see("end")
            stream_win.after(1000, update_log)
            
        update_log()
        
    btn_dept = ctk.CTkButton(app, text="🏢 部門用ダッシュボードを開く", command=open_dept_web, font=("Meiryo", 16, "bold"), width=300, height=45, fg_color="#00e5ff", text_color="#000000", hover_color="#00b3cc")
    btn_dept.pack(pady=5)

    btn_personal = ctk.CTkButton(app, text="👤 個人用ダッシュボードを開く", command=open_personal_web, font=("Meiryo", 16, "bold"), width=300, height=45, fg_color="#00e5ff", text_color="#000000", hover_color="#00b3cc")
    btn_personal.pack(pady=5)
    
    btn_stream = ctk.CTkButton(app, text="💻 リアルタイムストリームを見る", command=open_stream, font=("Meiryo", 16, "bold"), width=300, height=45, fg_color="#333333", hover_color="#444444")
    btn_stream.pack(pady=5)
    
    # 常に最前面に表示
    app.attributes('-topmost', True)
    app.mainloop()

if __name__ == "__main__":
    launch()
