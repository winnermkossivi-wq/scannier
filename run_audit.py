import os
os.environ['HEROZION_SKIP_BANNER'] = 'true'
import subprocess
result = subprocess.run(['herozion', 'scan', '.'], capture_output=True, text=True, cwd=r'C:\Users\Lenovo\Desktop\zip\scannier')
print("STDOUT:", result.stdout[:2000] if result.stdout else "empty")
print("STDERR:", result.stderr[:2000] if result.stderr else "empty")
print("Return code:", result.returncode)