"""
Main script for class scheduling optimization
Orchestrates data loading and optimization workflow using the SchedulingModel class.
"""
import time

from app.services.class_scheduling_main.source.optimization import SchedulingModel
from app.services.class_scheduling_main.source.preprocessing import extract_sets, extract_params, convert_faculty_schedule_to_slots, get_compulsory_course
from app.services.class_scheduling_main.source.postprocessing import interpret_solution, convert_to_time, remap_schedule_keys

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