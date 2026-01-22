# -*- coding: utf-8 -*-
"""
Created on Sat Nov 29 16:54:02 2025

@author: ghany
"""
from datetime import datetime

def calculate_time_slots(settings):
    fmt = "%H:%M"
    start = datetime.strptime(settings['waktu_mulai_terawal'], fmt)
    end = datetime.strptime(settings['waktu_selesai_terakhir'], fmt)

    diff = end - start
    minutes = diff.total_seconds() / 60
    
    return int(minutes // settings['interval'])

def time_to_slot(time_str, settings):
    """
    Convert a time string (e.g., '09:00') to a time slot index.
    
    Args:
        time_str: Time in 'HH:MM' format
        settings: Settings dict with 'waktu_mulai_terawal' and 'interval'
    
    Returns:
        Integer time slot index (0-based)
    """
    fmt = "%H:%M"
    start = datetime.strptime(settings['waktu_mulai_terawal'], fmt)
    time = datetime.strptime(time_str, fmt)
    
    diff = time - start
    minutes = diff.total_seconds() / 60
    
    return int(minutes // settings['interval'])

def times_to_slots(time_list, settings):
    """
    Convert a list of time strings to time slot indices.
    
    Args:
        time_list: List of times in 'HH:MM' format
        settings: Settings dict with 'waktu_mulai_terawal' and 'interval'
    
    Returns:
        List of integer time slot indices
    """
    return [time_to_slot(t, settings) for t in time_list]

def convert_faculty_schedule_to_slots(faculty_schedule, settings):
    """
    Convert faculty schedule times to slot indices.
    
    Args:
        faculty_schedule: Dict {lecturer: {day: [times]}}
        settings: Settings dict
    
    Returns:
        Dict {lecturer: {day: [slot_indices]}}
    """
    result = {}
    for lecturer, days in faculty_schedule.items():
        result[lecturer] = {}
        for day, times in days.items():
            result[lecturer][day] = times_to_slots(times, settings) if times else []
    return result

def extract_sets(course_dict, room_dict, settings):
    sets = {}
    sets['courses'] = {course['MKKode'] for course in course_dict.values()}
    sets['faculties'] = {course['DosenID'] for course in course_dict.values()}
    sets['pairs'] = {(course['MKKode'], course['DosenID'], course['KelasID'], course['SesiID']) for course in course_dict.values()}

    sets['rooms'] = set(room_dict.keys())
    sets['days'] = set(settings['daftar_hari'])
    sets['times'] = set(range(calculate_time_slots(settings)))
    
    # Create lookup dictionaries
    course_faculties = {}
    faculty_courses = {}
    
    for course, faculty,_,_ in sets['pairs']:
        if course not in course_faculties:
            course_faculties[course] = []
        course_faculties[course].append(faculty)
        
        if faculty not in faculty_courses:
            faculty_courses[faculty] = []
        faculty_courses[faculty].append(course)
    
    sets['course_faculties'] = course_faculties
    sets['faculty_courses'] = faculty_courses
    return sets

def extract_params(course_dict, room_dict, settings):
    params = {}
    
    # class_details - nested dict: MKKode -> KelasID -> SesiID -> {lecturer, duration, size}
    class_details = {}
    for course in course_dict.values():
        course_code = course['MKKode']
        class_id = course['KelasID']
        session_id = course['SesiID']
        
        if course_code not in class_details:
            class_details[course_code] = {}
        if class_id not in class_details[course_code]:
            class_details[course_code][class_id] = {}
        
        class_details[course_code][class_id][session_id] = {
            'lecturer': course['DosenID'],
            'duration': course['DurasiJam'],
            'size': course['KapasitasKelas']
        }

    params['class_details'] = class_details

    # room_capacity
    params['room_capacity'] = room_dict
    
    # penalty
    params['penalty'] = settings['penalti']
    
    # optimization settings
    params['optimization_settings'] = settings['optimization_settings']
    return params

def get_compulsory_course(course_dict):
    """Extract compulsory course from course dictionary into {PackageID: [MKKode]} format
    
    Extracts unique PaketID values and groups MKKode by package.
    Excludes packages with PaketID=0 (general/unpackaged courses).
    
    Args:
        course_dict: Dictionary of courses with PaketID and MKKode fields
    
    Returns:
        Dict {PackageID: [MKKode]} for packages with multiple courses
    """
    compulsory_dict = {}
    # Group by PaketID and collect unique MKKode for each package
    paket_courses = {}
    for course in course_dict.values():
        paket_id = course['PaketID']
        if paket_id == 0:  # Skip general/unpackaged courses
            continue
        if paket_id not in paket_courses:
            paket_courses[paket_id] = set()
        paket_courses[paket_id].add(course['MKKode'])
    
    # Only include packages with multiple courses
    for paket_id, courses in paket_courses.items():
        if len(courses) > 1:
            compulsory_dict[paket_id] = list(courses)
    
    return compulsory_dict

