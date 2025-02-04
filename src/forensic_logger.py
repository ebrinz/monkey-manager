import json
import os
import hashlib
import time
import psutil
import logging
from datetime import datetime
from typing import Dict, Any

class ForensicLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger('forensic_logger')
        self.logger.setLevel(logging.DEBUG)
        
        # Create timestamp for this session
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create file handler
        log_file = os.path.join(log_dir, f'forensic_{self.session_id}.log')
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def compute_file_hash(self, filepath: str) -> Dict[str, str]:
        """Compute multiple hashes of a file."""
        sha256_hash = hashlib.sha256()
        md5_hash = hashlib.md5()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
                md5_hash.update(chunk)
                
        return {
            'sha256': sha256_hash.hexdigest(),
            'md5': md5_hash.hexdigest()
        }

    def log_file_event(self, event_type: str, filepath: str, details: Dict[str, Any] = None):
        """Log file-related events with hashes and metadata."""
        try:
            stat = os.stat(filepath)
            hashes = self.compute_file_hash(filepath)
            
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'filepath': filepath,
                'file_size': stat.st_size,
                'file_permissions': oct(stat.st_mode),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'hashes': hashes,
                'details': details or {}
            }
            
            self.logger.info(json.dumps(event_data))
            
        except Exception as e:
            self.logger.error(f"Error logging file event: {str(e)}")

    def log_system_state(self):
        """Log system state information."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            state_data = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'open_files': len(psutil.Process().open_files()),
                'threads': len(psutil.Process().threads())
            }
            
            self.logger.info(f"System State: {json.dumps(state_data)}")
            
        except Exception as e:
            self.logger.error(f"Error logging system state: {str(e)}")

    def log_process_execution(self, command: str, pid: int, return_code: int):
        """Log process execution details."""
        try:
            process = psutil.Process(pid)
            
            process_data = {
                'timestamp': datetime.now().isoformat(),
                'command': command,
                'pid': pid,
                'return_code': return_code,
                'cpu_time': sum(process.cpu_times()),
                'memory_info': process.memory_info()._asdict(),
                'num_threads': process.num_threads(),
                'status': process.status()
            }
            
            self.logger.info(f"Process Execution: {json.dumps(process_data)}")
            
        except Exception as e:
            self.logger.error(f"Error logging process execution: {str(e)}")

    def log_anomaly(self, anomaly_type: str, details: Dict[str, Any]):
        """Log suspicious or anomalous activity."""
        try:
            anomaly_data = {
                'timestamp': datetime.now().isoformat(),
                'anomaly_type': anomaly_type,
                'details': details,
                'system_state': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'open_files': len(psutil.Process().open_files())
                }
            }
            
            self.logger.warning(f"Anomaly Detected: {json.dumps(anomaly_data)}")
            
        except Exception as e:
            self.logger.error(f"Error logging anomaly: {str(e)}")