#!/usr/bin/env python3
"""
GUI downloader skripsi UNAIR Digital Collection.

Fitur:
  - Tempel link skripsi (URL index.html atau URL apa pun yang memuat HASH)
  - Deteksi judul otomatis dari index.html -> jadi nama file (bisa diedit)
  - Pilih folder tujuan
  - Download semua halaman -> gabung jadi PDF
  - Progress bar + log, tombol batal

Jalankan:  python gui_scrapper.py
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import scraper_core as core


class App:
    def __init__(self, root):
        self.root = root
        root.title("UNAIR Skripsi Downloader  —  by mirza")
        root.geometry("720x560")
        root.minsize(640, 500)

        self.stop_flag = False
        self.worker = None

        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(root)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # Link
        ttk.Label(frm, text="Link skripsi:").grid(row=0, column=0, sticky="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(frm, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Deteksi judul", command=self.on_detect).grid(
            row=0, column=2, **pad)

        # Nama file
        ttk.Label(frm, text="Nama file:").grid(row=1, column=0, sticky="w", **pad)
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Label(frm, text=".pdf").grid(row=1, column=2, sticky="w", **pad)

        # Folder tujuan
        ttk.Label(frm, text="Folder tujuan:").grid(row=2, column=0, sticky="w", **pad)
        self.dir_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(frm, textvariable=self.dir_var).grid(row=2, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Pilih...", command=self.on_pick_dir).grid(
            row=2, column=2, **pad)

        # Opsi
        opt = ttk.Frame(frm)
        opt.grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        self.save_jpg = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="Simpan JPG mentah juga",
                        variable=self.save_jpg).pack(side="left", padx=(0, 16))

        # Tombol aksi
        act = ttk.Frame(frm)
        act.grid(row=4, column=0, columnspan=3, **pad)
        self.btn_start = ttk.Button(act, text="Download PDF", command=self.on_start)
        self.btn_start.pack(side="left", padx=6)
        self.btn_stop = ttk.Button(act, text="Batal", command=self.on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)

        # Progress + status
        self.pbar = ttk.Progressbar(frm, mode="determinate")
        self.pbar.grid(row=5, column=0, columnspan=3, sticky="ew", **pad)
        self.status_var = tk.StringVar(value="Siap.")
        ttk.Label(frm, textvariable=self.status_var).grid(
            row=6, column=0, columnspan=3, sticky="w", **pad)

        # Log
        logfrm = ttk.Frame(frm)
        logfrm.grid(row=7, column=0, columnspan=3, sticky="nsew", **pad)
        frm.rowconfigure(7, weight=1)
        logfrm.rowconfigure(0, weight=1)
        logfrm.columnconfigure(0, weight=1)
        self.log = tk.Text(logfrm, height=10, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(logfrm, command=self.log.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.log["yscrollcommand"] = sb.set

    # ---------- helper thread-safe ----------
    def ui(self, fn, *a):
        """Jalankan fn di thread UI."""
        self.root.after(0, lambda: fn(*a))

    def logline(self, msg):
        def _append():
            self.log["state"] = "normal"
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log["state"] = "disabled"
        self.ui(_append)

    def set_status(self, msg):
        self.ui(self.status_var.set, msg)

    # ---------- aksi ----------
    def on_pick_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get() or os.getcwd())
        if d:
            self.dir_var.set(d)

    def on_detect(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kosong", "Tempel link skripsi dulu.")
            return
        self.set_status("Mengambil judul...")

        def work():
            title = core.fetch_title(url)
            if title:
                self.ui(self.name_var.set, core.sanitize_filename(title))
                self.set_status("Judul terdeteksi.")
                self.logline(f"[judul] {title}")
            else:
                h = core.extract_hash(url)
                self.ui(self.name_var.set, f"skripsi_{h[:8]}")
                self.set_status("Judul tidak ada di metadata; pakai nama default (bisa diedit).")

        threading.Thread(target=work, daemon=True).start()

    def on_start(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Kosong", "Tempel link skripsi dulu.")
            return
        outdir = self.dir_var.get().strip() or os.getcwd()
        if not os.path.isdir(outdir):
            messagebox.showerror("Folder", "Folder tujuan tidak valid.")
            return

        name = self.name_var.get().strip()
        if not name:
            # Belum deteksi judul -> ambil otomatis.
            t = core.fetch_title(url)
            name = core.sanitize_filename(t) if t else f"skripsi_{core.extract_hash(url)[:8]}"
            self.name_var.set(name)
        name = core.sanitize_filename(name)
        out_pdf = os.path.join(outdir, name + ".pdf")

        if os.path.exists(out_pdf) and not messagebox.askyesno(
                "Timpa?", f"{name}.pdf sudah ada. Timpa?"):
            return

        self.stop_flag = False
        self.btn_start["state"] = "disabled"
        self.btn_stop["state"] = "normal"
        self.pbar["mode"] = "indeterminate"
        self.pbar.start(12)

        self.worker = threading.Thread(
            target=self.run_download, args=(url, out_pdf, outdir), daemon=True)
        self.worker.start()

    def on_stop(self):
        self.stop_flag = True
        self.set_status("Membatalkan...")

    def run_download(self, url, out_pdf, outdir):
        count = {"n": 0}

        def on_page(page, kb):
            count["n"] += 1
            self.logline(f"[+] Halaman {page}: {kb} KB")
            self.set_status(f"Terunduh {count['n']} halaman...")

        try:
            images = core.scrape(
                url,
                on_page=on_page,
                on_status=self.set_status,
                should_stop=lambda: self.stop_flag,
            )

            if self.save_jpg.get() and images:
                jpgdir = os.path.join(outdir, os.path.splitext(os.path.basename(out_pdf))[0] + "_jpg")
                os.makedirs(jpgdir, exist_ok=True)
                for i, b in enumerate(images, 1):
                    with open(os.path.join(jpgdir, f"{i:04d}.jpg"), "wb") as f:
                        f.write(b)
                self.logline(f"[i] JPG mentah -> {jpgdir}")

            if not images:
                self.set_status("Gagal: tidak ada halaman terunduh. Cek link.")
                self.logline("[!] 0 halaman. Pastikan link benar (memuat HASH koleksi).")
                return

            self.set_status(f"Menggabung {len(images)} halaman jadi PDF...")
            core.images_to_pdf(images, out_pdf)
            self.set_status(f"Selesai: {out_pdf}")
            self.logline(f"[OK] PDF tersimpan: {out_pdf} ({len(images)} halaman)")
            self.ui(messagebox.showinfo, "Selesai",
                    f"PDF tersimpan:\n{out_pdf}\n{len(images)} halaman")
        except Exception as e:
            self.set_status(f"Error: {e}")
            self.logline(f"[!] Error: {e}")
            self.ui(messagebox.showerror, "Error", str(e))
        finally:
            def reset():
                self.pbar.stop()
                self.pbar["mode"] = "determinate"
                self.pbar["value"] = 0
                self.btn_start["state"] = "normal"
                self.btn_stop["state"] = "disabled"
            self.ui(reset)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
