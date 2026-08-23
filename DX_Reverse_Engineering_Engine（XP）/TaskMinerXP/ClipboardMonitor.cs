using System;
using System.Drawing;
using System.Windows.Forms;

namespace TaskMinerXP
{
    public class ClipboardMonitor : NativeWindow
    {
        private IntPtr _nextClipboardViewer;
        private string _lastCopiedContent = "";
        private object _lockObj = new object();

        public ClipboardMonitor(IntPtr hWnd)
        {
            this.AssignHandle(hWnd);
            _nextClipboardViewer = NativeMethods.SetClipboardViewer(this.Handle);
        }

        public void Stop()
        {
            NativeMethods.ChangeClipboardChain(this.Handle, _nextClipboardViewer);
            this.ReleaseHandle();
        }

        public string GetAndResetLastCopiedContent()
        {
            lock (_lockObj)
            {
                string content = _lastCopiedContent;
                _lastCopiedContent = "";
                return content;
            }
        }

        protected override void WndProc(ref Message m)
        {
            switch (m.Msg)
            {
                case NativeMethods.WM_DRAWCLIPBOARD:
                    ExtractClipboardContent();
                    NativeMethods.SendMessage(_nextClipboardViewer, m.Msg, m.WParam, m.LParam);
                    break;

                case NativeMethods.WM_CHANGECBCHAIN:
                    if (m.WParam == _nextClipboardViewer)
                    {
                        _nextClipboardViewer = m.LParam;
                    }
                    else if (_nextClipboardViewer != IntPtr.Zero)
                    {
                        NativeMethods.SendMessage(_nextClipboardViewer, m.Msg, m.WParam, m.LParam);
                    }
                    break;

                default:
                    base.WndProc(ref m);
                    break;
            }
        }

        private void ExtractClipboardContent()
        {
            try
            {
                if (Clipboard.ContainsText())
                {
                    string text = Clipboard.GetText();
                    text = text.Replace("\r", " ").Replace("\n", " ").Replace(",", "，");
                    
                    lock (_lockObj)
                    {
                        _lastCopiedContent = text;
                    }
                }
                else if (Clipboard.ContainsImage())
                {
                    lock (_lockObj)
                    {
                        _lastCopiedContent = "[Image]";
                    }
                }
                else if (Clipboard.ContainsFileDropList())
                {
                    lock (_lockObj)
                    {
                        _lastCopiedContent = "[FileDrop]";
                    }
                }
            }
            catch
            {
                lock (_lockObj)
                {
                    _lastCopiedContent = "[Error Reading Clipboard]";
                }
            }
        }
    }
}
