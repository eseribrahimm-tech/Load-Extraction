from pyNastran.op2.op2 import OP2
from pyNastran.bdf.bdf import BDF
import pandas as pd
import os
import numpy as np
import tkinter as tk
import time
import math
import logging
from datetime import datetime
from tkinter import filedialog, StringVar, messagebox, scrolledtext
from pyNastran.op2.data_in_material_coord import data_in_material_coord

METRICS = [
    {"id": "M01", "fn": lambda fx,fy,fz: fz},
    {"id": "M02", "fn": lambda fx,fy,fz: -fz},
    {"id": "M03", "fn": lambda fx,fy,fz: fy},
    {"id": "M04", "fn": lambda fx,fy,fz: -fy},
    {"id": "M05", "fn": lambda fx,fy,fz: fx},
    {"id": "M06", "fn": lambda fx,fy,fz: -fx},
    {"id": "M07", "fn": lambda fx,fy,fz: abs(fx)},
    {"id": "M08", "fn": lambda fx,fy,fz: math.sqrt(fy**2+fz**2)},
    {"id": "M09", "fn": lambda fx,fy,fz: math.sqrt(fz**2+fy**2)+abs(fx)},
    {"id": "M10", "fn": lambda fx,fy,fz: math.sqrt((2*fz)**2+fy**2)},
    {"id": "M11", "fn": lambda fx,fy,fz: math.sqrt(fz**2+(2*fy)**2)},
    {"id": "M12", "fn": lambda fx,fy,fz: math.sqrt((2*fz)**2+fy**2)+abs(fx)},
    {"id": "M13", "fn": lambda fx,fy,fz: math.sqrt(fz**2+(2*fy)**2)+abs(fx)},
    {"id": "M14", "fn": lambda fx,fy,fz: abs(fx)+math.sqrt(fy**2+fz**2)},
    {"id": "M15", "fn": lambda fx,fy,fz: fx+math.sqrt(fy**2+fz**2)},
    {"id": "M16", "fn": lambda fx,fy,fz: math.sqrt((2*fx)**2+fy**2+fz**2)},
    {"id": "M17", "fn": lambda fx,fy,fz: math.sqrt(fx**2+(2*fy)**2+(2*fz)**2)},
    {"id": "M18", "fn": lambda fx,fy,fz: math.sqrt(fx**2+fy**2+fz**2)},
]

PSHELL_METRICS = [
    {"id": "M01", "fn": lambda nx,ny,nxy: nx},
    {"id": "M02", "fn": lambda nx,ny,nxy: -nx},
    {"id": "M03", "fn": lambda nx,ny,nxy: ny},
    {"id": "M04", "fn": lambda nx,ny,nxy: -ny},
    {"id": "M05", "fn": lambda nx,ny,nxy: nxy},
    {"id": "M06", "fn": lambda nx,ny,nxy: -nxy},
    {"id": "M07", "fn": lambda nx,ny,nxy: math.sqrt(nx**2 + ny**2)},
    {"id": "M08", "fn": lambda nx,ny,nxy: math.sqrt(nx**2 + ny**2) + abs(nxy)},
    {"id": "M09", "fn": lambda nx,ny,nxy: math.sqrt(2*nx**2 + 2*ny**2)},
    {"id": "M10", "fn": lambda nx,ny,nxy: math.sqrt(nx**2 + 2*ny**2)},
    {"id": "M11", "fn": lambda nx,ny,nxy: math.sqrt(2*nx**2 + ny**2) + 2*abs(nxy)},
    {"id": "M12", "fn": lambda nx,ny,nxy: math.sqrt(nx**2 + 2*ny**2) + 2*abs(nxy)},
    {"id": "M13", "fn": lambda nx,ny,nxy: nx + ny + nxy},
    {"id": "M14", "fn": lambda nx,ny,nxy: nx + ny},
    {"id": "M15", "fn": lambda nx,ny,nxy: ny + nxy},
    {"id": "M16", "fn": lambda nx,ny,nxy: nx + nxy},
]

def parse_id_input(input_str, all_ids=None):
    input_str = input_str.strip().upper()
    if input_str == "ALL":
        return all_ids if all_ids else []
    try:
        ids = [int(x.strip()) for x in input_str.split(',') if x.strip()]
        return ids
    except ValueError:
        return []

def extract_critical_pshell(raw_data, group_key, nx_key, ny_key, nxy_key):
    enriched  = {}
    group_lcs = {}
    for row in raw_data:
        gid = row[group_key]
        lc  = row['Load Case ID']
        key = (gid, lc)
        if key in enriched:
            continue
        try:
            nx  = float(row[nx_key])
            ny  = float(row[ny_key])
            nxy = float(row[nxy_key])
        except (ValueError, TypeError):
            nx = ny = nxy = 0.0
        vals = {m["id"]: m["fn"](nx, ny, nxy) for m in PSHELL_METRICS}
        r = {**row, "_nx": nx, "_ny": ny, "_nxy": nxy, "_vals": vals, "_metrics": set()}
        enriched[key] = r
        group_lcs.setdefault(gid, []).append(r)

    for gid, rows in group_lcs.items():
        for m in PSHELL_METRICS:
            mid  = m["id"]
            best = max(rows, key=lambda r, mid=mid: r["_vals"][mid])
            best["_metrics"].add(mid)

    result = [r for r in enriched.values() if r["_metrics"]]
    result.sort(key=lambda r: (r[group_key], r['Load Case ID']))
    return result

def extract_critical_rows(raw_data):
    enriched = {}
    eid_lcs  = {}
    for row in raw_data:
        eid = row["Element ID"]
        lc  = row["Load Case ID"]
        key = (eid, lc)
        if key in enriched:
            continue
        try:
            fx, fy, fz = float(row["FX"]), float(row["FY"]), float(row["FZ"])
        except (ValueError, TypeError):
            fx = fy = fz = 0.0
        vals = {m["id"]: m["fn"](fx, fy, fz) for m in METRICS}
        r = {**row, "_fx": fx, "_fy": fy, "_fz": fz, "_vals": vals, "_metrics": set()}
        enriched[key] = r
        eid_lcs.setdefault(eid, []).append(r)

    for eid, rows in eid_lcs.items():
        for m in METRICS:
            mid = m["id"]
            best = max(rows, key=lambda r, mid=mid: r["_vals"][mid])
            best["_metrics"].add(mid)

    result = [r for r in enriched.values() if r["_metrics"]]
    result.sort(key=lambda r: (r["Element ID"], r["Load Case ID"]))
    return result

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)
        self.text_widget.update()

logger = logging.getLogger('LoadExtraction')
logger.setLevel(logging.INFO)

input_entry_now = ""
output_entry_now = ""
stress_output_now = ""
stress_output_now2 = ""
pshell_property_ids = ""
bush_element_ids = ""
extraction_type = StringVar(value="PSHELL ALL AVERAGE")
coordinate_system = StringVar(value="Element CID")

COLORS = {
    'dark_bg': '#1e1e2e',
    'card_bg': '#2d2d44',
    'accent': '#4a9eff',
    'accent_dark': '#2e6bb8',
    'text': '#e0e0e0',
    'text_light': '#a0a0a0',
    'success': '#4caf50',
    'error': '#f44336',
    'warning': '#ff9800'
}

master = tk.Tk()
master.title('Load Extraction Tool')
master.geometry("1200x800")
master.configure(bg=COLORS['dark_bg'])
master.minsize(1000, 700)

def create_title_frame(parent):
    frame = tk.Frame(parent, bg=COLORS['accent'], height=80)
    frame.pack(fill="x", padx=0, pady=0)
    frame.pack_propagate(False)

    title = tk.Label(frame, text="⚙  LOAD EXTRACTION TOOL",
                     font=("Segoe UI", 24, "bold"),
                     bg=COLORS['accent'], fg="white")
    title.pack(pady=15)
    subtitle = tk.Label(frame, text="Extract and analyze FEA loads from Nastran OP2 files",
                        font=("Segoe UI", 10),
                        bg=COLORS['accent'], fg="white", alpha=0.8)
    subtitle.pack()
    return frame

def create_card(parent, title, bg=None):
    bg = bg or COLORS['card_bg']
    card = tk.Frame(parent, bg=bg, relief="flat", borderwidth=0)
    card.configure(highlightbackground=COLORS['accent'], highlightthickness=1)

    header = tk.Label(card, text=title, font=("Segoe UI", 11, "bold"),
                     bg=bg, fg=COLORS['accent'])
    header.pack(anchor="w", padx=15, pady=(10, 5))

    return card

def create_file_selector(parent, label_text, button_cmd):
    frame = tk.Frame(parent, bg=COLORS['card_bg'])
    frame.pack(fill="x", padx=0, pady=(0, 10))

    label = tk.Label(frame, text=label_text, font=("Segoe UI", 10),
                    bg=COLORS['card_bg'], fg=COLORS['text'])
    label.pack(anchor="w", padx=15, pady=(10, 5))

    file_frame = tk.Frame(frame, bg=COLORS['card_bg'])
    file_frame.pack(fill="x", padx=15, pady=(0, 10))

    entry = tk.Entry(file_frame, font=("Courier", 9),
                    bg="#3a3a4a", fg=COLORS['text_light'],
                    insertbackground=COLORS['accent'],
                    relief="flat", bd=0, padx=10, pady=8)
    entry.pack(side="left", fill="both", expand=True)

    btn = tk.Button(file_frame, text="📂 Browse", command=button_cmd,
                   bg=COLORS['accent'], fg="white", relief="flat",
                   font=("Segoe UI", 9, "bold"), cursor="hand2",
                   padx=15, pady=5)
    btn.pack(side="right", padx=(10, 0), ipady=2)

    return entry, btn, frame

def create_option_selector(parent, label_text, options):
    frame = tk.Frame(parent, bg=COLORS['card_bg'])
    frame.pack(fill="x", padx=0, pady=(0, 10))

    label = tk.Label(frame, text=label_text, font=("Segoe UI", 10),
                    bg=COLORS['card_bg'], fg=COLORS['text'])
    label.pack(anchor="w", padx=15, pady=(10, 5))

    var = StringVar()

    options_frame = tk.Frame(frame, bg=COLORS['card_bg'])
    options_frame.pack(fill="x", padx=15, pady=(0, 10))

    for opt in options:
        rb = tk.Radiobutton(options_frame, text=opt, variable=var, value=opt,
                          bg=COLORS['card_bg'], fg=COLORS['text'],
                          selectcolor=COLORS['accent'], activebackground=COLORS['card_bg'],
                          font=("Segoe UI", 10), cursor="hand2")
        rb.pack(anchor="w", padx=10, pady=3)

    var.set(options[0])
    return var

def bdf_input():
    global input_entry_now
    bdf_path=tk.filedialog.askopenfilename(title="Select a BDF file", filetypes=(("BDF File","*.bdf"),))
    if not bdf_path:
        return
    input_entry_now = bdf_path
    input_entry.delete(0, tk.END)
    input_entry.insert(0, f"✓ {os.path.basename(bdf_path)}")

def op2_input():
    global output_entry_now
    op2_path=tk.filedialog.askopenfilename(title="Select a OP2 file", filetypes=(("OP2 File","*.op2"),))
    if not op2_path:
        return
    output_entry_now = op2_path
    output_entry.delete(0, tk.END)
    output_entry.insert(0, f"✓ {os.path.basename(op2_path)}")

def update_pshell_ids(*args):
    global pshell_property_ids
    pshell_property_ids = property_id_entry.get().strip()

def update_bush_ids(*args):
    global bush_element_ids
    bush_element_ids = element_id_entry.get().strip()

def output_location():
    global stress_output_now2
    output_path=tk.filedialog.askdirectory(title="Select output directory")
    if not output_path:
        return
    stress_output_now2 = output_path
    stress_output_entry2.delete(0, tk.END)
    stress_output_entry2.insert(0, f"✓ {os.path.basename(output_path)}")

def asc_run():
    log_text.config(state=tk.NORMAL)
    log_text.delete(1.0, tk.END)
    log_text.config(state=tk.DISABLED)

    file_handler = logging.FileHandler(os.path.join(stress_entry_now2, f'LoadExtraction_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'))
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    text_handler = TextHandler(log_text)
    text_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    logger.addHandler(text_handler)

    logger.info("="*60)
    logger.info("LOAD EXTRACTION TOOL BAŞLATILDI")
    logger.info(f"Mod: {extraction_type.get()}")
    logger.info("="*60)

    start_time = time.time()
    if not input_entry_now or not output_entry_now:
        logger.error("Gerekli dosyalar seçilmedi!")
        messagebox.showerror("Hata", "Gerekli dosyalar seçilmedi")
        return

    elapsed_time = 0
    
    if extraction_type.get() == "PSHELL ALL AVERAGE":
        if not pshell_property_ids:
            logger.error("Property ID'leri girin!")
            messagebox.showerror("Hata", "Property ID'leri girin (tüm için: ALL veya 123,456,789)")
            return

        logger.info("📂 OP2 ve BDF dosyaları okunuyor...")
        op2 = OP2 ()
        bdf = BDF ()
        op2.read_op2(output_entry_now)
        logger.info("✓ OP2 dosyası okundu")
        bdf.read_bdf(input_entry_now, encoding='latin1')
        logger.info("✓ BDF dosyası okundu")

        logger.info("🔍 Property ID'leri parse ediliyor...")
        all_pids = set([elem.pid for elem in bdf.elements.values()
                       if elem.type in ("CQUAD4", "CTRIA3")])
        target_property_ids = parse_id_input(pshell_property_ids, list(all_pids))
        if not target_property_ids:
            target_property_ids = list(all_pids)
        logger.info(f"✓ {len(target_property_ids)} property ID seçildi")

        elements_with_properties = {
            element_id: element.pid
            for element_id, element in bdf.elements.items()
                if (element.type == "CQUAD4" or element.type == "CTRIA3") and element.pid in target_property_ids
        }

        property_forces = {}

        property_forces = {
            load_case_id: {
                pid:{'Nx':0.0, 'Ny':0.0, 'Nxy':0.0}
                for pid in target_property_ids
                }
            for load_case_id in set(op2.cquad4_force.keys()).union(op2.ctria3_force.keys())
        }  

        property_areas = {}
        element_areas = {}

        for element_id, element in bdf.elements.items():
            if element.pid in target_property_ids:        
                property_id = element.pid       
                area = element.Area()
                element_areas[element_id] = area        
                if property_id not in property_areas:
                    property_areas[property_id] = 0.0
                property_areas[property_id] += area
        

        element_base_data = []

        is_material_cid = coordinate_system.get() == "Material CID"
        coord_mode = "Material CID" if is_material_cid else "Element CID"
        logger.info(f"🔄 Koordinat sistemi: {coord_mode}")
        op2_data = data_in_material_coord(bdf, op2, in_place = False) if is_material_cid else op2
        logger.info("✓ Koordinat dönüşümü tamamlandı" if is_material_cid else "✓ Element CID kullanılacak")
        
        for load_case_id, element_forces in op2_data.cquad4_force.items():     
            element_ids = element_forces.element
            forces_data = element_forces.data[0]
            load_ids = element_forces.loadIDs[0]    
            for element_id, element_property_id in elements_with_properties.items():
                if element_id in element_ids:
                    index = np.where(element_ids == element_id)[0][0]
                    forces = forces_data[index][:3]  
                    area = element_areas[element_id]
            
                    property_forces[load_case_id][element_property_id]['Nx'] += forces[0] * area
                    property_forces[load_case_id][element_property_id]['Ny'] += forces[1] * area
                    property_forces[load_case_id][element_property_id]['Nxy'] += forces[2] * area
                    element_base_data.append({
                        'Property ID':element_property_id,
                        'Element ID':element_id,    
                        'Load Case ID' : load_ids,
                        'Nx':forces[0],
                        'Ny':forces[1],
                        'Nxy':forces[2], 
                        'Area': area
                        })
                    
        for load_case_id, element_forces in op2_data.ctria3_force.items():    
            element_ids = element_forces.element
            forces_data = element_forces.data[0]
            load_ids = element_forces.loadIDs[0]    
    
            for element_id, element_property_id in elements_with_properties.items():
                if element_id in element_ids:
                    index = np.where(element_ids == element_id)[0][0]
                    forces = forces_data[index][:3]  
                    area = element_areas[element_id]
            
                    property_forces[load_case_id][element_property_id]['Nx'] += forces[0] * area
                    property_forces[load_case_id][element_property_id]['Ny'] += forces[1] * area
                    property_forces[load_case_id][element_property_id]['Nxy'] += forces[2] * area
                    element_base_data.append({
                        'Property ID':element_property_id,
                        'Element ID':element_id,    
                        'Load Case ID' : load_ids,
                        'Nx':forces[0],
                        'Ny':forces[1],
                        'Nxy':forces[2], 
                        'Area': area
                        })
           
            df = pd.DataFrame(element_base_data)
            output_csv = os.path.join(stress_entry_now2, 'Element_Load.csv')
            df.to_csv(output_csv, index=False)
            logger.info(f"✓ Element_Load.csv yazıldı ({len(df)} satır)")

        Average_forces = []
        for load_case_id, force_by_property in property_forces.items():
            for property_id, forces in force_by_property.items():
                total_area = property_areas[property_id]
                Average_Nx = forces['Nx'] / total_area
                Average_Ny = forces['Ny'] / total_area
                Average_Nxy = forces ['Nxy'] / total_area
                Average_forces.append({
                    'Property ID': property_id,
                    'Load Case ID': load_case_id,
                    'Average Nx': Average_Nx,
                    'Average Ny': Average_Ny,
                    'Average_Nxy': Average_Nxy,
                    'Average_Area': total_area
                    })
    
        df2 = pd.DataFrame(Average_forces)
        output_csv2 = os.path.join(stress_entry_now2, 'Average_Load.csv')
        df2.to_csv(output_csv2, index=False)
        logger.info(f"✓ Average_Load.csv yazıldı ({len(df2)} satır)")

        logger.info("🔄 Element reduction hesaplanıyor (16 metrik)...")
        critical_elem = extract_critical_pshell(
            element_base_data, 'Element ID', 'Nx', 'Ny', 'Nxy')
        reduced_elem = [{
            'Property ID':  r['Property ID'],
            'Element ID':   r['Element ID'],
            'Load Case ID': r['Load Case ID'],
            'Nx':           r['_nx'],
            'Ny':           r['_ny'],
            'Nxy':          r['_nxy'],
            'Area':         r['Area'],
        } for r in critical_elem]
        df_elem_reduced = pd.DataFrame(reduced_elem)
        output_csv_elem_reduced = os.path.join(stress_entry_now2, 'Element_Load_Reduced.csv')
        df_elem_reduced.to_csv(output_csv_elem_reduced, index=False)
        logger.info(f"✓ Element_Load_Reduced.csv yazıldı ({len(df_elem_reduced)} kritik satır)")

        logger.info("🔄 Average reduction hesaplanıyor (16 metrik)...")
        critical_avg = extract_critical_pshell(
            Average_forces, 'Property ID', 'Average Nx', 'Average Ny', 'Average_Nxy')
        reduced_avg = [{
            'Property ID':  r['Property ID'],
            'Load Case ID': r['Load Case ID'],
            'Average Nx':   r['_nx'],
            'Average Ny':   r['_ny'],
            'Average_Nxy':  r['_nxy'],
            'Average_Area': r['Average_Area'],
        } for r in critical_avg]
        df_avg_reduced = pd.DataFrame(reduced_avg)
        output_csv_avg_reduced = os.path.join(stress_entry_now2, 'Average_Load_Reduced.csv')
        df_avg_reduced.to_csv(output_csv_avg_reduced, index=False)
        logger.info(f"✓ Average_Load_Reduced.csv yazıldı ({len(df_avg_reduced)} kritik satır)")

        end_time =time.time()
        elapsed_time = end_time - start_time
        
        
    elif extraction_type.get() == "BUSH LOAD":
        if not bush_element_ids:
            logger.error("Element ID'leri girin!")
            messagebox.showerror("Hata", "Element ID'leri girin (tüm için: ALL veya 452,678,890)")
            return

        logger.info("📂 OP2 dosyası okunuyor...")
        op2 = OP2()
        op2.read_op2(output_entry_now)
        logger.info("✓ OP2 dosyası okundu")

        logger.info("🔍 Element ID'leri parse ediliyor...")
        all_eids = []
        for load_case_id, element_forces in op2.cbush_force.items():
            all_eids.extend(element_forces.element)
        all_eids = list(set(all_eids))

        selected_element_ids = parse_id_input(bush_element_ids, all_eids)
        if not selected_element_ids:
            selected_element_ids = all_eids
        logger.info(f"✓ {len(selected_element_ids)} element ID seçildi")

        logger.info("🔄 Bush force verileri çıkarılıyor...")
        bush_forces_data = []
        for load_case_id, element_forces in op2.cbush_force.items():
            element_ids = element_forces.element
            forces_data = element_forces.data[0]
            load_ids = element_forces.loadIDs[0]

            for i, element_id in enumerate(element_ids):
                if element_id in selected_element_ids:
                    index = np.where(element_ids == element_id)[0][0]
                    forces = forces_data[index][:3]
                    bush_forces_data.append({
                        'Element ID': element_id,
                        'Load Case ID': load_ids,
                        'FX': forces[0],
                        'FY': forces[1],
                        'FZ': forces[2]
                    })

        df_bush_raw = pd.DataFrame(bush_forces_data)
        output_csv_bush_raw = os.path.join(stress_entry_now2, 'Bush_Load_Raw.csv')
        df_bush_raw.to_csv(output_csv_bush_raw, index=False)
        logger.info(f"✓ Bush_Load_Raw.csv yazıldı ({len(df_bush_raw)} satır)")

        logger.info("🔄 Bush reduction hesaplanıyor (18 metrik)...")
        critical_rows = extract_critical_rows(bush_forces_data)
        reduced_data = [{
            'Element ID':    r['Element ID'],
            'Load Case ID':  r['Load Case ID'],
            'FX':            r['_fx'],
            'FY':            r['_fy'],
            'FZ':            r['_fz'],
        } for r in critical_rows]
        df_bush_reduced = pd.DataFrame(reduced_data)
        output_csv_bush_reduced = os.path.join(stress_entry_now2, 'Bush_Load_Reduced.csv')
        df_bush_reduced.to_csv(output_csv_bush_reduced, index=False)
        logger.info(f"✓ Bush_Load_Reduced.csv yazıldı ({len(df_bush_reduced)} kritik satır)")
        
    end_time =time.time()
    elapsed_time = end_time - start_time
    logger.info("="*60)
    logger.info(f"✅ İşlem tamamlandı! ({elapsed_time:.2f} saniye)")
    logger.info(f"📁 Çıktılar kaydedildi: {stress_entry_now2}")
    logger.info("="*60)
    messagebox.showinfo("Başarılı", f"İşlem Tamamlandı\nSüre: {elapsed_time:.2f} saniye\nKlasör: {stress_entry_now2}")
        

create_title_frame(master)

main_frame = tk.Frame(master, bg=COLORS['dark_bg'])
main_frame.pack(fill="both", expand=True, padx=15, pady=15)

mode_frame = tk.Frame(main_frame, bg=COLORS['dark_bg'])
mode_frame.pack(fill="x", padx=0, pady=(0, 20))
tk.Label(mode_frame, text="📌 Select Mode:", font=("Segoe UI", 12, "bold"),
         bg=COLORS['dark_bg'], fg=COLORS['accent']).pack(anchor="w")

mode_inner = tk.Frame(mode_frame, bg=COLORS['dark_bg'])
mode_inner.pack(fill="x", pady=(10, 0))

for mode in ["PSHELL ALL AVERAGE", "BUSH LOAD"]:
    tk.Radiobutton(mode_inner, text=f"  {mode}", variable=extraction_type, value=mode,
                  bg=COLORS['dark_bg'], fg=COLORS['text'], selectcolor=COLORS['accent'],
                  activebackground=COLORS['dark_bg'], font=("Segoe UI", 10),
                  cursor="hand2", command=on_mode_change).pack(anchor="w", padx=20, pady=5)

scroll = tk.Canvas(main_frame, bg=COLORS['dark_bg'], highlightthickness=0)
scroll.pack(fill="both", expand=True)
scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=scroll.yview)
scrollbar.pack(side="right", fill="y")
scroll.configure(yscrollcommand=scrollbar.set)

content_frame = tk.Frame(scroll, bg=COLORS['dark_bg'])
scroll.create_window((0, 0), window=content_frame, anchor="nw")

pshell_frame = tk.Frame(content_frame, bg=COLORS['dark_bg'])
bush_frame = tk.Frame(content_frame, bg=COLORS['dark_bg'])

pshell_card = create_card(pshell_frame, "⚙  PSHELL ALL AVERAGE")
pshell_card.pack(fill="x", padx=0, pady=(0, 15))

input_entry, _, _ = create_file_selector(pshell_card, "📄 BDF File", bdf_input)
output_entry, _, _ = create_file_selector(pshell_card, "📊 OP2 File", op2_input)

prop_label = tk.Label(pshell_card, text="📋 Property IDs", font=("Segoe UI", 10),
                     bg=COLORS['card_bg'], fg=COLORS['text'])
prop_label.pack(anchor="w", padx=15, pady=(10, 5))
property_id_entry = tk.Entry(pshell_card, font=("Segoe UI", 10),
                            bg="#3a3a4a", fg=COLORS['text'],
                            insertbackground=COLORS['accent'],
                            relief="flat", bd=0, padx=10, pady=8)
property_id_entry.pack(fill="x", padx=15, pady=(0, 5))
property_id_entry.insert(0, "ALL  (or: 123,456,789)")
property_id_entry.bind("<KeyRelease>", update_pshell_ids)
tk.Label(pshell_card, text="Enter ALL for all properties or comma-separated IDs",
         font=("Segoe UI", 8), bg=COLORS['card_bg'], fg=COLORS['text_light']).pack(anchor="w", padx=15, pady=(0, 10))

coord_frame = create_card(pshell_card, "🔄 Coordinate System")
coord_frame.pack(fill="x", padx=0, pady=(0, 10))
for opt in ["Element CID", "Material CID"]:
    tk.Radiobutton(coord_frame, text=opt, variable=coordinate_system, value=opt,
                  bg=COLORS['card_bg'], fg=COLORS['text'], selectcolor=COLORS['accent'],
                  activebackground=COLORS['card_bg'], font=("Segoe UI", 10),
                  cursor="hand2").pack(anchor="w", padx=20, pady=5)

stress_output_entry2, _, _ = create_file_selector(pshell_card, "📁 Output Directory", output_location)

bush_card = create_card(bush_frame, "⚙  BUSH LOAD")
bush_card.pack(fill="x", padx=0, pady=(0, 15))

input_entry2, _, _ = create_file_selector(bush_card, "📄 BDF File", bdf_input)
output_entry2, _, _ = create_file_selector(bush_card, "📊 OP2 File", op2_input)

elem_label = tk.Label(bush_card, text="🔧 Element IDs", font=("Segoe UI", 10),
                     bg=COLORS['card_bg'], fg=COLORS['text'])
elem_label.pack(anchor="w", padx=15, pady=(10, 5))
element_id_entry = tk.Entry(bush_card, font=("Segoe UI", 10),
                           bg="#3a3a4a", fg=COLORS['text'],
                           insertbackground=COLORS['accent'],
                           relief="flat", bd=0, padx=10, pady=8)
element_id_entry.pack(fill="x", padx=15, pady=(0, 5))
element_id_entry.insert(0, "ALL  (or: 452,678,890)")
element_id_entry.bind("<KeyRelease>", update_bush_ids)
tk.Label(bush_card, text="Enter ALL for all elements or comma-separated IDs",
         font=("Segoe UI", 8), bg=COLORS['card_bg'], fg=COLORS['text_light']).pack(anchor="w", padx=15, pady=(0, 10))

stress_output_entry3, _, _ = create_file_selector(bush_card, "📁 Output Directory", output_location)

pshell_frame.pack(fill="x")

content_frame.update_idletasks()
scroll.configure(scrollregion=scroll.bbox("all"))

def on_mode_change():
    pshell_frame.pack_forget()
    bush_frame.pack_forget()
    if extraction_type.get() == "PSHELL ALL AVERAGE":
        pshell_frame.pack(fill="x")
    else:
        bush_frame.pack(fill="x")
    content_frame.update_idletasks()
    scroll.configure(scrollregion=scroll.bbox("all"))

log_frame = tk.Frame(master, bg=COLORS['card_bg'], height=140)
log_frame.pack(fill="both", expand=False, padx=15, pady=(0, 15))
tk.Label(log_frame, text="📋 Process Log", font=("Segoe UI", 11, "bold"),
         bg=COLORS['card_bg'], fg=COLORS['accent']).pack(anchor="w", padx=15, pady=(10, 5))
log_text = scrolledtext.ScrolledText(log_frame, height=6, font=("Courier", 8),
                                     bg="#1a1a2a", fg=COLORS['text_light'], insertbackground=COLORS['accent'])
log_text.pack(fill="both", expand=True, padx=15, pady=(0, 10))
log_text.config(state=tk.DISABLED)

button_frame = tk.Frame(master, bg=COLORS['dark_bg'])
button_frame.pack(fill="x", padx=15, pady=(0, 15))
tk.Button(button_frame, text="▶  RUN ANALYSIS", command=asc_run,
          bg=COLORS['success'], fg="white", font=("Segoe UI", 12, "bold"),
          relief="flat", cursor="hand2", padx=30, pady=12).pack(side="left", expand=True, fill="both", padx=(0, 7))
tk.Button(button_frame, text="⟳  CLEAR", command=lambda: log_text.config(state=tk.NORMAL) or log_text.delete(1.0, tk.END) or log_text.config(state=tk.DISABLED),
          bg="#666", fg="white", font=("Segoe UI", 11, "bold"),
          relief="flat", cursor="hand2", padx=20, pady=12).pack(side="left", expand=True, fill="both")

on_mode_change()

master.mainloop()
