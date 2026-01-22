# Daftar Hari Default
DEFAULT_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]

# Default Settings Algoritma
DEFAULT_SCHEDULING_SETTINGS = {
    "daftar_hari": DEFAULT_DAYS,
    "waktu_mulai_terawal": "07:00",
    "waktu_selesai_terakhir": "17:00",
    "interval": 60,
    "penalti": {
        "utilisasi_ruangan": 1,
        "jumlah_ruangan": 1,
        "maks_jam_mengajar": 1,
        "preferensi_dosen": 1
    },
    "algorithm": "ALNS",
    "optimization_settings": {
        "num_search_workers": 4,
        "linearization_level": 2,
        "symmetry_level": 2,
        "relative_gap_limit": 0.005,
        "max_time_mins": 10
    },
    "alns_settings":  {
        "max_iterations":  40000,
        "segment_length":  100,
        "reaction_factor":  0.2,
        "target_destroy_size":  2,
        "t_start":  1000,
        "cooling_rate":  0.999,
        "score_best":  15,
        "score_better":  8,
        "score_accept":  3,
        "score_reject":  0,  
        "max_iterations_without_improvement": 10000,
        "diversification_treshold":  100,
        "use_cpsat_for_init_solution":  True
    }
}