"""
BAS-APG — Digital Twin Visualizer (Blender)

Earth-side script for Abhijeet Tiwari.
Run this directly inside Blender's Text Editor to parse the downlinked
IDSN Protobuf telemetry and animate the 3D Digital Twin.
"""

import os
import sys

import bpy

# Add the app/schemas directory to the path so we can import telemetry_pb2
# Note: You must run `python scripts/compile_proto.py` before running this in Blender.
# Adjust this path to the absolute path of your bas-apg folder if running remotely.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

try:
    from app.schemas import telemetry_pb2
except ImportError:
    print(
        "ERROR: Could not import telemetry_pb2. Ensure it's compiled and on the PYTHONPATH."
    )
    sys.exit(1)


def build_scene():
    """Builds primitive objects if they don't exist."""
    if "MainBox" not in bpy.data.objects:
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, enter_editmode=False, align="WORLD", location=(0, 0, 0)
        )
        bpy.context.active_object.name = "MainBox"

    if "Tweezers" not in bpy.data.objects:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.1,
            depth=1.0,
            enter_editmode=False,
            align="WORLD",
            location=(2, 0, 0),
        )
        bpy.context.active_object.name = "Tweezers"


def visualize_telemetry(telemetry_path: str):
    print("=" * 60)
    print("  BAS-APG Digital Twin Visualizer")
    print("=" * 60)

    if not os.path.exists(telemetry_path):
        print(f"ERROR: Telemetry file not found at {telemetry_path}")
        return

    print(f"Loading {telemetry_path}...")

    # Load the downlinked telemetry file
    burst = telemetry_pb2.TelemetryLog()
    with open(telemetry_path, "rb") as f:
        burst.ParseFromString(f.read())

    print(f"Loaded procedure: {burst.procedure_name}")
    print(f"Found {len(burst.kinematic_stream)} kinematic frames.")

    build_scene()

    # Scale down the translation since OpenCV output is usually in millimeters
    # and Blender units are usually meters.
    SCALE_FACTOR = 0.001

    # Animate tools in Blender
    # Note: kinematic_stream only exists every 3 frames, so we space keyframes by 3.
    frame_step = 3

    for idx, k_frame in enumerate(burst.kinematic_stream):
        blender_frame = idx * frame_step

        # Tool Animation
        for tool_name, transform in k_frame.tools.items():
            # Match the tool name to the Blender object
            if tool_name == "Red_Box":
                obj = bpy.data.objects.get("MainBox")
            elif tool_name == "Tweezers":
                obj = bpy.data.objects.get("Tweezers")
            else:
                obj = None

            if obj:
                # Apply translation (convert mm to m)
                obj.location = (
                    transform.x * SCALE_FACTOR,
                    transform.y * SCALE_FACTOR,
                    transform.z * SCALE_FACTOR,
                )
                obj.keyframe_insert(data_path="location", frame=blender_frame)

                # Apply rotation (Pitch, Roll, Yaw mapping may depend on camera coords vs blender coords)
                # OpenCV uses right-handed Y-down, Z-forward. Blender is Z-up, Y-forward.
                # A simple mapping for demo purposes:
                import math

                obj.rotation_euler = (
                    math.radians(transform.pitch),
                    math.radians(transform.roll),
                    math.radians(transform.yaw),
                )
                obj.keyframe_insert(data_path="rotation_euler", frame=blender_frame)

    print("✅ Animation baked successfully!")


if __name__ == "__main__":
    # Ensure this points to the generated binary payload from Phase 17/18
    telemetry_file = os.path.join(PROJECT_ROOT, "data", "telemetry_burst.bin")
    visualize_telemetry(telemetry_file)
