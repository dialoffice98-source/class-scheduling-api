from pathlib import Path
from util import get_db_engine, fetch_jadwal_data, fetch_jadwal_detail, extract_room_capacity, prepare_course_data

# Example usage
if __name__ == "__main__":

    # Configuration
    PRODI_NAMA = 'S1 Teknik Industri'
    TAHUN_NAMA = '2024/2025 Ganjil'
    OUTPUT_DIR = 'data'

    # Exclude Tugas Akhir, Seminar, Praktek Kerja Lapangan, Proyek Akhir from scheduling
    # Specific Issue
    EXCLUDE_CODES = ["TI603057", "TI603059", "TI640303", "TI603150", "TI640307", "TI640306"]

    print("=" * 80)
    print(f"Processing scheduling data for {PRODI_NAMA} - {TAHUN_NAMA}")
    print("=" * 80)
    
    # Create output directory
    output_path = Path(__file__).resolve().parent.parent / OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Connect to database
    print("\n[1/5] Connecting to database...")
    engine = get_db_engine()
    
    # Step 2: Fetch jadwal data
    print("\n[2/5] Fetching jadwal data...")
    df_jadwal = fetch_jadwal_data(engine, PRODI_NAMA, TAHUN_NAMA)
    
    # Step 3: Fetch jadwal_detail data
    print("\n[3/5] Fetching jadwal_detail data...")
    df_detail = fetch_jadwal_detail(engine, PRODI_NAMA, TAHUN_NAMA)
    
    # Apply fixes to df_detail (specific known issues)
    # Give recap so user can reinput data if necessary
    FIX_JADWAL_IDS = {75993: '14:40:00'} 
    for jadwal_id, correct_time in FIX_JADWAL_IDS.items():
        if jadwal_id in df_detail['JadwalID'].values:
            df_detail.loc[df_detail['JadwalID'] == jadwal_id, 'JamSelesai'] = correct_time
            print(f"Applied fix: JadwalID {jadwal_id} -> JamSelesai {correct_time}")
    
    
    # Step 4: Extract room capacity
    print("\n[4/5] Extracting room capacity...")
    kelas_kapasitas = extract_room_capacity(df_jadwal)
    
    # Step 5: Prepare course data with duration
    print("\n[5/5] Preparing course data with duration...")
    grouped_filtered = prepare_course_data(df_jadwal, df_detail, EXCLUDE_CODES)
    

    # IRREGULARITIES HANDLING
    # It's much preferable to fix data collection than to fix it here

    # Drop rows with missing DosenID (marked as -1)
    # Kindly ask user to re-input data if this happens
    before_dropna = len(grouped_filtered)
    grouped_filtered = grouped_filtered[grouped_filtered['dosen_id'] != -1].reset_index(drop=True)
    if before_dropna > len(grouped_filtered):
        print(f"Removed {before_dropna - len(grouped_filtered)} course(s) with missing lecturer ID")
    
    # Filter out courses with durasi_jam = 0 (incomplete schedule data, something is wrong with the input)
    # Kindly ask user to re-input data if this happens
    FILTER_ZERO_DURASI = True 
    if FILTER_ZERO_DURASI:
        before_filter = len(grouped_filtered)
        zero_durasi_courses = grouped_filtered[grouped_filtered['durasi_jam'] == 0]
        if len(zero_durasi_courses) > 0:
            print(f"\nFiltering out courses with durasi_jam = 0:")
            for _, row in zero_durasi_courses.iterrows():
                print(f"  - {row['class_id']}: {row['nama_mk']} (Lecturer: {row['dosen_id']})")
        grouped_filtered = grouped_filtered[grouped_filtered['durasi_jam'] > 0].reset_index(drop=True)
        print(f"Removed {before_filter - len(grouped_filtered)} course(s) with no schedule data")
    
    # Save results
    print("\n" + "=" * 80)
    print("Saving results...")
    
    # Save room capacity
    room_output = output_path / f'{PRODI_NAMA.replace(" ", "_").lower()}_kelas_kapasitas_{TAHUN_NAMA.replace("/", "_").replace(" ", "_").lower()}.csv'
    kelas_kapasitas.to_csv(room_output, index=False)
    print(f"✓ Saved room capacity: {room_output}")
    
    # Reset grouped_filtered index after all filtering
    grouped_filtered = grouped_filtered.reset_index(drop=True)
    
    # Save course data
    course_output = output_path / f'{PRODI_NAMA.replace(" ", "_").lower()}_courses_{TAHUN_NAMA.replace("/", "_").replace(" ", "_").lower()}.csv'
    grouped_filtered.to_csv(course_output, index=False)
    print(f"✓ Saved course data: {course_output}")
    
    print("=" * 80)
    print("Processing complete!")
    print(f"Total rooms: {len(kelas_kapasitas)}")
    print(f"Total courses: {len(grouped_filtered)}")
    print("=" * 80)
    
    # Display summary
    print("\n📊 Summary Statistics:")
    print(f"  - Unique rooms: {len(kelas_kapasitas)}")
    print(f"  - Unique courses: {len(grouped_filtered)}")
    print(f"  - Unique lecturers: {grouped_filtered['dosen_id'].nunique()}")
