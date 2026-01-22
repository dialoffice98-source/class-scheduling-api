from datetime import datetime, timedelta

def convert_to_time(results, settings):
    start_time = settings['waktu_mulai_terawal']   # e.g. "07:00"
    interval = settings['interval']                # e.g. 60 minutes

    fmt = "%H:%M"
    start = datetime.strptime(start_time, fmt)

    def index_to_time(idx):
        return (start + timedelta(minutes=idx * interval)).strftime(fmt)

    # Update all schedule entries
    for key, entry in results['jadwal'].items():
        entry['JamMulai'] = index_to_time(entry['JamMulai'])
        entry['JamSelesai'] = index_to_time(entry['JamSelesai'])

    return results

def total_room_usage(schedule, room):
    total_duration = 0

    for (_, _, _), entry in schedule.items():
        if entry["RuanganID"] == room:
            duration = entry["JamSelesai"] - entry["JamMulai"]
            total_duration += duration

    return total_duration

def interpret_solution(model):
    """Extract the solution into a DataFrame."""
    schedule = {}
    for x in model.solution_vars['x']:
        course_id = x[0][0]
        faculty_id = x[0][1]
        class_id = x[0][2]
        session = x[0][3]
        room_id = x[1]
        day = x[2]
        time = x[3]
        
        schedule[(course_id, class_id, session)] = {
            'MKKode': course_id,
            'KelasID': class_id,
            'SesiID': session,
            'DosenID': faculty_id,
            'RuanganID': room_id,
            'HariNama': day,
            'JamMulai': time,
            'JamSelesai': time + model.class_details[course_id][class_id][session]['duration'],
            'KapasitasKelas': model.class_details[course_id][class_id][session]['size'],
            'KapasitasRuangan': model.room_capacity[x[1]],
        }
    
    # room utilization
    room_utilization = {}
    used_room = set()
    for room in model.room_set:
        # Use solution_vars['z'] which is solver-agnostic
        if model.solution_vars['z'].get(room, 0) > 0.5:
            used_room.add(room)
            classes_in_room = total_room_usage(schedule, room)
            total_slots = len(model.day_set) * len(model.time_set)
            utilization = (classes_in_room / total_slots) if total_slots > 0 else 0
            room_utilization[room] = utilization
    
    # output
    results = {
                'jadwal': schedule,
                'maks_jam_mengajar': model.solution_vars['k'],
                'ruangan_digunakan': list(used_room),
                'ruangan_tak_digunakan': [room for room in model.room_set 
                                          if room not in used_room],
                'utilisasi_ruangan': room_utilization,
                'objective_value': model.solution_vars.get('objective', None)
    }
    return results

def remap_schedule_keys(schedule_dict, course_dict):
    """
    Convert schedule keys of the form (MKKode, DosenID, KelasID)
    into the correct KelasKey (e.g. 'FM603002-K01').
    
    Returns:
        tuple: (scheduled_dict, unscheduled_dict)
            - scheduled_dict: Dictionary with remapped keys for scheduled classes
            - unscheduled_dict: Dictionary of unscheduled classes with their info from course_dict
    """
    
    # Build lookup: (MKKode, DosenID) -> 'FM603002-K01'
    key_map = {}
    for kelas_key, info in course_dict.items():
        mk = info["MKKode"]
        kelas = info["KelasID"]
        sesi = info["SesiID"]
        key_map[(mk, kelas, sesi)] = kelas_key

    # Track all kelas_keys from course_dict
    all_kelas_keys = set(course_dict.keys())
    scheduled_kelas_keys = set()

    # Create new schedule dictionary with remapped keys
    new_schedule = {}
    for (mk, kelas, sesi), entry in schedule_dict.items():
        kelas_key = key_map.get((mk, kelas, sesi))
        if kelas_key is None:
            raise ValueError(f"No matching kelas for ({mk}, {kelas}, {sesi})")
        new_schedule[kelas_key] = entry
        scheduled_kelas_keys.add(kelas_key)

    # Find unscheduled classes and return their info from course_dict
    unscheduled_keys = all_kelas_keys - scheduled_kelas_keys
    unscheduled = {kelas_key: course_dict[kelas_key] for kelas_key in unscheduled_keys}

    return new_schedule, unscheduled
