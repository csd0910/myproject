using System;

namespace TaskMinerXP.Models
{
    public class LogEvent
    {
        public string Timestamp { get; set; }
        public string ActiveApp { get; set; }
        public string EventType { get; set; }
        public string TargetName { get; set; }
        public string Metadata { get; set; }
    }
}
