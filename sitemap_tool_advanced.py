# sitemap_tool_advanced.py (modernes GUI-Design mit Stilverbesserungen)

import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import threading
import os
import csv
from collections import Counter

SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap/sitemap.xml",
    "/sitemap/sitemap-index.xml",
    "/sitemap-index.xml"
]

# === Funktion zum Finden der Sitemap ===
def find_sitemap(domain):
    candidates = [domain.rstrip("/") + path for path in SITEMAP_PATHS]
    for url in candidates:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and b"<urlset" in response.content or b"<sitemapindex" in response.content:
                return url
        except Exception:
            continue
    return None

# === Funktion zum Prüfen auf robots.txt ===
def check_robots(domain):
    try:
        robots_url = domain.rstrip("/") + "/robots.txt"
        response = requests.get(robots_url, timeout=10)
        if response.status_code == 200:
            return True, response.text
        return False, ""
    except Exception:
        return False, ""

# === Funktion zum Parsen der Sitemap ===
def get_sitemap_links(sitemap_url, collected=None):
    if collected is None:
        collected = set()
    try:
        response = requests.get(sitemap_url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        if root.tag.endswith("sitemapindex"):
            for sitemap in root.findall("{*}sitemap"):
                loc = sitemap.find("{*}loc").text
                get_sitemap_links(loc, collected)
        elif root.tag.endswith("urlset"):
            for url in root.findall("{*}url"):
                loc = url.find("{*}loc").text
                collected.add(loc)
    except Exception as e:
        print(f"Fehler bei {sitemap_url}: {e}")
    return collected

# === Funktion zum Prüfen, ob Links erreichbar sind ===
def validate_links(links):
    valid_links = []
    for link in links:
        try:
            response = requests.head(link, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                valid_links.append(link)
        except Exception:
            continue
    return valid_links

# === Funktion zum Erzeugen einer Keyword-Statistik ===
def keyword_statistics(links):
    words = []
    for link in links:
        parts = link.split("/")
        words.extend([w for w in parts if len(w) > 3])
    return Counter(words).most_common(10)

# === Funktion zum Speichern als CSV ===
def save_links_to_csv(links, filename):
    with open(filename, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["URL"])
        for link in links:
            writer.writerow([link])

# === GUI Hauptfunktion ===
def extract_links():
    def thread_task():
        domain = domain_entry.get().strip()
        filters_input = filter_entry.get().strip()
        filters = [f.strip() for f in filters_input.split(",") if f.strip()]
        use_filter = bool(filters)
        only_valid = validate_checkbox_var.get()

        if not domain:
            messagebox.showwarning("Eingabe fehlt", "Bitte gib eine Website-Adresse ein.")
            return
        if not domain.startswith("http"):
            domain = "https://" + domain

        parsed = urlparse(domain)
        filename_base = parsed.netloc.replace("www.", "")
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=filename_base,
            filetypes=[("CSV-Dateien", "*.csv"), ("Textdateien", "*.txt")]
        )
        if not save_path:
            return

        status_label.config(text="🔎 Suche nach Sitemap...")
        progress_bar.start()

        robots_ok, robots_txt = check_robots(domain)
        if not robots_ok:
            status_label.config(text="⚠️ Keine robots.txt gefunden oder Zugriff verweigert.")

        sitemap_url = find_sitemap(domain)
        if not sitemap_url:
            status_label.config(text="❌ Keine Sitemap gefunden.")
            progress_bar.stop()
            return

        status_label.config(text="📥 Sitemap wird geladen...")
        all_links = get_sitemap_links(sitemap_url)

        if not all_links:
            status_label.config(text="❌ Keine Links gefunden.")
            progress_bar.stop()
            return

        all_links = list(set(all_links))

        if use_filter:
            filtered_links = [link for link in all_links if any(keyword in link for keyword in filters)]
        else:
            filtered_links = list(all_links)

        if not filtered_links:
            status_label.config(text="⚠️ Keine passenden Links gefunden.")
            progress_bar.stop()
            return

        if only_valid:
            status_label.config(text="🔍 Prüfe Link-Gültigkeit...")
            filtered_links = validate_links(filtered_links)

        save_links_to_csv(filtered_links, save_path)

        stats = keyword_statistics(filtered_links)
        stats_text = "\n".join([f"{word}: {count}" for word, count in stats])

        status_label.config(text=f"✅ {len(filtered_links)} Link(s) gespeichert in: {os.path.basename(save_path)}")
        messagebox.showinfo("Zusammenfassung", f"Gespeicherte Links: {len(filtered_links)}\nTop Keywords:\n{stats_text}")
        progress_bar.stop()

    threading.Thread(target=thread_task).start()

# === GUI Setup ===
root = tk.Tk()
root.title("Sitemap Link Extractor Pro")
root.configure(bg="#f4f4f4")
root.geometry("620x420")
root.resizable(False, False)

style = ttk.Style()
style.configure("TButton", font=("Segoe UI", 10))
style.configure("TLabel", background="#f4f4f4", font=("Segoe UI", 10))

frame = tk.Frame(root, bg="#f4f4f4")
frame.pack(pady=10)

tk.Label(frame, text="🌐 Webadresse (z. B. example.com):", bg="#f4f4f4").pack(pady=5)
domain_entry = tk.Entry(frame, width=70, font=("Segoe UI", 10))
domain_entry.insert(0, "https://online.mason.wm.edu")
domain_entry.pack(pady=2)

tk.Label(frame, text="🔍 Filter (z. B. /blog/, /post/ – optional):", bg="#f4f4f4").pack(pady=5)
filter_entry = tk.Entry(frame, width=70, font=("Segoe UI", 10))
filter_entry.insert(0, "/blog/, /post/")
filter_entry.pack(pady=2)

validate_checkbox_var = tk.BooleanVar(value=True)
validate_checkbox = tk.Checkbutton(frame, text="Nur gültige Links speichern (Status 200)", variable=validate_checkbox_var, bg="#f4f4f4")
validate_checkbox.pack(pady=5)

start_button = ttk.Button(frame, text="Start", command=extract_links)
start_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, mode='indeterminate')
progress_bar.pack(pady=5, fill='x', padx=40)

status_label = ttk.Label(root, text="", foreground="blue")
status_label.pack(pady=5)

footer_label = tk.Label(root, text="Erstellt von noel.marketing", fg="gray", cursor="hand2", bg="#f4f4f4", font=("Segoe UI", 9, "italic"))
footer_label.pack(side="bottom", pady=10)
footer_label.bind("<Button-1>", lambda e: os.system("start https://www.noel.marketing"))

root.mainloop()


