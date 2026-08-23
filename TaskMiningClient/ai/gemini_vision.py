import os
from PIL import ImageGrab
import google.generativeai as genai

# APIキーは将来的にクラウドへ移すが、過渡期としてローカル設定を読む
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def init_vision_api():
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    return False

def analyze_screen_in_memory():
    """
    SSDに保存せず、メモリ上でスクショを取得してGemini Vision APIへ直接投げる（インメモリ処理）
    """
    try:
        # メモリ上でスクリーンショットを取得
        screenshot = ImageGrab.grab()
        
        # ※【完全なシンクライアント化】の際は、ここでPIL画像をbase64文字列に変換し、キュー（DB）へ送るだけにします。
        
        # 【過渡期の実装】ローカルで一時的にGeminiを呼ぶ場合
        if not GEMINI_API_KEY:
            return "【Cloud送信待ち】スクショ画像取得済（ローカルAPIキー未設定）"
        
        init_vision_api()
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = "この画面でユーザーがどのような業務（何のアプリで、どういう操作）を行っているか、15文字以内で簡潔に説明してください。個人情報・機密情報は含めないでください。"
        
        response = model.generate_content([prompt, screenshot])
        return response.text.strip()
    except Exception as e:
        return f"[Vision Error] {e}"
