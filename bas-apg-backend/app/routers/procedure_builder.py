"""Procedure Builder API — Create, list, select, and delete experimental procedures."""
import os
import json
import glob
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.core.state import MissionState

router = APIRouter(prefix="/api/procedures", tags=["procedures"])

PROCEDURES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'procedures')
os.makedirs(PROCEDURES_DIR, exist_ok=True)


class StepInput(BaseModel):
    action: str  # DETECT, OPEN, COMPLETE
    object: str  # object slug
    description: str
    audio_prompt: str


class CreateProcedureRequest(BaseModel):
    name: str
    steps: List[StepInput]


class SelectProcedureRequest(BaseModel):
    procedure_file: str


@router.get("/list")
def list_procedures():
    """Return all available procedure files."""
    procedures = []
    for filepath in sorted(glob.glob(os.path.join(PROCEDURES_DIR, "*.json"))):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            procedures.append({
                "filename": os.path.basename(filepath),
                "id": data.get("id", ""),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "step_count": len(data.get("steps", [])),
                "objects": data.get("objects", []),
                "selected": MissionState.selected_procedure.endswith(os.path.basename(filepath))
            })
        except Exception:
            continue
    
    return {"procedures": procedures}


@router.post("/create")
def create_procedure(req: CreateProcedureRequest):
    """Create a new procedure JSON from a list of steps."""
    slug = req.name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{slug}.json"
    filepath = os.path.join(PROCEDURES_DIR, filename)
    
    # Collect all unique objects
    all_objects = list(set(step.object for step in req.steps))
    if "procedure" not in all_objects:
        all_objects.append("procedure")
    if "hand" not in all_objects:
        all_objects.append("hand")
    
    # Build steps in the same format as red_yellow_box_experiment.json
    steps = []
    for i, step in enumerate(req.steps):
        step_id = f"S{i + 2:02d}"
        next_step = f"S{i + 3:02d}" if i < len(req.steps) - 1 else None
        
        steps.append({
            "step_id": step_id,
            "action": step.action.upper(),
            "object": step.object,
            "description": step.description,
            "audio_prompt": step.audio_prompt,
            "timeout_seconds": 60,
            "next_step": next_step,
            "required_evidence": [],
            "confidence_threshold": 0.50,
            "recovery_options": ["voice_prompt"]
        })
    
    # Always add a COMPLETE step at the end if not present
    if not steps or steps[-1]["action"] != "COMPLETE":
        step_id = f"S{len(steps) + 2:02d}"
        steps.append({
            "step_id": step_id,
            "action": "COMPLETE",
            "object": "procedure",
            "description": "Procedure Complete.",
            "audio_prompt": "Procedure complete. All steps verified.",
            "timeout_seconds": 60,
            "next_step": None,
            "required_evidence": [],
            "confidence_threshold": 0.50,
            "recovery_options": []
        })
    
    procedure = {
        "id": slug,
        "name": req.name,
        "version": "1.0-custom",
        "description": f"Custom experiment: {req.name}",
        "objects": all_objects,
        "steps": steps
    }
    
    with open(filepath, "w") as f:
        json.dump(procedure, f, indent=2)
    
    return {
        "status": "ok",
        "filename": filename,
        "step_count": len(steps),
        "objects": all_objects
    }


@router.post("/select")
def select_procedure(req: SelectProcedureRequest):
    """Set which procedure the engine should load on next FSM reset."""
    filepath = os.path.join(PROCEDURES_DIR, req.procedure_file)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Procedure '{req.procedure_file}' not found.")
    
    MissionState.selected_procedure = f"data/procedures/{req.procedure_file}"
    
    return {"status": "ok", "selected": req.procedure_file}


@router.delete("/delete/{filename}")
def delete_procedure(filename: str):
    """Remove a custom procedure. Cannot delete the default."""
    if filename == "red_yellow_box_experiment.json":
        raise HTTPException(status_code=403, detail="Cannot delete the default experiment.")
    
    filepath = os.path.join(PROCEDURES_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Procedure '{filename}' not found.")
    
    os.remove(filepath)
    
    # If this was the selected procedure, reset to default
    if MissionState.selected_procedure.endswith(filename):
        MissionState.selected_procedure = "data/procedures/red_yellow_box_experiment.json"
    
    return {"status": "ok", "deleted": filename}
