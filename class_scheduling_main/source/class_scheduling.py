"""
Main script for class scheduling optimization
Orchestrates data loading and optimization workflow using the SchedulingModel class.
"""
import time

from class_scheduling_main.source.optimization import SchedulingModel
from class_scheduling_main.source.preprocessing import extract_sets, extract_params, convert_faculty_schedule_to_slots, get_compulsory_course
from class_scheduling_main.source.postprocessing import interpret_solution, convert_to_time, remap_schedule_keys

def class_scheduling(course_dict, room_dict, settings, 
                     faculty_preference_dict = None, 
                     faculty_unavailability_dict = None,
                     allow_unscheduled_classes = False,
                     quick_scheduling = False,
                     verbose=False):
    start_time = time.time()
    
    ### Preprocessing
    sets = extract_sets(course_dict, room_dict, settings)
    params = extract_params(course_dict, room_dict, settings)
    
    ### Optimization Model
    # Create model
    model = SchedulingModel(sets, params, 
                            allow_unscheduled_classes=allow_unscheduled_classes, # return unscheduled classes but longer running time
                            quick_scheduling=quick_scheduling, # faster running time but lower quality
                            verbose=verbose)
    
    # Build and solve model
    if faculty_preference_dict:
        model.add_preferences(convert_faculty_schedule_to_slots(faculty_preference_dict, settings))
    
    if faculty_unavailability_dict:
        model.add_unavailability(convert_faculty_schedule_to_slots(faculty_unavailability_dict, settings))
    
    model.add_compulsory_courses(get_compulsory_course(course_dict))
    
    model.build()
    model.solve()
    
    end_time = time.time()
    solving_time = end_time - start_time
    
    ### Postprocessing
    if model.solution_vars:
        results = interpret_solution(model)
        
        #convert time index to time
        results = convert_to_time(results, settings)
        
        #convert key to jadwal_id
        results['jadwal'], results['tidak_terjadwal'] = remap_schedule_keys(results['jadwal'], course_dict)
    else:
        # infeasible/unbounded
        results = {}
    responses = {**results,
                 'durasi_solver': solving_time,
                 'status_solver': model.status
                 }
    return responses

if __name__ == "__main__":
    import os
    import json
    import pandas as pd
    from class_scheduling_main.source.visualization import generate_timetables
    
    # Set working directory to script location
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    def load_data(filename):
        """Load data from data folder"""
        parent_dir = '\\'.join(os.path.abspath('.').split('\\')[:-1])
        df = pd.read_csv(parent_dir+f'/data/{filename}')
        return df
    
    def load_settings(filename):
        """Load data from settings folder"""
        parent_dir = '\\'.join(os.path.abspath('.').split('\\')[:-2])
        settings = json.load(open(parent_dir + f'/API-settings/settings/{filename}'))
        return settings
    
    def parse_faculty_schedule(df):
        """Parse faculty schedule DataFrame into {DosenID: {HariNama: [times]}} format"""
        dict =  {}
        for _,row in df.iterrows():
            dict[row['DosenID']]={}
            for col in df.columns[2:]:
                dict[row['DosenID']][col]=eval(row[col])
        return dict
    
    print("="*80)
    print("CLASS SCHEDULING OPTIMIZATION")
    print("="*80)
    
    # Load settings
    settings = load_settings('class_scheduling_settings.json')
    
    # Load data
    print("\n Loading data...")
    course_df = load_data("matakuliah.csv")
    room_df = load_data("ruangan.csv")
    faculty_preference_df = load_data("preferensi_dosen.csv")
    faculty_unavailability_df = load_data("ketidaktersediaan_dosen.csv")
    
    # Convert to dictionary
    course_dict = course_df.set_index(course_df.columns[0]).to_dict(orient="index")
    room_dict = dict(zip(room_df["RuanganID"], room_df["KapasitasRuangan"]))
    faculty_preference_dict = parse_faculty_schedule(faculty_preference_df)
    faculty_unavailability_dict = parse_faculty_schedule(faculty_unavailability_df)
    
    print("\n Optimization start...")
    responses = class_scheduling(course_dict, room_dict, settings, 
                                 faculty_preference_dict=faculty_preference_dict,
                                 faculty_unavailability_dict=faculty_unavailability_dict,
                                 verbose=0)
    
    # Display results
    print("\a")
    print("="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print(f"  Status              : {responses['status_solver']}")
    print(f"  Objective Value     : {responses.get('objective_value', 'N/A'):.2f}" if responses.get('objective_value') else "  Objective Value     : N/A")
    print(f"  Duration            : {responses['durasi_solver']:.2f} seconds")
    print(f"  Max Teaching Hours  : {responses.get('maks_jam_mengajar', 'N/A')}")
    print(f"  Rooms Used          : {len(responses.get('ruangan_digunakan', []))} - {responses.get('ruangan_digunakan', [])}")
    print(f"  Rooms Unused        : {len(responses.get('ruangan_tak_digunakan', []))} - {responses.get('ruangan_tak_digunakan', [])}")
    print(f"  Scheduled           : {len(responses.get('jadwal', {}))}")
    print(f"  Unscheduled         : {len(responses.get('tidak_terjadwal', {}))}")
    if responses.get('tidak_terjadwal'):
        print(f"    -> {list(responses['tidak_terjadwal'].keys())}")
    print("="*80)
    
    # Room utilization
    utilization = responses.get('utilisasi_ruangan', {})
    if utilization:
        total_util = sum(utilization.values()) / len(utilization) if utilization else 0
        print(f"  Room Utilization    : {total_util*100:.1f}% (avg)")
        for room, util in utilization.items():
            print(f"    -> {room}: {util*100:.1f}%")

    print("="*80)
    
    # Save responses to JSON
    parent_dir = '\\'.join(os.path.abspath('.').split('\\')[:-1])
    output_path = parent_dir + '/output/responses.json'
    with open(output_path, 'w') as f:
        json.dump(responses, f, indent=2)
    print(f"\n Results saved to: {output_path}")
    
    # Generate timetables if there are scheduled classes
    if responses.get('jadwal'):
        print("\n Generating timetables...")
        timetable_output_dir = parent_dir + '/output/timetables'
        
        # Generate timetables by room
        generate_timetables(responses['jadwal'], timetable_output_dir + '/ruangan', 
                           course_dict=course_dict, group_by='RuanganID', title_prefix='Ruangan')
        
        # Generate timetables by lecturer
        generate_timetables(responses['jadwal'], timetable_output_dir + '/dosen', 
                           course_dict=course_dict, group_by='DosenID', title_prefix='Dosen')
