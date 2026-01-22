"""
Post-processing script for class scheduling optimization
Converts time slots to actual times and prepares data for database upload
"""
from util import load_data, post_process_schedule, generate_schedule_summary
from pathlib import Path

# Example usage
if __name__ == "__main__":
    
    # Configuration
    INPUT_FILE = 'schedule_solution_test.csv'
    OUTPUT_FILE = 'schedule_solution_processed_test.csv'
    
    # Time configuration
    START_HOUR = 7
    START_MINUTE = 0
    SLOT_DURATION_MINUTES = 60
    
    print("=" * 80)
    print("SCHEDULE POST-PROCESSING")
    print("=" * 80)
    
    # Load input data
    print("\n[1/3] Loading schedule data...")
    df_schedule = load_data(INPUT_FILE)
    
    # Process schedule
    print("\n[2/3] Processing schedule...")
    df_processed = post_process_schedule(
        df_schedule,
        start_hour=START_HOUR,
        start_minute=START_MINUTE,
        slot_duration_minutes=SLOT_DURATION_MINUTES
    )
    
    # Save processed schedule
    output_dir = Path(__file__).resolve().parent.parent / 'data'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / OUTPUT_FILE
    df_processed.to_csv(output_path, index=False)
    print(f"\n✓ Saved processed schedule: {output_path}")
    
    # Generate summary
    print("\n[3/3] Generating summary...")
    generate_schedule_summary(df_processed)
    
    print("\n" + "=" * 80)
    print("POST-PROCESSING COMPLETE")
    print("=" * 80)
