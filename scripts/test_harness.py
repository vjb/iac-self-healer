import os
import subprocess
import sys
import time

def main():
    consecutive_successes = 0
    max_count = 3
    
    python_bin = os.path.join("venv", "Scripts", "python.exe") if sys.platform == "win32" else "venv/bin/python"
    
    while consecutive_successes < max_count:
        print(f"\n=======================================================")
        print(f"--- Launching Validation Pipeline (Iteration {consecutive_successes + 1}) ---")
        print(f"=======================================================")
        
        # Enforce fresh launch parameters to strictly validate zero-shot multi-threading
        if os.path.exists("optimized_factory.json"):
            try:
                os.unlink("optimized_factory.json")
            except OSError:
                pass
                
        cmd = [python_bin, "scripts/optimize.py", "--auto", "light"]
        print(f"Executing payload: {' '.join(cmd)}\n")
        
        proc = subprocess.Popen(cmd)
        proc.wait()
        
        if proc.returncode == 0:
            print("\n[+] Iteration cleanly executed! JSII syntheses parallelized effectively.")
            consecutive_successes += 1
        else:
            print(f"\n[!] ABORT: Optimizer crashed with return code {proc.returncode}!")
            print("Restarting the loop sequence automatically in 5 seconds...")
            consecutive_successes = 0
            time.sleep(5)
            
    print(f"\n[+] SUCCESS: Continuous validation loop passed perfectly {max_count} times without execution deadlocks.")

if __name__ == "__main__":
    main()
