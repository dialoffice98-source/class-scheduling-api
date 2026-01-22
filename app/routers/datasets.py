from fastapi import APIRouter, HTTPException, UploadFile, File
from app.schemas.dataset import DatasetCreate, DatasetResponse
from app.core.settings_api import DEFAULT_SCHEDULING_SETTINGS, DEFAULT_DAYS
from app.db.datasets import create_dataset, get_dataset, list_datasets
import pandas as pd
import io
import ast
import copy
from typing import Dict, Any

router = APIRouter(prefix="/datasets", tags=["Datasets"])

def parse_schedule_list(val):
    """Helper untuk mengubah string list (misal: "['07:00', '08:00']") menjadi list python asli."""
    if pd.isna(val) or val == "" or val == "[]":
        return []
    try:
        # Jika formatnya string python list
        return ast.literal_eval(str(val))
    except (ValueError, SyntaxError):
        return []

def parse_excel_to_payload(filename: str, content: bytes) -> DatasetCreate:
    """Membaca file Excel dan mengubahnya menjadi schema DatasetCreate."""
    
    # Load Excel file dari memory
    xls = pd.ExcelFile(io.BytesIO(content))
    
    # 1. Parse Sheet "Matakuliah" -> course_dict
    df_mk = pd.read_excel(xls, "Matakuliah")
    course_dict = {}
    for _, row in df_mk.iterrows():
        # Pastikan data numerik tipe int (seperti DosenID, SesiID, dll)
        mk_data = {
            "MKKode": str(row["MKKode"]),
            "MatakuliahNama": str(row["MatakuliahNama"]),
            "KelasID": str(row["KelasID"]),
            "SesiID": int(row["SesiID"]),
            "DosenID": str(row["DosenID"]), # Gunakan string untuk konsistensi ID
            "DosenNama": str(row["DosenNama"]),
            "KapasitasKelas": int(row["KapasitasKelas"]),
            "DurasiJam": int(row["DurasiJam"]),
            "PaketID": int(row.get("PaketID", 0)),
            "PaketNama": str(row.get("PaketNama", "Umum"))
        }
        course_dict[str(row["JadwalID"])] = mk_data

    # 2. Parse Sheet "Ruangan" -> room_dict
    df_room = pd.read_excel(xls, "Ruangan")
    room_dict = {}
    for _, row in df_room.iterrows():
        room_data = {
            "RuanganNama": str(row["RuanganNama"]),
            "KapasitasRuangan": int(row["KapasitasRuangan"])
        }
        room_dict[str(row["RuanganID"])] = room_data

    # 3. Parse Preferensi & Ketidaktersediaan Dosen
    # Format kolom: DosenID, TahunNama, Senin, Selasa, Rabu, Kamis, Jumat
    days_columns = DEFAULT_DAYS
    
    def parse_dosen_sheet(sheet_name):
        data_dict = {}
        if sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name)
            for _, row in df.iterrows():
                dosen_id = str(row["DosenID"])
                data_dict[dosen_id] = {}
                for day in days_columns:
                    if day in row:
                        data_dict[dosen_id][day] = parse_schedule_list(row[day])
                    else:
                        data_dict[dosen_id][day] = []
        return data_dict

    faculty_preference = parse_dosen_sheet("Preferensi Dosen")
    faculty_unavailability = parse_dosen_sheet("Ketidaktersediaan Dosen")

    # 4. Settings Default (Sesuai request)
    settings = copy.deepcopy(DEFAULT_SCHEDULING_SETTINGS)

    return DatasetCreate(
        name=filename,
        course_dict=course_dict,
        room_dict=room_dict,
        faculty_preference_dict=faculty_preference,
        faculty_unavailability_dict=faculty_unavailability,
        settings=settings,
        quick_scheduling=False
    )

@router.post("/upload", response_model=dict)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload file Excel (.xlsx) berisi data penjadwalan.
    File harus memiliki sheet: 'Matakuliah', 'Ruangan', 'Preferensi Dosen', 'Ketidaktersediaan Dosen'.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "File harus berformat Excel (.xlsx)")

    try:
        content = await file.read()
        dataset_payload = parse_excel_to_payload(file.filename, content)
        
        # Simpan ke Database
        # .dict() deprecated di Pydantic v2, gunakan .model_dump() jika v2, atau .dict() jika v1
        # Menggunakan .dict() agar aman sesuai kode lama
        dataset_id = await create_dataset(dataset_payload.dict())
        
        return {
            "message": "Dataset uploaded and processed successfully",
            "dataset_id": dataset_id,
            "filename": file.filename
        }
        
    except ValueError as e:
        raise HTTPException(400, f"Error parsing Excel data: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Internal Server Error: {str(e)}")

@router.post("", response_model=dict)
async def create(payload: DatasetCreate):
    # .dict() deprecated di Pydantic v2, gunakan .model_dump() jika pakai v2
    # Jika masih v1, .dict() aman.
    dataset_id = await create_dataset(payload.dict())
    return {"dataset_id": dataset_id}

@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get(dataset_id: str):
    data = await get_dataset(dataset_id)
    if not data:
        raise HTTPException(404, "Dataset not found")

    return {
        "id": str(data["_id"]),
        **{k: v for k, v in data.items() if k not in ["_id"]}
    }

@router.get("", response_model=list[DatasetResponse])
async def get_all():
    datasets = await list_datasets()
    # Convert ObjectId to string for response
    results = []
    for d in datasets:
        d["id"] = str(d["_id"])
            
        results.append(d)
    return results