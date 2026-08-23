using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace TaskMinerXP
{
    public class InputHook
    {
        private StringBuilder _keyBuffer = new StringBuilder();
        private DateTime _lastKeyTime = DateTime.Now;

        private IntPtr _keyboardHookId = IntPtr.Zero;
        private NativeMethods.HookProc _keyboardProc;
        private object _lockObj = new object();

        public InputHook()
        {
            _keyboardProc = KeyboardHookCallback;
        }

        public void Start()
        {
            using (Process curProcess = Process.GetCurrentProcess())
            using (ProcessModule curModule = curProcess.MainModule)
            {
                IntPtr hMod = NativeMethods.GetModuleHandle(curModule.ModuleName);
                _keyboardHookId = NativeMethods.SetWindowsHookEx(NativeMethods.WH_KEYBOARD_LL, _keyboardProc, hMod, 0);
            }
        }

        public void Stop()
        {
            if (_keyboardHookId != IntPtr.Zero)
            {
                NativeMethods.UnhookWindowsHookEx(_keyboardHookId);
                _keyboardHookId = IntPtr.Zero;
            }
        }

        public string GetAndResetKeyBufferIfIdle(double idleSecondsThreshold)
        {
            lock (_lockObj)
            {
                if (_keyBuffer.Length > 0 && (DateTime.Now - _lastKeyTime).TotalSeconds > idleSecondsThreshold)
                {
                    string keys = _keyBuffer.ToString();
                    _keyBuffer.Length = 0;
                    return keys;
                }
                return "";
            }
        }

        private IntPtr KeyboardHookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (nCode >= 0 && (wParam == (IntPtr)NativeMethods.WM_KEYDOWN || wParam == (IntPtr)NativeMethods.WM_SYSKEYDOWN))
            {
                int vkCode = Marshal.ReadInt32(lParam);
                Keys key = (Keys)vkCode;

                lock (_lockObj)
                {
                    _lastKeyTime = DateTime.Now;

                    bool isCtrl = (NativeMethodsHelper.GetKeyState((int)Keys.ControlKey) & 0x8000) != 0;
                    if (isCtrl)
                    {
                        if (key == Keys.C) _keyBuffer.Append("[Ctrl+C]");
                        else if (key == Keys.V) _keyBuffer.Append("[Ctrl+V]");
                        else if (key == Keys.X) _keyBuffer.Append("[Ctrl+X]");
                        else if (key == Keys.Z) _keyBuffer.Append("[Ctrl+Z]");
                        else if (key == Keys.A) _keyBuffer.Append("[Ctrl+A]");
                        else if (key == Keys.S) _keyBuffer.Append("[Ctrl+S]");
                        else if (key == Keys.F) _keyBuffer.Append("[Ctrl+F]");
                    }
                    else
                    {
                        // 簡易的なキー変換（英数字と一部の特殊キーのみ対応）
                        if ((key >= Keys.A && key <= Keys.Z) || (key >= Keys.D0 && key <= Keys.D9))
                        {
                            _keyBuffer.Append(key.ToString().ToLower());
                        }
                        else if (key == Keys.Enter) _keyBuffer.Append("[Enter]");
                        else if (key == Keys.Back) _keyBuffer.Append("[Back]");
                        else if (key == Keys.Space) _keyBuffer.Append(" ");
                    }
                }
            }
            return NativeMethods.CallNextHookEx(_keyboardHookId, nCode, wParam, lParam);
        }
    }

    internal static class NativeMethodsHelper
    {
        [DllImport("user32.dll")]
        public static extern short GetKeyState(int nVirtKey);
    }
}
