# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 17:51:23 2025

@author: Ariansyah
"""
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

### GENERATE TIMETABLE =============================================================
# Need polishing to make it look good an flexible

def _time_to_hour(time_str):
    """Convert time string (HH:MM) to hours as float (e.g., 09:30 -> 9.5)."""
    parts = time_str.split(':')
    return int(parts[0]) + int(parts[1]) / 60.0

def _create_timetable_html(schedule_list, identifier, output_dir, title_prefix='Schedule', course_dict=None):
    """
    Create a visual timetable from schedule data as HTML file.
    
    Args:
        schedule_list: List of schedule entries with JadwalID as key
        identifier: Identifier for the timetable (e.g., room_id, dosen_id, 'All')
        output_dir: Directory to save the timetable HTML file
        title_prefix: Prefix for the timetable title
        course_dict: Optional course dictionary for course names
    
    Returns:
        Path to the generated HTML file or None if failed
    """
    if not schedule_list:
        return None
    
    # Days of the week
    days = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu']
    day_positions = {day: i for i, day in enumerate(days)}
    
    # Color palette for different courses
    color_palette = px.colors.qualitative.Set3
    course_colors = {}
    color_idx = 0
    
    # Create figure
    fig = go.Figure()
    
    # Add vertical grid lines between days
    for i in range(len(days) + 1):
        fig.add_shape(
            type="line",
            x0=i, x1=i,
            y0=7, y1=18,
            line=dict(color="lightgray", width=1),
            layer="below"
        )
    
    # Sort schedules by day and time
    schedule_list_sorted = sorted(schedule_list, key=lambda x: (
        day_positions.get(x[1]['HariNama'], 99),
        x[1]['JamMulai']
    ))
    
    # Calculate max schedules per hour for each day
    max_per_hour = {}
    for day in days:
        max_count = 1
        day_schedules = [(k, v) for k, v in schedule_list_sorted if v['HariNama'] == day]
        
        for hour in range(7, 18):
            count = 0
            for _, entry in day_schedules:
                start_h = _time_to_hour(entry['JamMulai'])
                end_h = _time_to_hour(entry['JamSelesai'])
                if start_h < hour + 1 and end_h > hour:
                    count += 1
            max_count = max(max_count, count)
        
        max_per_hour[day] = max_count
    
    # Assign slot to each schedule (greedy algorithm)
    schedule_slots = {}
    for day in days:
        day_schedules = [(k, v) for k, v in schedule_list_sorted if v['HariNama'] == day]
        occupied_slots = []
        
        for jadwal_id, entry in day_schedules:
            start_h = _time_to_hour(entry['JamMulai'])
            end_h = _time_to_hour(entry['JamSelesai'])
            
            slot = 0
            while True:
                conflict = False
                for occ_start, occ_end, occ_slot in occupied_slots:
                    if occ_slot == slot:
                        if not (end_h <= occ_start or start_h >= occ_end):
                            conflict = True
                            break
                
                if not conflict:
                    break
                slot += 1
            
            occupied_slots.append((start_h, end_h, slot))
            schedule_slots[jadwal_id] = slot
    
    # Render each schedule
    for jadwal_id, entry in schedule_list_sorted:
        if entry['HariNama'] not in day_positions:
            continue
        
        day = entry['HariNama']
        day_pos = day_positions[day]
        start_hour = _time_to_hour(entry['JamMulai'])
        end_hour = _time_to_hour(entry['JamSelesai'])
        
        # Calculate box width and position
        max_schedules = max_per_hour[day]
        col_width = 0.9 / max_schedules
        slot = schedule_slots[jadwal_id]
        
        x0 = day_pos + 0.05 + (slot * col_width)
        x1 = x0 + col_width
        
        # Assign color to course
        mk_kode = entry['MKKode']
        if mk_kode not in course_colors:
            course_colors[mk_kode] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
        
        color = course_colors[mk_kode]
        
        # Get course name from course_dict if available
        course_name = ""
        if course_dict and jadwal_id in course_dict:
            course_name = course_dict[jadwal_id].get('MatakuliahNama', '')
        
        # Create hover text
        hover_text = (
            f"<b>{mk_kode} - {entry['KelasID']}</b><br>"
            f"{course_name}<br>" if course_name else f"<b>{mk_kode} - {entry['KelasID']}</b><br>"
            f"<b>Time:</b> {entry['JamMulai']} - {entry['JamSelesai']}<br>"
            f"<b>Jadwal ID:</b> {jadwal_id}<br>"
            f"<b>Lecturer ID:</b> {entry['DosenID']}<br>"
            f"<b>Room:</b> {entry['RuanganID']}"
        )
        
        # Add rectangle
        fig.add_shape(
            type="rect",
            x0=x0,
            y0=start_hour,
            x1=x1,
            y1=end_hour,
            fillcolor=color,
            line=dict(color="black", width=2),
            layer="below"
        )
        
        center_x = (x0 + x1) / 2
        
        # Adjust font size based on column width
        title_font_size = max(7, int(11 * col_width / 0.9))
        name_font_size = max(6, int(8 * col_width / 0.9))
        time_font_size = max(5, int(7 * col_width / 0.9))
        
        # Add course code annotation
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 - 0.25,
            text=f"<b>{mk_kode}-{entry['KelasID']}</b>",
            showarrow=False,
            font=dict(size=title_font_size, color="black"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add course name (shortened if needed)
        if course_name:
            max_len = int(30 * col_width / 0.9)
            display_name = course_name[:max_len-3] + '...' if len(course_name) > max_len else course_name
            fig.add_annotation(
                x=center_x,
                y=(start_hour + end_hour) / 2 - 0.05,
                text=display_name,
                showarrow=False,
                font=dict(size=name_font_size, color="black"),
                xanchor="center",
                yanchor="middle"
            )
        
        # Add lecturer ID
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 + 0.1,
            text=f"Dosen: {entry['DosenID']}",
            showarrow=False,
            font=dict(size=time_font_size, color="darkblue"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add time
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 + 0.25,
            text=f"{entry['JamMulai']}-{entry['JamSelesai']}",
            showarrow=False,
            font=dict(size=time_font_size, color="gray"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add invisible scatter for hover
        fig.add_trace(go.Scatter(
            x=[center_x],
            y=[(start_hour + end_hour) / 2],
            mode='markers',
            marker=dict(size=15, color=color, opacity=0.01),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=f'<b>Timetable for {title_prefix} {identifier}</b>',
            font=dict(size=20),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=[i + 0.5 for i in range(len(days))],
            ticktext=days,
            range=[-0.1, len(days) - 0.1],
            showgrid=False,
            zeroline=False,
            title=None
        ),
        yaxis=dict(
            tickmode='linear',
            tick0=7,
            dtick=1,
            range=[18, 7],
            showgrid=False,
            zeroline=False,
            title='Time',
            tickformat='%H:00'
        ),
        plot_bgcolor='white',
        width=1400,
        height=800,
        hovermode='closest',
        margin=dict(l=60, r=40, t=80, b=40)
    )
    
    # Save the figure
    output_file = output_dir / f'timetable_{title_prefix.lower().replace(" ", "_")}_{identifier}.html'
    fig.write_html(str(output_file))
    
    return output_file

def generate_timetables(jadwal_dict, output_path, course_dict=None, group_by=None, title_prefix='Schedule'):
    """
    Generate interactive visual timetables from schedule dictionary.
    
    Args:
        jadwal_dict: Dictionary with JadwalID as key and schedule entry as value
                     (format from class_scheduling responses['jadwal'])
        output_path: Path to directory for saving timetable HTML files
        course_dict: Optional course dictionary for course names (from matakuliah.csv)
        group_by: Column to group timetables by:
                  - None: Single timetable with all schedules
                  - 'RuanganID': Timetable per room
                  - 'DosenID': Timetable per lecturer
        title_prefix: Prefix for timetable titles
    
    Returns:
        Number of timetables generated
    
    Examples:
        # Generate single timetable with all schedules
        generate_timetables(responses['jadwal'], output_path, group_by=None, title_prefix='All')
        
        # Generate timetables by room
        generate_timetables(responses['jadwal'], output_path, group_by='RuanganID', title_prefix='Room')
        
        # Generate timetables by lecturer
        generate_timetables(responses['jadwal'], output_path, group_by='DosenID', title_prefix='Dosen')
    """
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    if group_by is None:
        print("GENERATING INTERACTIVE TIMETABLE (All schedules)")
    else:
        print(f"GENERATING INTERACTIVE TIMETABLES (Grouped by {group_by})")
    print("=" * 80)
    
    # Convert dict to list of (key, value) tuples
    schedule_list = list(jadwal_dict.items())
    
    if not schedule_list:
        print("\n[WARNING] No schedules to visualize")
        return 0
    
    # Handle case where group_by is None - generate single timetable
    if group_by is None:
        print("\nGenerating single timetable with all schedules...")
        try:
            result = _create_timetable_html(schedule_list, 'All', output_path, title_prefix, course_dict)
            if result:
                print("\n[OK] Generated 1 interactive timetable")
                print(f"[OK] Saved to: {result}")
                return 1
            else:
                print("\n[ERROR] Failed to generate timetable")
                return 0
        except Exception as e:
            print(f"\n[ERROR] Error generating timetable: {str(e)}")
            return 0
    
    # Group by specified field
    groups = {}
    for jadwal_id, entry in schedule_list:
        group_value = entry.get(group_by)
        if group_value not in groups:
            groups[group_value] = []
        groups[group_value].append((jadwal_id, entry))
    
    print(f"\nFound {len(groups)} unique {group_by} values")
    print("Generating interactive HTML timetables...")
    
    generated_count = 0
    for group_value, group_schedules in sorted(groups.items()):
        try:
            result = _create_timetable_html(group_schedules, group_value, output_path, title_prefix, course_dict)
            if result:
                generated_count += 1
        except Exception as e:
            print(f"  [WARNING] Error processing {group_by} {group_value}: {str(e)}")
    
    print(f"\n[OK] Generated {generated_count} interactive timetables")
    print(f"[OK] Saved to: {output_path}")
    
    return generated_count