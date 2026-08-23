using System;
using System.Runtime.InteropServices;
using System.Threading;

namespace TaskMinerXP
{
    public class ExcelComHook
    {
        private Thread _excelThread;
        private bool _isRunning = false;
        private AsyncCsvWriter _csvWriter;

        public ExcelComHook(AsyncCsvWriter csvWriter)
        {
            _csvWriter = csvWriter;
        }

        public void Start()
        {
            _isRunning = true;
            _excelThread = new Thread(ExcelMonitorLoop);
            _excelThread.IsBackground = true;
            _excelThread.Start();
        }

        public void Stop()
        {
            _isRunning = false;
        }

        private void ExcelMonitorLoop()
        {
            string lastAddress = "";
            string lastValue = "";
            object excelApp = null;

            while (_isRunning)
            {
                try
                {
                    if (excelApp == null)
                    {
                        try
                        {
                            excelApp = Marshal.GetActiveObject("Excel.Application");
                            Console.WriteLine("Excel COM Attached.");
                        }
                        catch
                        {
                            Thread.Sleep(2000); // 起動していなければ待機
                            continue;
                        }
                    }

                    if (excelApp != null)
                    {
                        object selection = null;
                        try 
                        {
                            selection = excelApp.GetType().InvokeMember("Selection", System.Reflection.BindingFlags.GetProperty, null, excelApp, null);
                        }
                        catch 
                        {
                            // セル編集中などはアクセスがロックされるため一時的に無視
                        }

                        if (selection != null)
                        {
                            string currentAddress = "";
                            string currentValue = "";
                            string sheetName = "";

                            try { currentAddress = (string)selection.GetType().InvokeMember("Address", System.Reflection.BindingFlags.GetProperty, null, selection, null); } catch { }
                            
                            // 値はActiveCellから取得（範囲選択時は全体の値が配列で返ってきてしまうため）
                            object activeCell = null;
                            try { activeCell = excelApp.GetType().InvokeMember("ActiveCell", System.Reflection.BindingFlags.GetProperty, null, excelApp, null); } catch { }
                            if (activeCell != null)
                            {
                                try { currentValue = Convert.ToString(activeCell.GetType().InvokeMember("Value", System.Reflection.BindingFlags.GetProperty, null, activeCell, null)); } catch { }
                            }

                            try 
                            { 
                                object activeSheet = excelApp.GetType().InvokeMember("ActiveSheet", System.Reflection.BindingFlags.GetProperty, null, excelApp, null);
                                sheetName = (string)activeSheet.GetType().InvokeMember("Name", System.Reflection.BindingFlags.GetProperty, null, activeSheet, null); 
                            } 
                            catch { }

                            // セルの位置（範囲）や値が変化したら記録
                            if (!string.IsNullOrEmpty(currentAddress) && (currentAddress != lastAddress || currentValue != lastValue))
                            {
                                // 初回はスキップ（アタッチした瞬間の記録を防ぐため）
                                if (lastAddress != "")
                                {
                                    string meta = string.Format("Sheet:{0}, Range:{1}, Value:{2}", sheetName, currentAddress, currentValue);
                                    _csvWriter.EnqueueLog("Excel", "SheetChange", "ActiveWorkbook", meta);
                                }
                                
                                lastAddress = currentAddress;
                                lastValue = currentValue;
                            }
                        }
                        Thread.Sleep(500);
                    }
                }
                catch (Exception)
                {
                    // Excelプロセスが終了した等の場合、次回再アタッチを試みる
                    excelApp = null;
                    Thread.Sleep(2000);
                }
            }
        }
    }
}
