"""Object Registry API — Capture, register, and manage dynamic objects for ORB detection."""
import os
import json
import glob
import cv2
import numpy as np
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.state import MissionState

router = APIRouter(prefix="/api/objects", tags=["objects"])

OBJECTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'objects')
os.makedirs(OBJECTS_DIR, exist_ok=True)


class CaptureRequest(BaseModel):
    object_slug: str


class RegisterRequest(BaseModel):
    object_slug: str
    display_name: str


@router.get("/list")
def list_objects():
    """Return all registered objects with metadata."""
    objects = []
    if not os.path.exists(OBJECTS_DIR):
        return {"objects": objects}
    
    for slug in sorted(os.listdir(OBJECTS_DIR)):
        obj_dir = os.path.join(OBJECTS_DIR, slug)
        if not os.path.isdir(obj_dir):
            continue
        
        manifest_path = os.path.join(obj_dir, "manifest.json")
        image_count = len(glob.glob(os.path.join(obj_dir, "capture_*.jpg")))
        
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            manifest["image_count"] = image_count
            manifest["registered"] = True
            objects.append(manifest)
        else:
            objects.append({
                "slug": slug,
                "name": slug.replace("_", " ").title(),
                "image_count": image_count,
                "registered": False,
                "created_at": None
            })
    
    return {"objects": objects}


@router.post("/capture")
def capture_object_image(req: CaptureRequest):
    """Save the current camera frame as a reference image for an object."""
    slug = req.object_slug.lower().replace(" ", "_").replace("-", "_")
    obj_dir = os.path.join(OBJECTS_DIR, slug)
    os.makedirs(obj_dir, exist_ok=True)
    
    # Grab the current frame from the engine
    frame = MissionState.latest_frame
    if frame is None:
        raise HTTPException(status_code=503, detail="Camera not ready — no frame available")
    
    # Count existing captures and save the next one
    existing = glob.glob(os.path.join(obj_dir, "capture_*.jpg"))
    next_num = len(existing) + 1
    filename = f"capture_{next_num}.jpg"
    filepath = os.path.join(obj_dir, filename)
    
    cv2.imwrite(filepath, frame)
    
    return {
        "status": "ok",
        "slug": slug,
        "filename": filename,
        "count": next_num
    }


@router.post("/register")
def register_object(req: RegisterRequest):
    """Finalize registration: run ORB feature extraction and save manifest."""
    slug = req.object_slug.lower().replace(" ", "_").replace("-", "_")
    obj_dir = os.path.join(OBJECTS_DIR, slug)
    
    if not os.path.exists(obj_dir):
        raise HTTPException(status_code=404, detail=f"Object '{slug}' not found. Capture images first.")
    
    images = sorted(glob.glob(os.path.join(obj_dir, "capture_*.jpg")))
    if len(images) < 5:
        raise HTTPException(status_code=400, detail=f"Need at least 5 images, got {len(images)}. Capture more.")
    
    # Run ORB feature extraction
    from app.core.engine import load_dynamic_object
    ref_count = load_dynamic_object(slug)
    
    # Save manifest
    manifest = {
        "slug": slug,
        "name": req.display_name,
        "image_count": len(images),
        "orb_refs_loaded": ref_count,
        "registered": True,
        "created_at": datetime.now().isoformat()
    }
    
    with open(os.path.join(obj_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    
    return {"status": "ok", "slug": slug, "refs_loaded": ref_count}


@router.delete("/delete/{slug}")
def delete_object(slug: str):
    """Remove an object and all its images."""
    import shutil
    obj_dir = os.path.join(OBJECTS_DIR, slug)
    
    if not os.path.exists(obj_dir):
        raise HTTPException(status_code=404, detail=f"Object '{slug}' not found.")
    
    shutil.rmtree(obj_dir)
    
    # Remove from runtime registry
    from app.core.engine import dynamic_object_refs
    dynamic_object_refs.pop(slug, None)
    
    return {"status": "ok", "deleted": slug}
