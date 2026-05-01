import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import time
import threading
import traceback

def log(message):
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def get_local_versions():
    """Najde všechny .jar soubory ve složce 'versions'."""
    v_dir = os.path.join(os.path.dirname(__file__), "versions")
    if not os.path.exists(v_dir):
        os.makedirs(v_dir)
        return []
    files = [f.replace(".jar", "") for f in os.listdir(v_dir) if f.endswith(".jar")]
    return sorted(files, reverse=True)

def create_server():
    version = version_var.get()
    target_folder = folder_path.get()
    port = port_entry.get()
    min_ram = min_ram_entry.get()
    max_ram = max_ram_entry.get()
    
    if not version or not target_folder:
        messagebox.showerror("Error", "Choose version and folder!")
        return

    def process():
        try:
            log(f"--- START: {version} ({min_ram}G - {max_ram}G RAM) ---")
            
            # 1. Příprava souborů
            source_jar = os.path.join(os.path.dirname(__file__), "versions", f"{version}.jar")
            target_jar = os.path.join(target_folder, "paper.jar")
            os.makedirs(target_folder, exist_ok=True)
            
            status_label.config(text="Copying JAR...", fg="blue")
            shutil.copy2(source_jar, target_jar)

            # 2. První start (EULA)
            status_label.config(text="Generating EULA...", fg="orange")
            subprocess.run(['java', '-jar', 'paper.jar', '--nogui'], cwd=target_folder, shell=True, timeout=30)
            
            with open(os.path.join(target_folder, "eula.txt"), "w") as f:
                f.write("eula=true")

            # 3. Druhý start (Properties)
            status_label.config(text="Setting port...", fg="orange")
            proc = subprocess.Popen(['java', '-jar', 'paper.jar', '--nogui'], 
                                   cwd=target_folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
                                   text=True, shell=True)
            
            while True:
                line = proc.stdout.readline()
                if "Done" in line or "For help" in line:
                    proc.stdin.write("stop\n")
                    proc.stdin.flush()
                    break
            proc.wait()

            # Zápis portu
            props_path = os.path.join(target_folder, "server.properties")
            if os.path.exists(props_path):
                with open(props_path, "r") as f:
                    lines = f.readlines()
                with open(props_path, "w") as f:
                    for l in lines:
                        if l.startswith("server-port="):
                            f.write(f"server-port={port}\n")
                        else:
                            f.write(l)

            # 4. Generování Start.bat s Aikarovými vlajkami
            if bat_var.get():
                aikar_flags = (
                    f"@echo off\n"
                    f"java -Xms{min_ram}G -Xmx{max_ram}G -XX:+UseG1GC -XX:+ParallelRefProcEnabled "
                    f"-XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC "
                    f"-XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 "
                    f"-XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 "
                    f"-XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 "
                    f"-XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 "
                    f"-XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 "
                    f"-Dusing.aikars.flags=https://emc.gs -Daikars.new.flags=true "
                    f"-jar paper.jar --nogui\n"
                    f"pause"
                )
                with open(os.path.join(target_folder, "start.bat"), "w") as f:
                    f.write(aikar_flags)
                log("Optimized start.bat vytvořen.")

            status_label.config(text="DONE!", fg="green")
            subprocess.Popen(f'explorer "{os.path.realpath(target_folder)}"')
            messagebox.showinfo("Succes", f"Server {version} vytvořen!\nRAM: {min_ram}G - {max_ram}G")

        except Exception:
            traceback.print_exc()
            messagebox.showerror("Error", "Check CMD.")

    threading.Thread(target=process, daemon=True).start()

# --- GUI ---
root = tk.Tk()
root.title("Paper Server Maker (Local & Optimized)")
root.geometry("450x550")

# Složka
tk.Label(root, text="Server Folder:", font=("Arial", 9, "bold")).pack(pady=5)
folder_path = tk.StringVar()
tk.Entry(root, textvariable=folder_path, width=40).pack()
tk.Button(root, text="Vybrat složku", command=lambda: folder_path.set(filedialog.askdirectory())).pack(pady=5)

# Verze
tk.Label(root, text="Version (From folder /versions/):", font=("Arial", 9, "bold")).pack(pady=5)
version_var = tk.StringVar()
local_v = get_local_versions()
v_drop = ttk.Combobox(root, textvariable=version_var, values=local_v, state="readonly")
v_drop.pack()
if local_v: v_drop.current(0)

# Port
tk.Label(root, text="Port:", font=("Arial", 9, "bold")).pack(pady=5)
port_entry = tk.Entry(root, justify="center", width=10)
port_entry.insert(0, "25565")
port_entry.pack()

# RAM Nastavení
ram_frame = tk.Frame(root)
ram_frame.pack(pady=10)

tk.Label(ram_frame, text="Min RAM (GB):").grid(row=0, column=0, padx=5)
min_ram_entry = tk.Entry(ram_frame, width=5, justify="center")
min_ram_entry.insert(0, "2")
min_ram_entry.grid(row=0, column=1, padx=5)

tk.Label(ram_frame, text="Max RAM (GB):").grid(row=0, column=2, padx=5)
max_ram_entry = tk.Entry(ram_frame, width=5, justify="center")
max_ram_entry.insert(0, "4")
max_ram_entry.grid(row=0, column=3, padx=5)

# Start.bat Checkbox
bat_var = tk.BooleanVar(value=True)
tk.Checkbutton(root, text="Create Optimized start.bat", variable=bat_var).pack(pady=5)

# Start Button
tk.Button(root, text="🚀 CREATE SERVER", bg="#27ae60", fg="white", font=("Arial", 12, "bold"), 
          command=create_server, height=2, width=25).pack(pady=20)

status_label = tk.Label(root, text="Ready", font=("Arial", 9, "italic"))
status_label.pack()

root.mainloop()
