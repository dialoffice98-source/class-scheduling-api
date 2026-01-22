"""Utility functions for class scheduling optimization."""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime,  timedelta, time

def load_data(path):
    """Load data from data folder"""
    data_dir = Path(__file__).parent.parent / "data"
    
    file = data_dir / path
    
    print(f"Loading data from: ../data/{file.name}")

    df = pd.read_csv(file)
    
    print(f"\n✓ Loaded {len(df)} records")
    
    return df

#===============================PRE PROCESSING=================================
def get_db_engine():
    """
    Connects to the database using environment variables.
    
    Returns:
        engine: SQLAlchemy engine object
    """
    # Check .env file
    if not os.getenv("DB_USERNAME"):
        env_path = Path(__file__).resolve().parent.parent / '.env'
        print(f"Loading environment from: {env_path}")
        load_dotenv(dotenv_path=env_path)

    # Create the Connection URL for PostgreSQL
    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )

    # Create and return the engine
    engine = create_engine(connection_url, echo=False)
    return engine


def fetch_jadwal_data(engine, prodi_nama, tahun_nama):
    """
    Fetch jadwal data for a specific program and academic year.
    
    Args:
        engine: SQLAlchemy engine
        prodi_nama: Program name
        tahun_nama: Academic year
    
    Returns:
        df: DataFrame with jadwal data
    """
    query = f"""
    SELECT * FROM public.jadwal 
    WHERE "ProdiNama" = '{prodi_nama}' 
    AND "TahunNama" = '{tahun_nama}'
    """
    df = pd.read_sql_query(query, engine)
    print(f"Fetched {len(df)} jadwal records")
    return df


def fetch_jadwal_detail(engine, prodi_nama, tahun_nama):
    """
    Fetch jadwal_detail data for a specific program and academic year.
    
    Args:
        engine: SQLAlchemy engine
        prodi_nama: Program name
        tahun_nama: Academic year
    
    Returns:
        df_detail: DataFrame with jadwal_detail data
    """
    query = f"""
    SELECT * FROM public.jadwal_detail
    WHERE "JadwalID" IN (
        SELECT "ID" FROM public.jadwal 
        WHERE "ProdiNama" = '{prodi_nama}' 
        AND "TahunNama" = '{tahun_nama}'
    )
    """
    df_detail = pd.read_sql_query(query, engine)
    print(f"Fetched {len(df_detail)} jadwal_detail records")
    return df_detail


def extract_room_capacity(df_jadwal):
    """
    Extract room capacity information from jadwal data.
    Groups by KelasID and takes the maximum Kapasitas value, rounded up to nearest 10. (For now)
    
    Args:
        df_jadwal: DataFrame with jadwal data
    
    Returns:
        kelas_kapasitas: DataFrame with RuanganID and Max_Kapasitas
    """
    kelas_kapasitas = df_jadwal.groupby('KelasID')['Kapasitas'].max().reset_index()
    kelas_kapasitas.columns = ['ruangan_id', 'kapasitas']
    
    # Round up to nearest 10
    kelas_kapasitas['kapasitas'] = (np.ceil(kelas_kapasitas['kapasitas'] / 10) * 10).astype(int)
    kelas_kapasitas = kelas_kapasitas.sort_values('ruangan_id').reset_index(drop=True)
    
    print(f"Extracted capacity for {len(kelas_kapasitas)} unique rooms")
    return kelas_kapasitas


def calculate_duration_from_detail(df_detail):
    """
    Calculate course duration from jadwal_detail data.
    
    Args:
        df_detail: DataFrame with jadwal_detail data
    
    Returns:
        durasi_per_jadwal: DataFrame with JadwalID and total duration
    """
    # Calculate duration from jadwal_detail
    df_detail_clean = df_detail[
        df_detail['JamMulai'].notna() & 
        df_detail['JamSelesai'].notna()
    ].copy()
    
    # Parse times and calculate duration in hours
    df_detail_clean['start_time'] = pd.to_datetime(df_detail_clean['JamMulai'], format='%H:%M:%S')
    df_detail_clean['end_time'] = pd.to_datetime(df_detail_clean['JamSelesai'], format='%H:%M:%S')
    df_detail_clean['duration_hours'] = (df_detail_clean['end_time'] - df_detail_clean['start_time']).dt.total_seconds() / 3600
    df_detail_clean['session_durasi'] = np.ceil(df_detail_clean['duration_hours']).astype(int)
    
    # Get unique weekly sessions (remove duplicate days within the same week)
    df_detail_unique = df_detail_clean.drop_duplicates(subset=['JadwalID', 'HariNama', 'JamMulai', 'JamSelesai'])
    
    # Aggregate duration per JadwalID (sum of unique weekly sessions)
    durasi_per_jadwal = df_detail_unique.groupby('JadwalID')['session_durasi'].sum().reset_index()
    durasi_per_jadwal.columns = ['JadwalID', 'durasi']
    
    return durasi_per_jadwal


def prepare_course_data(df_jadwal, df_detail, exclude_codes):
    """
    Prepare course and lecturer data from jadwal with class_id naming.
    Removes specified course codes and filters out incomplete data.
    Adds duration information from jadwal_detail.
    
    Args:
        df_jadwal: DataFrame with jadwal data
        df_detail: DataFrame with jadwal_detail data
        exclude_codes: List of MKKode to exclude
    
    Returns:
        grouped_filtered: DataFrame with processed course data including class_id
    """
    # Calculate duration
    durasi_per_jadwal = calculate_duration_from_detail(df_detail)
    
    # Select required columns from jadwal
    grouped = df_jadwal[['ID', 'MKKode', 'MatakuliahNama', 'DosenID', 'Kapasitas']].copy()
    
    # Merge with duration data
    grouped = grouped.merge(durasi_per_jadwal, left_on='ID', right_on='JadwalID', how='left')
    grouped['durasi'] = grouped['durasi'].fillna(0).astype(int)
    grouped = grouped.drop('JadwalID', axis=1)
    
    # Select only required columns for final output
    grouped = grouped[['ID', 'MKKode', 'MatakuliahNama', 'DosenID', 'Kapasitas', 'durasi']].copy()
    
    # Convert DosenID to nullable integer
    grouped['DosenID'] = pd.to_numeric(grouped['DosenID'], errors='coerce').astype('Int64')
    
    # Normalize MKKode by removing whitespace
    grouped['MKKode'] = grouped['MKKode'].astype(str).str.split().str.join('')
    
    # Remove excluded courses if any
    if exclude_codes:
        grouped_filtered = grouped[~grouped['MKKode'].isin(exclude_codes)].reset_index(drop=True)
        print(f"Excluded {len(exclude_codes)} course codes")
    else:
        grouped_filtered = grouped.copy()
        print("No courses excluded")
    
    # Fill missing DosenID with -1 (will be dropped in main block)
    grouped_filtered['DosenID'] = grouped_filtered['DosenID'].fillna(-1).astype(int)

    # Add class_id with K0x-J0x suffixes BEFORE dropping ID
    # K0x: Different lecturers teaching the same course
    grouped_filtered['K_Count'] = grouped_filtered.groupby('MKKode')['DosenID'].transform(lambda x: pd.factorize(x)[0] + 1)
    # J0x: Multiple sections of the same course-lecturer combination
    grouped_filtered['J_Count'] = grouped_filtered.groupby(['MKKode', 'DosenID']).cumcount() + 1
    # Create class_id
    grouped_filtered['class_id'] = grouped_filtered.apply(
        lambda row: f"{row['MKKode']}-K{row['K_Count']:02d}-J{row['J_Count']:02d}", 
        axis=1
    )
    # Drop temporary columns
    grouped_filtered = grouped_filtered.drop(['K_Count', 'J_Count'], axis=1)
    
    # Now drop ID column after generating class_id
    grouped_filtered = grouped_filtered.drop('ID', axis=1)
    
    # Remove duplicates (if any remain after class_id generation)
    grouped_filtered = grouped_filtered.drop_duplicates().reset_index(drop=True)
    
    # Rename columns
    grouped_filtered = grouped_filtered.rename(columns={
        'MKKode': 'kode_mk',
        'MatakuliahNama': 'nama_mk',
        'DosenID': 'dosen_id',
        'Kapasitas': 'jumlah_mhs',
        'durasi': 'durasi_jam'
    })
    
    # Reorder columns to put class_id first
    grouped_filtered = grouped_filtered[['class_id', 'kode_mk', 'nama_mk', 'dosen_id', 'jumlah_mhs', 'durasi_jam']]
    
    # Sort for consistency
    grouped_filtered = grouped_filtered.sort_values(['kode_mk', 'dosen_id', 'class_id']).reset_index(drop=True)
    
    print(f"Prepared {len(grouped_filtered)} course records")
    return grouped_filtered

def convert_slot_to_time(slot_number, start_hour=7, start_minute=0, slot_duration_minutes=50):
    """
    Convert slot number to actual time.
    
    Args:
        slot_number: Integer slot number (0, 1, 2, ...)
        start_hour: Starting hour (default 7 for 7:00 AM)
        start_minute: Starting minute (default 0)
        slot_duration_minutes: Duration of each slot in minutes (default 50)
    
    Returns:
        time: Time object representing the slot time
    """
    total_minutes = start_hour * 60 + start_minute + (slot_number * slot_duration_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return time(hours, minutes)

#================================POST PROCESSING=================================
def format_time(time_obj):
    """
    Format time object to HH:MM:SS string.
    
    Args:
        time_obj: time object
    
    Returns:
        str: Formatted time string (HH:MM:SS)
    """
    return time_obj.strftime('%H:%M:%S')

def post_process_schedule(df, start_hour=7, start_minute=0, slot_duration_minutes=50):
    """
    Post-process schedule solution by converting slot numbers to actual times.
    
    Args:
        df: Input DataFrame with schedule solution (slot numbers)
        start_hour: Starting hour (default 7 for 7:00 AM)
        start_minute: Starting minute (default 0)
        slot_duration_minutes: Duration of each slot in minutes (default 50)
    
    Returns:
        df_processed: Processed DataFrame with actual times
    """
    # Make a copy to avoid modifying the original
    df_processed = df.copy()
    
    print(f"Processing {len(df_processed)} scheduled classes")
    
    # Convert slot numbers to actual times
    print("\nConverting time slots to actual times...")
    print(f"  Start time: {start_hour:02d}:{start_minute:02d}")
    print(f"  Slot duration: {slot_duration_minutes} minutes")
    
    # Convert waktu_mulai (start time slot) to actual time
    df_processed['waktu_mulai_time'] = df_processed['waktu_mulai'].apply(
        lambda x: convert_slot_to_time(x, start_hour, start_minute, slot_duration_minutes)
    )
    df_processed['waktu_mulai'] = df_processed['waktu_mulai_time'].apply(format_time)
    
    # Convert waktu_selesai (end time slot) to actual time
    df_processed['waktu_selesai_time'] = df_processed['waktu_selesai'].apply(
        lambda x: convert_slot_to_time(x, start_hour, start_minute, slot_duration_minutes)
    )
    df_processed['waktu_selesai'] = df_processed['waktu_selesai_time'].apply(format_time)
    
    # Drop temporary time columns
    df_processed = df_processed.drop(['waktu_mulai_time', 'waktu_selesai_time'], axis=1)
    
    # Extract kelas (K0x) from class_id
    # class_id format: COURSE-K0x-J0x
    df_processed['kelas'] = df_processed['class_id'].str.extract(r'-(K\d+)-')[0]
    
    # Select only relevant columns for output
    # Include kode_mk and nama_mk if they exist in the dataframe
    column_order = ['class_id']
    if 'kode_mk' in df_processed.columns:
        column_order.append('kode_mk')
    if 'nama_mk' in df_processed.columns:
        column_order.append('nama_mk')
    
    column_order.append('kelas')
    
    column_order.extend([
        'dosen_id',
        'ruangan_id',
        'hari_nama',
        'waktu_mulai',
        'waktu_selesai'
    ])
    
    # Only select columns that exist in the dataframe
    column_order = [col for col in column_order if col in df_processed.columns]
    df_processed = df_processed[column_order]
    
    return df_processed

def generate_schedule_summary(df):
    """
    Generate summary statistics for the processed schedule.
    
    Args:
        df: Processed schedule DataFrame
    """
    print("\n" + "=" * 80)
    print("SCHEDULE SUMMARY")
    print("=" * 80)
    
    print(f"\n📊 Overall Statistics:")
    print(f"  - Total scheduled classes: {len(df)}")
    print(f"  - Unique courses: {df['class_id'].nunique()}")
    print(f"  - Unique lecturers: {df['dosen_id'].nunique()}")
    print(f"  - Unique rooms: {df['ruangan_id'].nunique()}")
    
    print(f"\n📅 Schedule by Day:")
    day_counts = df['hari_nama'].value_counts()
    for day, count in day_counts.items():
        print(f"  - {day}: {count} classes")
    
    print(f"\n🏫 Room Utilization:")
    room_usage = df.groupby('ruangan_id').size().sort_values(ascending=False)
    print(f"  - Most used room: {room_usage.index[0]} ({room_usage.iloc[0]} classes)")
    print(f"  - Average classes per room: {len(df) / df['ruangan_id'].nunique():.2f}")
    
    print(f"\n👨‍🏫 Lecturer Workload:")
    lecturer_load = df.groupby('dosen_id').size().sort_values(ascending=False)
    print(f"  - Max classes per lecturer: {lecturer_load.iloc[0]}")
    print(f"  - Average classes per lecturer: {len(df) / df['dosen_id'].nunique():.2f}")
    
    print(f"\n⏰ Time Distribution:")
    time_slots = df.groupby(['hari_nama', 'waktu_mulai']).size().reset_index(name='count')
    busiest_slot = time_slots.loc[time_slots['count'].idxmax()]
    print(f"  - Busiest time slot: {busiest_slot['hari_nama']} at {busiest_slot['waktu_mulai']} ({busiest_slot['count']} classes)")
    
    print("=" * 80)

# =================================GENERATE TIMETABLES=================================
def parse_time(time_str):
    """Parse time string to datetime object."""
    return datetime.strptime(time_str, '%H:%M:%S')


def time_to_hour(time_str):
    """Convert time string to hours as float (e.g., 09:30:00 -> 9.5)."""
    dt = parse_time(time_str)
    return dt.hour + dt.minute / 60.0


def create_timetable_from_df(df, identifier, output_dir, title_prefix='Room'):
    """
    Create a visual timetable from a dataframe, handling overlapping schedules.
    
    Args:
        df: DataFrame containing schedule data
        identifier: Identifier for the timetable (e.g., room_id, dosen_id, 'All')
        output_dir: Directory to save the timetable HTML file
        title_prefix: Prefix for the timetable title (default: 'Room')
    """
    # Skip empty schedules
    if len(df) == 0:
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
    df_sorted = df.sort_values(['hari_nama', 'waktu_mulai', 'waktu_selesai'])
    
    # Calculate max schedules per hour for each day
    max_per_hour = {}
    for day in days:
        max_count = 1
        day_df = df_sorted[df_sorted['hari_nama'] == day]
        
        # Check each hour from 7 to 18
        for hour in range(7, 18):
            # Count schedules that include this hour
            count = 0
            for _, row in day_df.iterrows():
                start_h = time_to_hour(row['waktu_mulai'])
                end_h = time_to_hour(row['waktu_selesai'])
                # A schedule includes this hour if it starts before hour+1 and ends after hour
                if start_h < hour + 1 and end_h > hour:
                    count += 1
            max_count = max(max_count, count)
        
        max_per_hour[day] = max_count
    
    # Assign slot to each schedule (greedy algorithm)
    schedule_slots = {}
    for day in days:
        day_df = df_sorted[df_sorted['hari_nama'] == day]
        occupied_slots = []  # List of (start_hour, end_hour, slot_number)
        
        for _, row in day_df.iterrows():
            start_h = time_to_hour(row['waktu_mulai'])
            end_h = time_to_hour(row['waktu_selesai'])
            
            # Find the first available slot
            slot = 0
            while True:
                # Check if this slot is occupied by any overlapping schedule
                conflict = False
                for occ_start, occ_end, occ_slot in occupied_slots:
                    if occ_slot == slot:
                        # Check if times overlap
                        if not (end_h <= occ_start or start_h >= occ_end):
                            conflict = True
                            break
                
                if not conflict:
                    break
                slot += 1
            
            occupied_slots.append((start_h, end_h, slot))
            schedule_slots[row['class_id']] = slot
    
    # Render each schedule
    for _, row in df_sorted.iterrows():
        if row['hari_nama'] not in day_positions:
            continue
        
        day = row['hari_nama']
        day_pos = day_positions[day]
        start_hour = time_to_hour(row['waktu_mulai'])
        end_hour = time_to_hour(row['waktu_selesai'])
        
        # Calculate box width and position
        max_schedules = max_per_hour[day]
        col_width = 0.9 / max_schedules
        slot = schedule_slots[row['class_id']]
        
        # Left-aligned positioning
        x0 = day_pos + 0.05 + (slot * col_width)
        x1 = x0 + col_width
        
        # Assign color to course
        if row['kode_mk'] not in course_colors:
            course_colors[row['kode_mk']] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
        
        color = course_colors[row['kode_mk']]
        
        # Create hover text
        hover_text = (
            f"<b>{row['kode_mk']} - {row['kelas']}</b><br>"
            f"{row['nama_mk']}<br>"
            f"<b>Time:</b> {row['waktu_mulai'][:5]} - {row['waktu_selesai'][:5]}<br>"
            f"<b>Class ID:</b> {row['class_id']}<br>"
            f"<b>Lecturer ID:</b> {row['dosen_id']}<br>"
            f"<b>Room:</b> {row['ruangan_id']}"
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
        
        # Calculate center x position for annotations
        center_x = (x0 + x1) / 2
        
        # Adjust font size based on column width
        title_font_size = max(7, int(11 * col_width / 0.9))
        name_font_size = max(6, int(8 * col_width / 0.9))
        time_font_size = max(5, int(7 * col_width / 0.9))
        
        # Add text annotation (course code with class)
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 - 0.25,
            text=f"<b>{row['kode_mk']}-{row['kelas']}</b>",
            showarrow=False,
            font=dict(size=title_font_size, color="black"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add course name (shortened if needed)
        course_name = row['nama_mk']
        max_len = int(30 * col_width / 0.9)
        if len(course_name) > max_len:
            course_name = course_name[:max_len-3] + '...'
        
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 - 0.05,
            text=course_name,
            showarrow=False,
            font=dict(size=name_font_size, color="black"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add lecturer ID
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 + 0.1,
            text=f"Dosen: {row['dosen_id']}",
            showarrow=False,
            font=dict(size=time_font_size, color="darkblue"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add time
        time_text = f"{row['waktu_mulai'][:5]}-{row['waktu_selesai'][:5]}"
        fig.add_annotation(
            x=center_x,
            y=(start_hour + end_hour) / 2 + 0.25,
            text=time_text,
            showarrow=False,
            font=dict(size=time_font_size, color="gray"),
            xanchor="center",
            yanchor="middle"
        )
        
        # Add invisible scatter trace for hover
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
            tickvals=[i + 0.5 for i in range(len(days))],  # Center ticks in each column
            ticktext=days,
            range=[-0.1, len(days) - 0.1],
            showgrid=False,  # Disable default grid, using custom lines instead
            zeroline=False,
            title=None
        ),
        yaxis=dict(
            tickmode='linear',
            tick0=7,
            dtick=1,
            range=[18, 7],  # Inverted range (morning at top)
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
    fig.write_html(output_file)
    
    return output_file


def filter_schedule(df, **filters):
    """
    Filter schedule DataFrame based on specified criteria.
    
    Args:
        df: DataFrame containing the complete schedule
        **filters: Keyword arguments for filtering. Supported filters:
            - ruangan_id: Single value or list of room IDs
            - dosen_id: Single value or list of lecturer IDs
            - kode_mk: Single value or list of course codes
            - kelas: Single value or list of class names
            - hari_nama: Single value or list of day names
            - Any other column name in the DataFrame
    
    Returns:
        Filtered DataFrame
    
    Examples:
        # Filter by single room
        filter_schedule(df, ruangan_id=359)
        
        # Filter by multiple rooms
        filter_schedule(df, ruangan_id=[359, 360])
        
        # Filter by lecturer and course
        filter_schedule(df, dosen_id=856, kode_mk='TI601036')
        
        # Filter by course and class combinations
        filter_schedule(df, kode_mk='TI601036', kelas=['K01', 'K02'])
    """
    filtered_df = df.copy()
    
    for column, value in filters.items():
        if column not in filtered_df.columns:
            continue
        
        # Handle both single values and lists
        if isinstance(value, (list, tuple)):
            filtered_df = filtered_df[filtered_df[column].isin(value)]
        else:
            filtered_df = filtered_df[filtered_df[column] == value]
    
    return filtered_df


def filter_classes(df, class_combinations):
    """
    Filter schedule DataFrame for specific combinations of course code and class.
    
    Args:
        df: DataFrame containing the complete schedule
        class_combinations: List of tuples (kode_mk, kelas) or list of dicts with 'kode_mk' and 'kelas' keys
    
    Returns:
        Filtered DataFrame
    
    Examples:
        # Filter specific class combinations using tuples
        filter_classes(df, [('TI601036', 'K01'), ('TI601004', 'K02')])
        
        # Filter specific class combinations using dicts
        filter_classes(df, [
            {'kode_mk': 'TI601036', 'kelas': 'K01'},
            {'kode_mk': 'TI601004', 'kelas': 'K02'}
        ])
    """
    if not class_combinations:
        return df.copy()
    
    # Convert to list of tuples if dict format provided
    if isinstance(class_combinations[0], dict):
        class_combinations = [(c['kode_mk'], c['kelas']) for c in class_combinations]
    
    # Create a boolean mask for matching rows
    mask = pd.Series([False] * len(df), index=df.index)
    
    for kode_mk, kelas in class_combinations:
        mask |= (df['kode_mk'] == kode_mk) & (df['kelas'] == kelas)
    
    return df[mask].copy()


def generate_all_timetables(df, output_path=None, group_by=None, title_prefix='Schedule'):
    """
    Generate interactive visual timetables from a schedule DataFrame.
    
    Args:
        df: DataFrame containing the complete schedule
        output_path: Path object for the directory to save timetable HTML files (optional, defaults to current directory)
        group_by: Column name to group timetables by (default: None - shows all schedules in one timetable)
                  Common options: 'ruangan_id', 'dosen_id', 'kode_mk', 'kelas', or None
        title_prefix: Prefix for timetable titles (default: 'Schedule')
    
    Returns:
        Number of timetables generated
    
    Examples:
        # Generate single timetable with all schedules
        generate_all_timetables(df, output_path, group_by=None, title_prefix='All')
        
        # Generate timetables by room
        generate_all_timetables(df, output_path, group_by='ruangan_id', title_prefix='Room')
        
        # Generate timetables by lecturer
        generate_all_timetables(df, output_path, group_by='dosen_id', title_prefix='Lecturer')
        
        # Generate timetables by course
        generate_all_timetables(df, output_path, group_by='kode_mk', title_prefix='Course')
    """
    # Set default output path to current directory if not provided
    if output_path is None:
        output_path = Path.cwd()
    
    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    if group_by is None:
        print("GENERATING INTERACTIVE TIMETABLE (All schedules)")
    else:
        print(f"GENERATING INTERACTIVE TIMETABLES (Grouped by {group_by})")
    print("=" * 80)
    
    # Handle case where group_by is None - generate single timetable with all data
    if group_by is None:
        print("\nGenerating single timetable with all schedules...")
        try:
            result = create_timetable_from_df(df, 'All', output_path, title_prefix)
            if result:
                print(f"\n[OK] Generated 1 interactive timetable")
                print(f"\n[OK] HTML timetable saved to: {output_path}")
                print("  [TIP] Open the HTML file in a web browser to view the interactive timetable")
                print("\n" + "=" * 80)
                print("TIMETABLE GENERATION COMPLETE")
                print("=" * 80)
                return 1
            else:
                print("\n[ERROR] Failed to generate timetable (empty schedule)")
                return 0
        except Exception as e:
            print(f"\n[ERROR] Error generating timetable: {str(e)}")
            return 0
    
    # Check if group_by column exists
    if group_by not in df.columns:
        print(f"\n[ERROR] Error: Column '{group_by}' not found in DataFrame")
        print(f"Available columns: {', '.join(df.columns)}")
        return 0
    
    # Get unique values for grouping
    groups = sorted(df[group_by].unique())
    print(f"\nFound {len(groups)} {group_by} values in the schedule")
    print("\nGenerating interactive HTML timetables...")
    
    # Generate timetables for each group
    generated_count = 0
    skipped_count = 0
    
    for group_value in groups:
        group_df = df[df[group_by] == group_value].copy()
        
        try:
            result = create_timetable_from_df(group_df, group_value, output_path, title_prefix)
            if result:
                generated_count += 1
                if generated_count % 5 == 0:
                    print(f"  Generated {generated_count} timetables...")
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  ⚠ Error processing {group_by} {group_value}: {str(e)}")
            skipped_count += 1
    
    print(f"\n[OK] Generated {generated_count} interactive timetables")
    if skipped_count > 0:
        print(f"  Skipped {skipped_count} empty schedules")
    
    print(f"\n[OK] HTML timetables saved to: {output_path}")
    print("  [TIP] Open the HTML files in a web browser to view interactive timetables")
    
    print("\n" + "=" * 80)
    print("TIMETABLE GENERATION COMPLETE")
    print("=" * 80)
    
    return generated_count

if __name__ == "__main__":
    pass