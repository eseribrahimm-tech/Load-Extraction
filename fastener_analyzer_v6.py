"""
Fastener Force Analyzer  v6
MSC Nastran · FX=Tension, FY/FZ=Shear

Mantık:
  Her element için her metriğin MAX verdiği load case → kritik LC
  19 metrik × N element → kritik (EID, LC) çiftleri toplanır
  Aynı element için aynı LC birden fazla metrikten geldiyse → tek satır
  CSV çıktısı: Element ID, Load Case ID, FX, FY, FZ
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv, math
from pathlib import Path

# ─── METRİK TANIMLARI ──────────────────────────────────────────────────────────
METRICS = [
    {"id": "M01", "label": "M01  FZ",                  "fn": lambda fx,fy,fz: fz},
    {"id": "M02", "label": "M02  -FZ",                 "fn": lambda fx,fy,fz: -fz},
    {"id": "M03", "label": "M03  FY",                  "fn": lambda fx,fy,fz: fy},
    {"id": "M04", "label": "M04  -FY",                 "fn": lambda fx,fy,fz: -fy},
    {"id": "M05", "label": "M05  FX",                  "fn": lambda fx,fy,fz: fx},
    {"id": "M06", "label": "M06  -FX",                 "fn": lambda fx,fy,fz: -fx},
    {"id": "M07", "label": "M07  |FX|",                "fn": lambda fx,fy,fz: abs(fx)},
    {"id": "M08", "label": "M08  Vr=√(FY²+FZ²)",      "fn": lambda fx,fy,fz: math.sqrt(fy**2+fz**2)},
    {"id": "M09", "label": "M09  √(FZ²+FY²)",          "fn": lambda fx,fy,fz: math.sqrt(fz**2+fy**2)},
    {"id": "M10", "label": "M10  √(FZ²+FY²)+|FX|",    "fn": lambda fx,fy,fz: math.sqrt(fz**2+fy**2)+abs(fx)},
    {"id": "M11", "label": "M11  √((2FZ)²+FY²)",       "fn": lambda fx,fy,fz: math.sqrt((2*fz)**2+fy**2)},
    {"id": "M12", "label": "M12  √(FZ²+(2FY)²)",       "fn": lambda fx,fy,fz: math.sqrt(fz**2+(2*fy)**2)},
    {"id": "M13", "label": "M13  √((2FZ)²+FY²)+|FX|", "fn": lambda fx,fy,fz: math.sqrt((2*fz)**2+fy**2)+abs(fx)},
    {"id": "M14", "label": "M14  √(FZ²+(2FY)²)+|FX|", "fn": lambda fx,fy,fz: math.sqrt(fz**2+(2*fy)**2)+abs(fx)},
    {"id": "M15", "label": "M15  |FX|+Vr",             "fn": lambda fx,fy,fz: abs(fx)+math.sqrt(fy**2+fz**2)},
    {"id": "M16", "label": "M16  FX+Vr",               "fn": lambda fx,fy,fz: fx+math.sqrt(fy**2+fz**2)},
    {"id": "M17", "label": "M17  √((2FX)²+Vr²)",      "fn": lambda fx,fy,fz: math.sqrt((2*fx)**2+fy**2+fz**2)},
    {"id": "M18", "label": "M18  √(FX²+(2Vr)²)",      "fn": lambda fx,fy,fz: math.sqrt(fx**2+(2*fy)**2+(2*fz)**2)},
    {"id": "M19", "label": "M19  √(FX²+FY²+FZ²)",     "fn": lambda fx,fy,fz: math.sqrt(fx**2+fy**2+fz**2)},
]

# ─── RENKLER ───────────────────────────────────────────────────────────────────
BG    = "#0d1117"; BG2   = "#161b22"; BG3   = "#21262d"
BORDER= "#30363d"; ACCENT= "#58a6ff"; GREEN = "#3fb950"
RED_  = "#f85149"; TEXT  = "#e6edf3"; MUTED = "#8b949e"
FM = ("Consolas", 10); FH = ("Consolas", 11, "bold")
FS = ("Consolas", 9);  FT = ("Consolas", 9, "bold")


def entry_opts(**kw):
    return dict(bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                font=FM, bd=0, highlightthickness=1,
                highlightbackground=BORDER, highlightcolor=ACCENT, **kw)


# ─── KRİTİK LC BULMA MANTIĞI ───────────────────────────────────────────────────
def extract_critical_rows(raw_data, allowed_ids=None):
    """
    Her element için her metriğin MAX verdiği LC'yi bulur.
    Tüm metriklerden gelen (EID, LC) birleştirilir → duplicate temizlenir.
    Döndürür: list of dict  {Element ID, Load Case ID, _fx, _fy, _fz, _vals, _metrics}
      _metrics: bu satırı hangi metrikler kritik seçti (gösterim için)
    """
    # 1) Ham veriyi enrich et ve isteğe göre filtrele
    enriched = {}   # (eid, lc) → row dict
    eid_lcs  = {}   # eid → [(lc, row), ...]
    for row in raw_data:
        eid = row["Element ID"]
        if allowed_ids is not None and eid not in allowed_ids:
            continue
        lc = row.get("Load Case ID", "")
        key = (eid, lc)
        if key in enriched:
            continue  # ham duplicate (aynı EID+LC zaten var)
        try:
            fx, fy, fz = float(row["FX"]), float(row["FY"]), float(row["FZ"])
        except ValueError:
            fx = fy = fz = 0.0
        vals = {m["id"]: m["fn"](fx, fy, fz) for m in METRICS}
        r = {**row, "_fx": fx, "_fy": fy, "_fz": fz, "_vals": vals, "_metrics": set()}
        enriched[key] = r
        eid_lcs.setdefault(eid, []).append(r)

    # 2) Her element × her metrik → MAX olan LC'yi kritik işaretle
    for eid, rows in eid_lcs.items():
        for m in METRICS:
            mid = m["id"]
            best = max(rows, key=lambda r, mid=mid: r["_vals"][mid])
            best["_metrics"].add(mid)

    # 3) Sadece en az bir metrik tarafından kritik seçilen satırları al
    result = [r for r in enriched.values() if r["_metrics"]]

    # 4) Orijinal CSV sırasını koru (EID, LC sırası)
    result.sort(key=lambda r: (r["Element ID"], r.get("Load Case ID","")))
    return result


class FastenerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fastener Force Analyzer  ·  MSC Nastran")
        self.geometry("1600x820")
        self.minsize(1000, 600)
        self.configure(bg=BG)

        self.raw_data     = []
        self.filtered     = []
        self.all_elem_var = tk.BooleanVar(value=True)
        self.elem_var     = tk.StringVar(value="")

        self._build_ui()
        self._style_ttk()
        self._on_allelem_change()

    # ── TTK STYLE ──────────────────────────────────────────────────────────────
    def _style_ttk(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview",
            background=BG2, foreground=TEXT, fieldbackground=BG2,
            font=FM, rowheight=22, borderwidth=0)
        s.configure("Treeview.Heading",
            background=BG3, foreground=MUTED, font=FS,
            relief="flat", borderwidth=0)
        s.map("Treeview",
            background=[("selected","#1f3a5f")],
            foreground=[("selected",TEXT)])
        for o in ("Vertical","Horizontal"):
            s.configure(f"{o}.TScrollbar",
                background=BG3, troughcolor=BG2, borderwidth=0, arrowsize=11)

    # ── ANA YAPI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg="#0d2137", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  ⚙  FASTENER FORCE ANALYZER",
                 font=("Consolas",13,"bold"), fg=ACCENT, bg="#0d2137"
                 ).pack(side="left", padx=20)
        tk.Label(hdr,
                 text="Her element · 19 metrik · Kritik LC per metrik → Deduplicate",
                 font=FS, fg=MUTED, bg="#0d2137").pack(side="left", padx=6)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=BG2, width=265)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left(left)

        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_right(right)

    # ── SOL PANEL ──────────────────────────────────────────────────────────────
    def _build_left(self, p):
        # CSV
        sec = self._sec(p, "📂  CSV DOSYASI")
        tk.Button(sec, text="Dosya Seç…", command=self._load_csv,
                  bg="#238636", fg="white", font=FH, relief="flat",
                  cursor="hand2", padx=8, pady=6,
                  activebackground="#2ea043", activeforeground="white"
                  ).pack(fill="x", padx=14, pady=4)
        self.file_lbl = tk.Label(sec, text="Henüz dosya seçilmedi",
                                 font=FS, fg=MUTED, bg=BG2,
                                 wraplength=238, justify="left")
        self.file_lbl.pack(fill="x", padx=14, pady=(0,8))

        # Element ID filtresi
        sec2 = self._sec(p, "🔢  ELEMENT ID FİLTRE")
        self.all_elem_cb = tk.Checkbutton(
            sec2, text="Tüm elementler",
            variable=self.all_elem_var, command=self._on_allelem_change,
            bg=BG2, fg=TEXT, selectcolor=BG2,
            activebackground=BG2, activeforeground=TEXT,
            font=FS, cursor="hand2")
        self.all_elem_cb.pack(anchor="w", padx=14, pady=(6,3))
        tk.Label(sec2, text="Seçili ID'ler  (virgülle:  123, 456, 789)",
                 font=FS, fg=MUTED, bg=BG2).pack(anchor="w", padx=14)
        self.elem_entry = tk.Entry(sec2, textvariable=self.elem_var,
                                   **entry_opts(), width=26)
        self.elem_entry.pack(fill="x", padx=14, pady=(3,12), ipady=5)

        # Açıklama kutusu
        info = tk.Frame(p, bg="#0d2137", pady=8, padx=12)
        info.pack(fill="x", padx=14, pady=(4,4))
        tk.Label(info,
            text=("Her metrik için elemandaki\n"
                  "MAX kritik LC seçilir.\n"
                  "Aynı LC → tek satır kalır."),
            font=FS, fg=MUTED, bg="#0d2137", justify="left"
        ).pack(anchor="w")

        # Hesapla
        tk.Button(p, text="▶   HESAPLA & FİLTRELE", command=self._apply,
                  bg=ACCENT, fg="#0d1117", font=("Consolas",11,"bold"),
                  relief="flat", cursor="hand2", pady=10,
                  activebackground="#79c0ff", activeforeground="#0d1117"
                  ).pack(fill="x", padx=14, pady=12)

        self.stat_lbl = tk.Label(p, text="", font=FS, fg=MUTED,
                                 bg=BG2, justify="left", wraplength=238)
        self.stat_lbl.pack(fill="x", padx=14, pady=2)

        # Export
        tk.Button(p, text="⬇  CSV Olarak Kaydet", command=self._export_csv,
                  bg=BG3, fg=TEXT, font=FM, relief="flat",
                  cursor="hand2", pady=7, activebackground=BORDER
                  ).pack(fill="x", padx=14, pady=(10,18))

    # ── SAĞ PANEL ──────────────────────────────────────────────────────────────
    def _build_right(self, p):
        top = tk.Frame(p, bg=BG2, pady=8)
        top.pack(fill="x")
        self.result_lbl = tk.Label(top,
            text="CSV yükleyip  ▶ HESAPLA & FİLTRELE'ye basın",
            font=FH, fg=MUTED, bg=BG2)
        self.result_lbl.pack(side="left", padx=20)
        self.row_count_lbl = tk.Label(top, text="", font=FS, fg=GREEN, bg=BG2)
        self.row_count_lbl.pack(side="left", padx=4)
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x")

        tf = tk.Frame(p, bg=BG)
        tf.pack(fill="both", expand=True)

        # Sütunlar: 5 sabit + Kritik Metrikler sütunu + 19 metrik değeri
        fixed = ["Element ID", "Load Case ID", "FX", "FY", "FZ", "Kritik Metrikler"]
        cols  = fixed + [m["id"] for m in METRICS]
        self.tree = ttk.Treeview(tf, columns=cols,
                                  show="headings", selectmode="extended")

        self.tree.heading("Element ID",       text="Element ID")
        self.tree.column ("Element ID",       width=90,  anchor="center", minwidth=70)
        self.tree.heading("Load Case ID",     text="LC ID")
        self.tree.column ("Load Case ID",     width=75,  anchor="center", minwidth=60)
        for fc in ["FX","FY","FZ"]:
            self.tree.heading(fc, text=fc)
            self.tree.column (fc, width=90, anchor="center", minwidth=60)
        self.tree.heading("Kritik Metrikler", text="Kritik Metrikler")
        self.tree.column ("Kritik Metrikler", width=160, anchor="w", minwidth=100)
        for m in METRICS:
            self.tree.heading(m["id"], text=m["id"])
            self.tree.column (m["id"], width=78, anchor="center", minwidth=55)

        vsb = ttk.Scrollbar(tf, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)

        self.status_bar = tk.Label(p, text="Hazır", font=FS, fg=MUTED,
                                   bg=BG3, anchor="w", padx=12, pady=4)
        self.status_bar.pack(fill="x", side="bottom")

    # ── OLAYLAR ────────────────────────────────────────────────────────────────
    def _on_allelem_change(self):
        state = "disabled" if self.all_elem_var.get() else "normal"
        if hasattr(self, "elem_entry"):
            self.elem_entry.configure(state=state)

    # ── CSV YÜKLE ──────────────────────────────────────────────────────────────
    def _load_csv(self):
        path = filedialog.askopenfilename(
            title="CSV Dosyası Seç",
            filetypes=[("CSV","*.csv"),("Tüm Dosyalar","*.*")])
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            if not rows:
                messagebox.showerror("Hata","CSV boş."); return

            col_map = {k.strip().lower(): k for k in rows[0].keys()}
            REQUIRED = {
                "element id":   "Element ID",
                "load case id": "Load Case ID",
                "fx": "FX", "fy": "FY", "fz": "FZ"
            }
            missing = [v for n, v in REQUIRED.items() if n not in col_map]
            if missing:
                messagebox.showerror("Hata",
                    f"Eksik sütunlar: {', '.join(missing)}\n"
                    f"Mevcut: {', '.join(rows[0].keys())}"); return

            self.raw_data = [
                {std: row.get(col_map[norm],"")
                 for norm, std in REQUIRED.items()}
                for row in rows
            ]
            name = Path(path).name
            eids = len({r["Element ID"] for r in self.raw_data})
            self.file_lbl.configure(
                text=f"✓  {name}\n{len(rows)} satır  |  {eids} element", fg=GREEN)
            self.stat_lbl.configure(
                text=f"Yüklendi: {len(rows)} satır\n{eids} unique element", fg=MUTED)
            self.status_bar.configure(text=f"Yüklendi: {path}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ── HESAPLA & FİLTRELE ─────────────────────────────────────────────────────
    def _apply(self):
        if not self.raw_data:
            messagebox.showwarning("Uyarı","Önce CSV yükleyin."); return

        if self.all_elem_var.get():
            allowed_ids = None
        else:
            raw_ids = self.elem_var.get()
            allowed_ids = {x.strip() for x in raw_ids.split(",") if x.strip()}
            if not allowed_ids:
                messagebox.showwarning("Uyarı",
                    "Element ID alanı boş!\n"
                    "'Tüm elementler' işaretleyin veya ID girin."); return

        result = extract_critical_rows(self.raw_data, allowed_ids)
        self.filtered = result

        # Tabloyu doldur
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(result):
            tag = "even" if i % 2 == 0 else "odd"
            # Kritik metrik listesi (sıralı, kısa)
            crits = ", ".join(sorted(row["_metrics"]))
            mvals = [f"{row['_vals'][m['id']]:.3f}" for m in METRICS]
            self.tree.insert("","end", tags=(tag,), values=(
                row.get("Element ID",""),
                row.get("Load Case ID",""),
                f"{row['_fx']:.4f}",
                f"{row['_fy']:.4f}",
                f"{row['_fz']:.4f}",
                crits,
                *mvals))
        self.tree.tag_configure("even", background=BG)
        self.tree.tag_configure("odd",  background=BG2)

        eids_found = len({r["Element ID"] for r in result})
        self.result_lbl.configure(
            text=f"Kritik LC'ler  —  {eids_found} element", fg=TEXT)
        self.row_count_lbl.configure(text=f"  {len(result)} kritik satır")
        self.stat_lbl.configure(
            text=(f"Kritik satır: {len(result)}\n"
                  f"Element sayısı: {eids_found}\n"
                  f"Ort LC/element: {len(result)/max(eids_found,1):.1f}"),
            fg=GREEN)
        self.status_bar.configure(
            text=f"Tamamlandı: {len(result)} kritik satır  |  {eids_found} element")

    # ── CSV AKTAR (sadece 5 sütun) ─────────────────────────────────────────────
    def _export_csv(self):
        if not self.filtered:
            messagebox.showwarning("Uyarı","Önce HESAPLA & FİLTRELE'ye basın."); return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile="fastener_critical.csv")
        if not path:
            return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Element ID","Load Case ID","FX","FY","FZ"])
                for row in self.filtered:
                    w.writerow([
                        row.get("Element ID",""),
                        row.get("Load Case ID",""),
                        f"{row['_fx']:.6f}",
                        f"{row['_fy']:.6f}",
                        f"{row['_fz']:.6f}",
                    ])
            messagebox.showinfo("Başarılı", f"Kaydedildi:\n{path}")
            self.status_bar.configure(text=f"Kaydedildi: {path}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    # ── YARDIMCI ───────────────────────────────────────────────────────────────
    def _sec(self, parent, title):
        frm = tk.Frame(parent, bg=BG2)
        frm.pack(fill="x", pady=(6,0))
        tk.Label(frm, text=title, font=FT, fg=MUTED,
                 bg=BG2).pack(anchor="w", padx=14, pady=(8,2))
        tk.Frame(frm, bg=BORDER, height=1).pack(fill="x", padx=14)
        return frm


if __name__ == "__main__":
    app = FastenerApp()
    app.mainloop()
