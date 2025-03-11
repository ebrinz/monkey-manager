#!/usr/bin/env python3
import json
import sys
import os
import pandas as pd
from typing import List, Dict
from collections import defaultdict
import matplotlib.pyplot as plt
from datetime import datetime

class ForensicAnalyzer:
    def __init__(self, log_directory: str):
        self.log_directory = log_directory
        self.events = []
        self.anomalies = []
        self.system_states = []
        self.process_executions = []

    def load_logs(self):
        """Load and parse all forensic logs in the directory."""
        for filename in os.listdir(self.log_directory):
            if filename.startswith('forensic_') and filename.endswith('.log'):
                filepath = os.path.join(self.log_directory, filename)
                with open(filepath, 'r') as f:
                    for line in f:
                        try:
                            parts = line.split(' - ', 2)
                            if len(parts) < 3:
                                continue
                            
                            timestamp, level, message = parts
                            
                            if 'System State' in message:
                                self.system_states.append(json.loads(message.replace('System State: ', '')))
                            elif 'Anomaly Detected' in message:
                                self.anomalies.append(json.loads(message.replace('Anomaly Detected: ', '')))
                            elif 'Process Execution' in message:
                                self.process_executions.append(json.loads(message.replace('Process Execution: ', '')))
                            else:
                                self.events.append(json.loads(message))
                                
                        except Exception as e:
                            print(f"Error parsing log line: {e}")

    def analyze_file_operations(self) -> Dict:
        """Analyze file operations and detect patterns."""
        file_stats = defaultdict(int)
        hash_occurrences = defaultdict(list)
        suspicious_operations = []

        for event in self.events:
            if 'event_type' in event:
                file_stats[event['event_type']] += 1
                
                # Track hash occurrences
                if 'hashes' in event:
                    hash_occurrences[event['hashes']['sha256']].append(event['filepath'])
                
                # Look for suspicious patterns
                if event['event_type'] == 'write' and event.get('file_size', 0) == 0:
                    suspicious_operations.append({
                        'type': 'zero_byte_write',
                        'filepath': event['filepath'],
                        'timestamp': event['timestamp']
                    })

        return {
            'operation_counts': dict(file_stats),
            'duplicate_files': {k: v for k, v in hash_occurrences.items() if len(v) > 1},
            'suspicious_operations': suspicious_operations
        }

    def analyze_system_behavior(self) -> Dict:
        """Analyze system behavior patterns."""
        if not self.system_states:
            return {}

        df = pd.DataFrame(self.system_states)
        
        return {
            'cpu_usage': {
                'mean': df['cpu_percent'].mean(),
                'max': df['cpu_percent'].max(),
                'std': df['cpu_percent'].std()
            },
            'memory_usage': {
                'mean': df['memory_percent'].mean(),
                'max': df['memory_percent'].max(),
                'std': df['memory_percent'].std()
            },
            'disk_usage': {
                'mean': df['disk_percent'].mean(),
                'max': df['disk_percent'].max(),
                'std': df['disk_percent'].std()
            }
        }

    def generate_timeline(self) -> List[Dict]:
        """Generate a timeline of significant events."""
        timeline = []
        
        # Add file events
        for event in self.events:
            timeline.append({
                'timestamp': event['timestamp'],
                'type': 'file_operation',
                'details': event
            })
            
        # Add anomalies
        for anomaly in self.anomalies:
            timeline.append({
                'timestamp': anomaly['timestamp'],
                'type': 'anomaly',
                'details': anomaly
            })
            
        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])
        return timeline

    def plot_system_metrics(self, output_dir: str):
        """Generate plots of system metrics over time."""
        if not self.system_states:
            return

        # Create a reports subdirectory for non-JSON output files
        reports_dir = os.path.join(output_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)

        df = pd.DataFrame(self.system_states)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)

        # Plot CPU usage
        plt.figure(figsize=(12, 6))
        df['cpu_percent'].plot()
        plt.title('CPU Usage Over Time')
        plt.ylabel('CPU %')
        plt.savefig(os.path.join(reports_dir, 'cpu_usage.png'))
        plt.close()

        # Plot Memory usage
        plt.figure(figsize=(12, 6))
        df['memory_percent'].plot()
        plt.title('Memory Usage Over Time')
        plt.ylabel('Memory %')
        plt.savefig(os.path.join(reports_dir, 'memory_usage.png'))
        plt.close()

    def generate_report(self, output_dir: str) -> str:
        """Generate a comprehensive analysis report."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a reports subdirectory for non-JSON output files
        reports_dir = os.path.join(output_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        file_analysis = self.analyze_file_operations()
        system_analysis = self.analyze_system_behavior()
        timeline = self.generate_timeline()
        
        # Create JSON report for outputs directory
        report_json = {
            "generated": datetime.now().isoformat(),
            "file_operations": file_analysis,
            "system_behavior": system_analysis,
            "timeline": timeline[-10:]  # Last 10 events
        }
        
        json_report_path = os.path.join(output_dir, 'forensic_report.json')
        with open(json_report_path, 'w') as f:
            json.dump(report_json, f, indent=2)
        
        # Create markdown report for reports subdirectory
        report = []
        report.append("# Forensic Analysis Report")
        report.append(f"Generated: {datetime.now().isoformat()}\n")
        
        report.append("## File Operations Summary")
        report.append("```")
        report.append(json.dumps(file_analysis['operation_counts'], indent=2))
        report.append("```\n")
        
        if file_analysis['suspicious_operations']:
            report.append("### Suspicious Operations Detected")
            for op in file_analysis['suspicious_operations']:
                report.append(f"- {op['type']} on {op['filepath']} at {op['timestamp']}")
            report.append("")
        
        report.append("## System Behavior Analysis")
        report.append("```")
        report.append(json.dumps(system_analysis, indent=2))
        report.append("```\n")
        
        report.append("## Event Timeline")
        for event in timeline[-10:]:  # Show last 10 events
            report.append(f"- {event['timestamp']}: {event['type']}")
        
        # Generate plots in reports subdirectory
        self.plot_system_metrics(output_dir)
        
        report_path = os.path.join(reports_dir, 'forensic_report.md')
        with open(report_path, 'w') as f:
            f.write('\n'.join(report))
            
        return json_report_path

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: forensic_analyzer.py <log_directory> <output_directory>")
        sys.exit(1)
        
    analyzer = ForensicAnalyzer(sys.argv[1])
    analyzer.load_logs()
    report_path = analyzer.generate_report(sys.argv[2])
    print(f"Analysis report generated: {report_path}")