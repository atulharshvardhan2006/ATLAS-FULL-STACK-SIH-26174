"""
BAS-APG — Protobuf Compiler

Compiles the telemetry.proto schema into Python bindings (telemetry_pb2.py).
Requires `grpcio-tools`.
"""

import os
import subprocess
import sys


def compile_proto():
    print("=" * 60)
    print("  BAS-APG Protobuf Schema Compiler")
    print("=" * 60)

    proto_dir = os.path.abspath("app/schemas")
    proto_file = os.path.join(proto_dir, "telemetry.proto")

    if not os.path.exists(proto_file):
        print(f"ERROR: Proto file not found at {proto_file}")
        sys.exit(1)

    print(f"Compiling {proto_file}...")

    # Run python -m grpc_tools.protoc -Iapp/schemas --python_out=app/schemas app/schemas/telemetry.proto
    try:
        import grpc_tools.protoc
    except ImportError:
        print(
            "ERROR: grpcio-tools is not installed. Please run `pip install grpcio-tools`."
        )
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_dir}",
        f"--python_out={proto_dir}",
        proto_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Compilation Failed:\n{result.stderr}")
        sys.exit(1)

    print("✅ Success! Created app/schemas/telemetry_pb2.py")


if __name__ == "__main__":
    compile_proto()
