#!/usr/bin/env python3

"""
Safe Test Runner - job-finder-worker

Prevents test explosions through process locking and resource control.
This is the ONLY way to run tests in this repository.
"""

import subprocess
import os
import sys
import time
import json
import signal
import psutil

# Configuration
LOCK_FILE = '.test-lock'
MAX_MEMORY_MB = 2048  # 2GB max memory
MAX_EXECUTION_TIME = 600  # 10 minutes

class SafeTestRunner:
    def __init__(self):
        self.start_time = time.time()
        self.lock_acquired = False

    def acquire_lock(self):
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, 'r') as f:
                    lock_data = json.load(f)
                lock_age = time.time() - lock_data['start_time']
                
                # If lock is older than 15 minutes, consider it stale
                if lock_age > 900:  # 15 minutes
                    print('⚠️  Removing stale lock file')
                    os.unlink(LOCK_FILE)
                else:
                    print('❌ Another test process is already running')
                    print('   PID: ' + str(lock_data['pid']))
                    print('   Started: ' + str(lock_data['start_time']))
                    sys.exit(1)
            except (json.JSONDecodeError, KeyError):
                # Corrupted lock file, remove it
                os.unlink(LOCK_FILE)

        # Create lock file
        lock_data = {
            'pid': os.getpid(),
            'start_time': time.time(),
            'repository': 'job-finder-worker',
            'test_suite': 'unit'
        }
        
        with open(LOCK_FILE, 'w') as f:
            json.dump(lock_data, f)
        
        self.lock_acquired = True
        print('🔒 Test execution lock acquired')

    def release_lock(self):
        if self.lock_acquired and os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)
            print('🔓 Test execution lock released')

    def monitor_resources(self):
        """Monitor system resources during test execution"""
        while True:
            try:
                # Check memory usage
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if memory_mb > MAX_MEMORY_MB:
                    print('\n⚠️  CRITICAL: Memory usage exceeded ' + str(MAX_MEMORY_MB) + 'MB')
                    print('Current usage: ' + str(round(memory_mb, 1)) + 'MB')
                    self.terminate_tests()
                    sys.exit(1)

                # Check execution time
                execution_time = time.time() - self.start_time
                if execution_time > MAX_EXECUTION_TIME:
                    print('\n⚠️  CRITICAL: Test execution exceeded ' + str(MAX_EXECUTION_TIME) + 's')
                    self.terminate_tests()
                    sys.exit(1)

                # Log status every 30 seconds
                if execution_time % 30 < 1:
                    print('[Monitor] Memory: ' + str(round(memory_mb, 1)) + 'MB | Time: ' + str(round(execution_time, 1)) + 's')

                time.sleep(1)
            except KeyboardInterrupt:
                break

    def terminate_tests(self):
        """Terminate all test processes"""
        print('\n🛑 Terminating test processes...')
        try:
            # Kill pytest processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'pytest' in ' '.join(proc.info['cmdline'] or []):
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print('Error terminating processes: ' + str(e))

    def run_tests(self):
        """Run tests with safety controls"""
        print('\n🧪 Running tests...')
        
        try:
            # Run pytest with timeout
            result = subprocess.run(
                ['python', '-m', 'pytest'],
                timeout=MAX_EXECUTION_TIME,
                capture_output=False
            )
            
            if result.returncode == 0:
                print('✅ Tests completed successfully')
                return True
            else:
                print('❌ Tests failed (exit code: ' + str(result.returncode) + ')')
                return False
                
        except subprocess.TimeoutExpired:
            print('❌ Tests timed out after ' + str(MAX_EXECUTION_TIME) + 's')
            return False
        except Exception as e:
            print('❌ Error running tests: ' + str(e))
            return False

    def run(self):
        """Main execution"""
        print('\n🛡️  Safe Test Runner - job-finder-worker\n')
        
        try:
            # Acquire lock
            self.acquire_lock()
            
            # Start monitoring in background
            import threading
            monitor_thread = threading.Thread(target=self.monitor_resources)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Run tests
            success = self.run_tests()
            
            # Cleanup
            self.release_lock()
            
            # Exit with appropriate code
            sys.exit(0 if success else 1)
            
        except KeyboardInterrupt:
            print('\n\nReceived SIGINT, cleaning up...')
            self.terminate_tests()
            self.release_lock()
            sys.exit(130)
        except Exception as e:
            print('Fatal error: ' + str(e))
            self.release_lock()
            sys.exit(1)

if __name__ == '__main__':
    runner = SafeTestRunner()
    runner.run()
