"""
System Health Checker
---------------------
A simple desktop app that shows your computer's CPU, RAM and disk usage,
lists the busiest programs, and warns you when something is too high.

HOW TO RUN:
    1. Install the one extra library:   pip install psutil
    2. Run this file:                   python system_health_checker.py

(Tkinter, the GUI library, already comes with Python.)
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import psutil


# ----------------------------------------------------------------------
# SETTINGS  (change these numbers to whatever you like!)
# ----------------------------------------------------------------------
CPU_LIMIT = 85        # warn if CPU usage goes above 85%
RAM_LIMIT = 90        # warn if RAM usage goes above 90%
DISK_LIMIT = 90       # warn if disk usage goes above 90%
REFRESH_MS = 2000     # update every 2000 milliseconds (= 2 seconds)
TOP_PROCESSES = 10    # how many programs to show in the table


# ----------------------------------------------------------------------
# THE APP
# ----------------------------------------------------------------------
class HealthCheckerApp:
    def __init__(self, window):
        self.window = window
        self.window.title("System Health Checker")
        self.window.geometry("560x640")

        # Remember how the process table is sorted: "cpu" or "memory"
        self.sort_by = "cpu"

        # Disk to check: "C:\" on Windows, "/" on Mac/Linux
        self.disk_path = Path.home().anchor

        self.setup_styles()
        self.build_screen()
        self.update_stats()   # start the repeating update

    # ------------------------------------------------------------------
    # STEP 1: Make green and red progress bars
    # ------------------------------------------------------------------
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")  # this theme lets us change bar colours
        style.configure("Good.Horizontal.TProgressbar", background="#2ecc71")
        style.configure("Bad.Horizontal.TProgressbar", background="#e74c3c")

    # ------------------------------------------------------------------
    # STEP 2: Build everything you see on the screen
    # ------------------------------------------------------------------
    def build_screen(self):
        # Title
        tk.Label(self.window, text="System Health Checker",
                 font=("Arial", 18, "bold")).pack(pady=10)

        # Warning banner (text changes depending on the situation)
        self.banner = tk.Label(self.window, text="", font=("Arial", 11, "bold"),
                               width=60, height=3, wraplength=500)
        self.banner.pack(padx=10, pady=5)

        # Three rows: CPU, RAM, Disk. Each has a label + bar.
        self.cpu_label, self.cpu_bar = self.make_meter("CPU")
        self.ram_label, self.ram_bar = self.make_meter("RAM")
        self.disk_label, self.disk_bar = self.make_meter("Disk")

        # Process table
        tk.Label(self.window, text="Busiest programs",
                 font=("Arial", 12, "bold")).pack(pady=(15, 2))

        columns = ("name", "cpu", "memory")
        self.table = ttk.Treeview(self.window, columns=columns,
                                  show="headings", height=TOP_PROCESSES)
        self.table.heading("name", text="Program")
        self.table.heading("cpu", text="CPU %")
        self.table.heading("memory", text="Memory %")
        self.table.column("name", width=280)
        self.table.column("cpu", width=100, anchor="center")
        self.table.column("memory", width=100, anchor="center")
        self.table.pack(padx=10, fill="x")

        # Button to switch sorting
        self.sort_button = tk.Button(self.window, text="Sort by Memory",
                                     command=self.toggle_sort)
        self.sort_button.pack(pady=10)

    def make_meter(self, name):
        """Creates one 'label + progress bar' row and returns both."""
        frame = tk.Frame(self.window)
        frame.pack(fill="x", padx=20, pady=6)

        label = tk.Label(frame, text=f"{name}: --%", font=("Arial", 11))
        label.pack(anchor="w")

        bar = ttk.Progressbar(frame, maximum=100, length=500)
        bar.pack(fill="x")
        return label, bar

    # ------------------------------------------------------------------
    # STEP 3: Button action - switch between CPU and Memory sorting
    # ------------------------------------------------------------------
    def toggle_sort(self):
        if self.sort_by == "cpu":
            self.sort_by = "memory"
            self.sort_button.config(text="Sort by CPU")
        else:
            self.sort_by = "cpu"
            self.sort_button.config(text="Sort by Memory")
        self.update_stats()

    # ------------------------------------------------------------------
    # STEP 4: Colour a bar green or red depending on the limit
    # ------------------------------------------------------------------
    def set_meter(self, label, bar, name, value, limit):
        label.config(text=f"{name}: {value:.1f}%   (limit {limit}%)")
        bar["value"] = value
        if value > limit:
            bar.config(style="Bad.Horizontal.TProgressbar")
            return True    # True means "this one is too high"
        bar.config(style="Good.Horizontal.TProgressbar")
        return False

    # ------------------------------------------------------------------
    # STEP 5: Read the real numbers using psutil and update the screen
    # ------------------------------------------------------------------
    def update_stats(self):
        # --- Read the numbers ---
        cpu = psutil.cpu_percent()                      # CPU usage %
        ram = psutil.virtual_memory().percent           # RAM usage %
        disk = psutil.disk_usage(self.disk_path).percent  # Disk usage %

        # --- Show them, and collect warnings ---
        problems = []
        if self.set_meter(self.cpu_label, self.cpu_bar, "CPU", cpu, CPU_LIMIT):
            problems.append("CPU is too high. Close heavy programs.")
        if self.set_meter(self.ram_label, self.ram_bar, "RAM", ram, RAM_LIMIT):
            problems.append("RAM is too high. Close some apps or tabs.")
        if self.set_meter(self.disk_label, self.disk_bar, "Disk", disk, DISK_LIMIT):
            problems.append("Disk is almost full. Delete files you don't need.")

        # --- Update the banner ---
        if problems:
            self.banner.config(text="WARNING\n" + "\n".join(problems),
                               bg="#e74c3c", fg="white")
        else:
            self.banner.config(text="All good! Your computer looks healthy.",
                               bg="#2ecc71", fg="white")

        # --- Update the process table ---
        self.update_process_table()

        # --- Ask Tkinter to run this function again after 2 seconds ---
        self.window.after(REFRESH_MS, self.update_stats)

    def update_process_table(self):
        processes = []
        cpu_cores = psutil.cpu_count() or 1

        # Loop through every running program
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                processes.append((
                    info["name"] or "Unknown",
                    (info["cpu_percent"] or 0) / cpu_cores,
                    info["memory_percent"] or 0,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue  # program closed or is protected - just skip it

        # Sort: column 1 is CPU, column 2 is memory. Biggest first.
        sort_column = 1 if self.sort_by == "cpu" else 2
        processes.sort(key=lambda row: row[sort_column], reverse=True)

        # Clear the old rows, then add the new top rows
        for row in self.table.get_children():
            self.table.delete(row)
        for name, cpu, mem in processes[:TOP_PROCESSES]:
            self.table.insert("", "end", values=(name, f"{cpu:.1f}", f"{mem:.1f}"))


# ----------------------------------------------------------------------
# START THE PROGRAM
# ----------------------------------------------------------------------
if __name__ == "__main__":
    window = tk.Tk()
    app = HealthCheckerApp(window)
    window.mainloop()
