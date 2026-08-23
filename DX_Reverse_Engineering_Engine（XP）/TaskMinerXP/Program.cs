using System;
using System.Threading;
using System.Windows.Forms;

namespace TaskMinerXP
{
    static class Program
    {
        private static Mutex _mutex;

        [STAThread]
        static void Main()
        {
            // 二重起動防止
            bool createdNew;
            _mutex = new Mutex(true, "TaskMinerXP_SingleInstance_Mutex", out createdNew);
            if (!createdNew)
            {
                // すでに起動中の場合は終了
                return;
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            // メインとなる操作画面を起動
            Application.Run(new MainForm());

            if (_mutex != null)
            {
                _mutex.ReleaseMutex();
            }
        }
    }
}
