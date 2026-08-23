using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace TaskMinerXP
{
    public class TaskMinerManager
    {
        private System.Windows.Forms.Timer _pollingTimer;
        private InputHook _inputHook;
        private ClipboardMonitor _clipboardMonitor;
        private AsyncCsvWriter _csvWriter;
        private Form _parentForm;

        private string _lastClipboard = "";
        private string _lastActiveApp = "";
        private string _sourceAppOfClipboard = "";
        
        private ExcelComHook _excelHook;
        
        // プロセス名のキャッシュ (PID -> AppName)
        private Dictionary<uint, string> _pidCache = new Dictionary<uint, string>();

        public TaskMinerManager(Form parentForm, string baseDir)
        {
            _parentForm = parentForm;
            _csvWriter = new AsyncCsvWriter(baseDir);
            _inputHook = new InputHook();
            _clipboardMonitor = new ClipboardMonitor(parentForm.Handle);
            _excelHook = new ExcelComHook(_csvWriter);

            _pollingTimer = new System.Windows.Forms.Timer();
            _pollingTimer.Interval = 500; // 500ms
            _pollingTimer.Tick += PollingTimer_Tick;
        }

        public void Start()
        {
            _csvWriter.Start();
            _inputHook.Start();
            _excelHook.Start();
            _pollingTimer.Start();
        }

        public void Stop()
        {
            _pollingTimer.Stop();
            _excelHook.Stop();
            _inputHook.Stop();
            _clipboardMonitor.Stop();
            _csvWriter.Stop();
        }

        private void PollingTimer_Tick(object sender, EventArgs e)
        {
            try
            {
                IntPtr fgHwnd = NativeMethods.GetForegroundWindow();
                string title = GetWindowTitle(fgHwnd);
                string appName = GetApplicationName(fgHwnd);

                // ブラウザ・AI検知ロジック
                appName = DetectBrowserAndAI(appName, title);

                // 転記判定 (Paste検知)
                if (appName != _lastActiveApp && !string.IsNullOrEmpty(_lastActiveApp))
                {
                    if (!string.IsNullOrEmpty(_sourceAppOfClipboard) && _sourceAppOfClipboard != appName && !string.IsNullOrEmpty(_lastClipboard))
                    {
                        string snippet = _lastClipboard.Length > 50 ? _lastClipboard.Substring(0, 50) + "..." : _lastClipboard;
                        _csvWriter.EnqueueLog(appName, "PotentialTransfer (Paste)", title, string.Format("Source: {0}, Data:[{1}]", _sourceAppOfClipboard, snippet));
                    }
                }
                
                _lastActiveApp = appName;

                // クリップボード監視
                string currentClipboard = _clipboardMonitor.GetAndResetLastCopiedContent();
                if (!string.IsNullOrEmpty(currentClipboard) && currentClipboard != _lastClipboard)
                {
                    _lastClipboard = currentClipboard;
                    _sourceAppOfClipboard = appName;
                    
                    int size = currentClipboard.Length;
                    string snippet = currentClipboard.Length > 100 ? currentClipboard.Substring(0, 100) + "..." : currentClipboard;
                    _csvWriter.EnqueueLog(appName, "Copy", title, string.Format("Size:{0} chars, Data:[{1}]", size, snippet));
                }

                // キーロガーフラッシュ
                string keys = _inputHook.GetAndResetKeyBufferIfIdle(1.5);
                if (!string.IsNullOrEmpty(keys))
                {
                    _csvWriter.EnqueueLog(appName, "KeyLog", title, string.Format("Keys:{0}", keys));
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("PollingTimer Error: " + ex.Message);
            }
        }

        private string DetectBrowserAndAI(string appName, string title)
        {
            string appLower = appName.ToLower();
            string titleLower = title.ToLower();

            if (appLower.Contains("chrome") || appLower.Contains("msedge") || appLower.Contains("firefox"))
            {
                string[] aiKeywords = { "chatgpt", "claude", "gemini", "copilot", "perplexity" };
                foreach (string kw in aiKeywords)
                {
                    if (titleLower.Contains(kw)) return string.Format("AI({0})", kw);
                }

                string[] mailKeywords = { "gmail", "outlook", "yahoo" };
                foreach (string kw in mailKeywords)
                {
                    if (titleLower.Contains(kw)) return string.Format("WebMail({0})", kw);
                }
            }
            return appName;
        }

        private string GetWindowTitle(IntPtr hWnd)
        {
            if (hWnd == IntPtr.Zero) return "Unknown";
            StringBuilder sb = new StringBuilder(512);
            NativeMethods.GetWindowText(hWnd, sb, sb.Capacity);
            return sb.ToString();
        }

        private string GetApplicationName(IntPtr hWnd)
        {
            if (hWnd == IntPtr.Zero) return "Unknown";
            uint pid;
            NativeMethods.GetWindowThreadProcessId(hWnd, out pid);
            
            // プロセス名のキャッシュを利用
            if (_pidCache.ContainsKey(pid))
            {
                return _pidCache[pid];
            }

            IntPtr hProcess = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_INFORMATION | NativeMethods.PROCESS_VM_READ, false, pid);
            if (hProcess != IntPtr.Zero)
            {
                StringBuilder sb = new StringBuilder(512);
                if (NativeMethods.GetModuleBaseName(hProcess, IntPtr.Zero, sb, (uint)sb.Capacity) > 0)
                {
                    NativeMethods.CloseHandle(hProcess);
                    string name = sb.ToString();
                    _pidCache[pid] = name; // キャッシュに保存
                    return name;
                }
                NativeMethods.CloseHandle(hProcess);
            }
            
            _pidCache[pid] = "Unknown";
            return "Unknown";
        }
    }
}
