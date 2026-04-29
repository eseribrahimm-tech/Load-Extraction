from pyNastran.op2.op2 import OP2
from pyNastran.bdf.bdf import BDF
import pandas as pd
import os
import numpy as np
import tkinter as tk
import time
from tkinter import filedialog, StringVar, messagebox
from pyNastran.op2.data_in_material_coord import data_in_material_coord

master=tk.Tk()
master.title('LOAD EXTRACTION TOOL')
master.geometry("350x150")
 
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
    start_time = time.time()
    if not input_entry_now or not output_entry_now:
        messagebox.showinfo("Necessary files nonselected")
        return
    
    elapsed_time = 0
    
    if extraction_type.get() == "PSHELL ALL AVERAGE":
        if not stress_entry_now:
            messagebox.showinfo("csv file nonselected for ALL AVERAGE")
            return

    
        df_properties = pd.read_csv(stress_entry_now)
        target_property_ids = df_properties['Property ID'].tolist()

        op2 = OP2 ()
        bdf = BDF ()
        op2.read_op2(output_entry_now)
        bdf.read_bdf(input_entry_now, encoding='latin1')

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
        op2_data = data_in_material_coord(bdf, op2, in_place = False) if is_material_cid else op2
        
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
        end_time =time.time()
        elapsed_time = end_time - start_time
        
        
    elif extraction_type.get() == "BUSH LOAD":
        if not bush_entry_now:
            print("CSV nonselected for BUSH element")
            return
        
        df_bush =pd.read_csv(bush_entry_now)
        bush_element_ids = df_bush['Element ID'].tolist()
        
        op2 = OP2()
        op2.read_op2(output_entry_now)
        
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
                        'Element ID':element_id,
                        'Load Case ID': load_ids,
                        'Fx':forces[0],
                        'Fy':forces[1],
                        'Fz':forces[2]
                    })
        df_bush_froces = pd.DataFrame(bush_forces_data)
        output_csv_bush = os.path.join(stress_entry_now2,'Bush_Load.csv')
        df_bush_froces.to_csv(output_csv_bush, index=False)    
        
    end_time =time.time()
    elapsed_time = end_time - start_time
    messagebox.showinfo("Process Done", f"Process Done\nTime: {elapsed_time:.2f} s")
        

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

master.mainloop()
