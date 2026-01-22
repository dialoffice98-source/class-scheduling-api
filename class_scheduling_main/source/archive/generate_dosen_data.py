from util import load_data
import pandas as pd
import os
from numpy import random

if __name__ == "__main__":
    df = load_data("test_course.csv")
    
    # Create a DataFrame with unique course codes
    unique_courses = pd.DataFrame({
        'kode_mk': df["kode_mk"].unique()
    })
    
    # Create a DataFrame with unique DosenID
    unique_dosen = pd.DataFrame({
        'dosen_id': df["dosen_id"].sort_values().unique()
    })
    
    # Create day-timeslot combinations
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat']
    time_slot = list(range(10))

    # Generate lecturer preference template for each lecturer
    preference_rows = []
    unavailable_rows = []
    random.seed(42)  # For reproducibility

    for dosen_id in unique_dosen['dosen_id']:
        for day in days:
            preffered = False
            unavailable = False
            for timeslot in time_slot:
                random_value = random.rand()
                # Generate preference or unavailability
                if not (preffered or unavailable):
                    # Generate new preference or unavailability
                    if random_value < 0.35:  
                        preference_rows.append({
                            'dosen_id': dosen_id,
                            'day': day,
                            'time_slot': timeslot,
                        })
                        preffered = True
                    elif random_value < 0.5:
                        unavailable_rows.append({
                            'dosen_id': dosen_id,
                            'day': day,
                            'time_slot': timeslot,
                        })
                        unavailable = True
                    else:
                        continue
                    
                else:
                    # Consecutive preference and unavailability
                    if preffered and random_value < 0.7:
                        preference_rows.append({
                            'dosen_id': dosen_id,
                            'day': day,
                            'time_slot': timeslot,
                        })
                    elif unavailable and random_value < 0.7:
                        unavailable_rows.append({
                            'dosen_id': dosen_id,
                            'day': day,
                            'time_slot': timeslot,
                        })
                    else:
                        unavailable = False
                        continue

    lecturer_unavailable_df = pd.DataFrame(unavailable_rows)
    lecturer_preferences_df = pd.DataFrame(preference_rows)

    #Save to CSV
    print("Saving generated lecturer preference and unavailability data...")
    lecturer_preferences_df.to_csv("data/pref_dosen.csv", index=False)
    lecturer_unavailable_df.to_csv("data/unav_dosen.csv", index=False)
    unique_courses.to_csv("data/unique_courses.csv", index=False)
    unique_dosen.to_csv("data/unique_dosen.csv", index=False)
    print("Data saved to data/pref_dosen.csv, data/unav_dosen.csv, data/unique_courses.csv, data/unique_dosen.csv")

