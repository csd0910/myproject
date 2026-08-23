using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using TaskMinerXP.Models;

namespace TaskMinerXP
{
    public class AsyncCsvWriter
    {
        private Queue<LogEvent> _logQueue = new Queue<LogEvent>();
        private object _lockObj = new object();
        private Thread _writerThread;
        private bool _isRunning = false;

        private string _logDir;

        public AsyncCsvWriter(string logDir)
        {
            _logDir = logDir;
        }

        public void Start()
        {
            _isRunning = true;
            _writerThread = new Thread(WriterLoop);
            _writerThread.IsBackground = true;
            _writerThread.Start();
        }

        public void Stop()
        {
            _isRunning = false;
            if (_writerThread != null && _writerThread.IsAlive)
            {
                _writerThread.Join(2000);
            }
        }

        public void EnqueueLog(string appName, string eventType, string target, string metadata)
        {
            var log = new LogEvent
            {
                Timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                ActiveApp = appName,
                EventType = eventType,
                TargetName = target,
                Metadata = metadata
            };

            lock (_lockObj)
            {
                _logQueue.Enqueue(log);
                Monitor.Pulse(_lockObj);
            }
        }

        private void WriterLoop()
        {
            while (_isRunning || _logQueue.Count > 0)
            {
                LogEvent log = null;
                lock (_lockObj)
                {
                    if (_logQueue.Count == 0)
                    {
                        if (!_isRunning) break;
                        Monitor.Wait(_lockObj, 1000);
                        continue;
                    }
                    log = _logQueue.Dequeue();
                }

                if (log != null)
                {
                    WriteToFile(log);
                }
            }
        }

        private void WriteToFile(LogEvent log)
        {
            try
            {
                string dateStr = DateTime.Now.ToString("yyyyMMdd");
                string dir = _logDir;
                if (!Directory.Exists(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                string csvPath = Path.Combine(dir, string.Format("system_log_{0}.csv", dateStr));
                bool fileExists = File.Exists(csvPath);

                using (StreamWriter sw = new StreamWriter(csvPath, true, new UTF8Encoding(true)))
                {
                    if (!fileExists)
                    {
                        sw.WriteLine("Timestamp,ActiveApp,EventType,TargetName,Metadata");
                    }
                    
                    string line = string.Format("\"{0}\",\"{1}\",\"{2}\",\"{3}\",\"{4}\"",
                        EscapeCsv(log.Timestamp),
                        EscapeCsv(log.ActiveApp),
                        EscapeCsv(log.EventType),
                        EscapeCsv(log.TargetName),
                        EscapeCsv(log.Metadata));
                        
                    sw.WriteLine(line);
                }
            }
            catch (Exception)
            {
                // 無視（Python版と同様のフェールセーフ）
            }
        }

        private string EscapeCsv(string field)
        {
            if (string.IsNullOrEmpty(field)) return "";
            return field.Replace("\"", "\"\"");
        }
    }
}
