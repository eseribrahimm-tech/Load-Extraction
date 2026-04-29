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

master=tk.Tk()
master.title('LOAD EXTRACTION TOOL')
master.geometry("900x700")
 
input_entry_now = ""
output_entry_now = ""
stress_output_now = ""
stress_output_now2 = ""
bush_entry_now = ""
extraction_type = StringVar()
coordinate_system = StringVar()

top_frame = tk.Frame(master)
top_frame.pack(pady=10)
bottom_frame = tk.Frame(master)
bottom_frame.pack(pady=10)

option_label = tk.Label(bottom_frame, text="Select Extraction Type:")
option_label.pack(pady=5)
option_menu = tk.OptionMenu(bottom_frame, extraction_type, "PSHELL ALL AVERAGE", "BUSH LOAD")
option_menu.pack(pady=5)

def bdf_input():
    
    global input_entry_now
    bdf_path=tk.filedialog.askopenfilename(title="Selecet a BDF file", filetypes=(("BDF File","*.bdf"),))
    if not bdf_path:
        print("BDF file nonselected")
        return
    input_entry.delete(0, tk.END)
    input_entry.insert(0, bdf_path)
    input_entry_now=input_entry.get()

def op2_input():
    
    global output_entry_now
    op2_path=tk.filedialog.askopenfilename(title="Selecet a OP2 file", filetypes=(("OP2 File","*.op2"),))
    if not op2_path:
        print("OP2 file nonselected")
        return
    output_entry.delete(0, tk.END)
    output_entry.insert(0, op2_path)
    output_entry_now=output_entry.get()
    
def csv_input():
    
    global stress_entry_now
    csv_path=tk.filedialog.askopenfilename(title="Selecet a CSV file", filetypes=(("CSV File","*.csv"),))
    if not csv_path:
        print("CSV file nonselected")
        return
    stress_output_entry.delete(0, tk.END)
    stress_output_entry.insert(0, csv_path)
    stress_entry_now=stress_output_entry.get()
    
def bush_input():
    
    global bush_entry_now
    bush_path=tk.filedialog.askopenfilename(title="Selecet a CSV file", filetypes=(("CSV File","*.csv"),))
    if not bush_path:
        print("BUSH CSV file nonselected")
        return
    bush_output_entry.delete(0, tk.END)
    bush_output_entry.insert(0, bush_path)
    bush_entry_now = bush_output_entry.get()
    
def output_location():
        
    global stress_entry_now2
    Load_extraction_output=tk.filedialog.askdirectory()
    if not Load_extraction_output:
        print("OUTPUT file nonselected")
        return
    stress_output_entry2.delete(0,tk.END)
    stress_output_entry2.insert(0,Load_extraction_output)
    stress_entry_now2=stress_output_entry2.get()
    
def show_info_ALL_AVERAGE():
    info_text_ALL_AVERAGE.insert(tk.END, """ALL AVERAGE TOOL;
    The extracted loads are determined according to the Element&Material CID.
    The properties you want extract should be grouped under the 'Property ID' header in the CSV.
    """)
    
def show_info_BUSH():
    info_text_BUSH.insert(tk.END, """BUSH TOOL;
      The elements you want extract should be grouped under the 'Element ID' header in the CSV.""")

def update_inputs_visibility(*args):   
    
    extraction = extraction_type.get()
    
    coordinate_label.pack_forget()
    coordinate_dropdown.pack_forget()
    
    bdf_path.pack_forget()
    input_entry.pack_forget()
    browse1.pack_forget()

    op2_path.pack_forget()
    output_entry.pack_forget()
    browse2.pack_forget()
    
    Load_extraction_output.pack_forget()
    stress_output_entry2.pack_forget()
    browse5.pack_forget()
    
    csv_path.pack_forget()
    stress_output_entry.pack_forget()
    browse3.pack_forget()
    
    bush_path.pack_forget()
    bush_output_entry.pack_forget()
    browse4.pack_forget()

    begin_button.pack_forget()
    
    info_text_ALL_AVERAGE.pack_forget()
    
    info_text_BUSH.pack_forget()
    
    if extraction == "PSHELL ALL AVERAGE":
        
        coordinate_label.pack(pady=5)
        coordinate_dropdown.pack(pady=5)
        
        bdf_path.pack(pady=5)
        input_entry.pack(pady=5)
        browse1.pack(pady=5)
        
        op2_path.pack(pady=5)
        output_entry.pack(pady=5)
        browse2.pack(pady=5)
        
        csv_path.pack(pady=5)
        stress_output_entry.pack(pady=5)
        browse3.pack(pady=5)
        
        Load_extraction_output.pack(pady=5)
        stress_output_entry2.pack(pady=5)
        browse5.pack(pady=5)
        
        begin_button.pack(pady=10,fill=tk.X)
        
        info_text_ALL_AVERAGE.pack(pady=10)
        show_info_ALL_AVERAGE()
        master.geometry("")
         
    elif  extraction == "BUSH LOAD":
        
        bdf_path.pack(pady=5)
        input_entry.pack(pady=5)
        browse1.pack(pady=5)
        
        op2_path.pack(pady=5)
        output_entry.pack(pady=5)
        browse2.pack(pady=5)
        
        bush_path.pack(pady=5)
        bush_output_entry.pack(pady=5)
        browse4.pack(pady=5)
        
        Load_extraction_output.pack(pady=5)
        stress_output_entry2.pack(pady=5)
        browse5.pack(pady=5)
        
        begin_button.pack(pady=10,fill=tk.X)
        
        info_text_BUSH.pack(pady=10)
        
        show_info_BUSH()
        master.geometry("")

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
        if not stress_entry_now:
            logger.error("CSV dosyası seçilmedi!")
            messagebox.showerror("Hata", "CSV dosyası seçilmedi (ALL AVERAGE)")
            return

        logger.info("📂 CSV dosyası okunuyor...")
        df_properties = pd.read_csv(stress_entry_now)
        target_property_ids = df_properties['Property ID'].tolist()
        logger.info(f"✓ {len(target_property_ids)} property ID bulundu")

        logger.info("📂 OP2 ve BDF dosyaları okunuyor...")
        op2 = OP2 ()
        bdf = BDF ()
        op2.read_op2(output_entry_now)
        logger.info("✓ OP2 dosyası okundu")
        bdf.read_bdf(input_entry_now, encoding='latin1')
        logger.info("✓ BDF dosyası okundu")

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
        if not bush_entry_now:
            logger.error("Bush CSV dosyası seçilmedi!")
            messagebox.showerror("Hata", "Bush CSV dosyası seçilmedi")
            return

        logger.info("📂 Bush CSV dosyası okunuyor...")
        df_bush = pd.read_csv(bush_entry_now)
        bush_element_ids = df_bush['Element ID'].tolist()
        logger.info(f"✓ {len(bush_element_ids)} bush element ID bulundu")

        logger.info("📂 OP2 dosyası okunuyor...")
        op2 = OP2()
        op2.read_op2(output_entry_now)
        logger.info("✓ OP2 dosyası okundu")

        logger.info("🔄 Bush force verileri çıkarılıyor...")
        bush_forces_data = []
        for load_case_id, element_forces in op2.cbush_force.items():
            element_ids = element_forces.element
            forces_data = element_forces.data[0]
            load_ids = element_forces.loadIDs[0]

            for i, element_id in enumerate(element_ids):
                if element_id in bush_element_ids:
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
        

top_frame = tk.Frame(master)
top_frame.pack(pady=10)
bottom_frame = tk.Frame(master)
bottom_frame.pack(pady=10)


extraction_type.trace("w", update_inputs_visibility)

coordinate_label = tk.Label(top_frame, text="Select Coordinate System:")
coordinate_dropdown = tk.OptionMenu(top_frame, coordinate_system, "Element CID", "Material CID")

bdf_path=tk.Label(top_frame, text="BDF File Location:")
input_entry=tk.Entry(top_frame,text="",width=60)
browse1=tk.Button(top_frame, text='Browse',command=bdf_input)

op2_path=tk.Label(bottom_frame, text="OP2 File Location:")
output_entry=tk.Entry(bottom_frame,text="",width=60)
browse2=tk.Button(bottom_frame, text='Browse',command=op2_input)

csv_path=tk.Label(bottom_frame, text="Shell Property CSV File:")
stress_output_entry=tk.Entry(bottom_frame,text="",width=60)
browse3=tk.Button(bottom_frame, text='Browse',command=csv_input)

bush_path=tk.Label(bottom_frame, text="BUSH CSV File Location:")
bush_output_entry=tk.Entry(bottom_frame,text="",width=60)
browse4=tk.Button(bottom_frame, text='Browse',command=bush_input)

Load_extraction_output=tk.Label(bottom_frame, text="Output File Excel Location:")
stress_output_entry2=tk.Entry(bottom_frame,text="",width=60)
browse5=tk.Button(bottom_frame, text='Browse',command=output_location)

begin_button=tk.Button(bottom_frame, text='Run Script',command=asc_run)


info_text_ALL_AVERAGE = tk.Text(master, height=10, width=70)

info_text_BUSH = tk.Text(master, height=10, width=50)

log_frame = tk.Frame(master, bg="#f0f0f0", height=150)
log_frame.pack(fill="both", expand=False, padx=10, pady=5)
log_label = tk.Label(log_frame, text="📋 İşlem Günlüğü:", bg="#f0f0f0", font=("Courier", 9, "bold"))
log_label.pack(anchor="w", padx=5, pady=(5, 2))
log_text = scrolledtext.ScrolledText(log_frame, height=7, width=110, font=("Courier", 8), bg="white", fg="black")
log_text.pack(fill="both", expand=True, padx=5, pady=5)
log_text.config(state=tk.DISABLED)

master.mainloop()
