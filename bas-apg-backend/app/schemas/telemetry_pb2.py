

"""Generated protocol buffer code."""

from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 7, 35, 1, "", "telemetry.proto"
)


_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0ftelemetry.proto\x12\x11\x62\x61s_apg.telemetry"\x87\x01\n\tDetection\x12\x12\n\nclass_name\x18\x01 \x01(\t\x12\x12\n\nconfidence\x18\x02 \x01(\x02\x12\x10\n\x08track_id\x18\x03 \x01(\x05\x12\x0f\n\x07\x62\x62ox_cx\x18\x04 \x01(\x02\x12\x0f\n\x07\x62\x62ox_cy\x18\x05 \x01(\x02\x12\x0e\n\x06\x62\x62ox_w\x18\x06 \x01(\x02\x12\x0e\n\x06\x62\x62ox_h\x18\x07 \x01(\x02"E\n\x0bInteraction\x12\x12\n\nclass_name\x18\x01 \x01(\t\x12\r\n\x05state\x18\x02 \x01(\t\x12\x13\n\x0b\x64istance_mm\x18\x03 \x01(\x02"^\n\x08\x46SMState\x12\x17\n\x0f\x63urrent_step_id\x18\x01 \x01(\t\x12\x0e\n\x06status\x18\x02 \x01(\t\x12\x12\n\nstart_time\x18\x03 \x01(\t\x12\x15\n\rrecovery_text\x18\x04 \x01(\t"\xdc\x01\n\x0eTelemetryFrame\x12\x11\n\ttimestamp\x18\x01 \x01(\x01\x12.\n\tfsm_state\x18\x02 \x01(\x0b\x32\x1b.bas_apg.telemetry.FSMState\x12\x30\n\ndetections\x18\x03 \x03(\x0b\x32\x1c.bas_apg.telemetry.Detection\x12\x34\n\x0cinteractions\x18\x04 \x03(\x0b\x32\x1e.bas_apg.telemetry.Interaction\x12\x12\n\nlatency_ms\x18\x05 \x01(\x05\x12\x0b\n\x03\x66ps\x18\x06 \x01(\x05"X\n\x0bTransform3D\x12\t\n\x01x\x18\x01 \x01(\x02\x12\t\n\x01y\x18\x02 \x01(\x02\x12\t\n\x01z\x18\x03 \x01(\x02\x12\r\n\x05pitch\x18\x04 \x01(\x02\x12\x0b\n\x03yaw\x18\x05 \x01(\x02\x12\x0c\n\x04roll\x18\x06 \x01(\x02"\xe3\x01\n\x0eKinematicFrame\x12\x11\n\ttimestamp\x18\x01 \x01(\x01\x12\x33\n\x0bhand_joints\x18\x02 \x03(\x0b\x32\x1e.bas_apg.telemetry.Transform3D\x12;\n\x05tools\x18\x03 \x03(\x0b\x32,.bas_apg.telemetry.KinematicFrame.ToolsEntry\x1aL\n\nToolsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12-\n\x05value\x18\x02 \x01(\x0b\x32\x1e.bas_apg.telemetry.Transform3D:\x02\x38\x01"\x96\x01\n\x0cTelemetryLog\x12\x16\n\x0eprocedure_name\x18\x01 \x01(\t\x12\x31\n\x06\x66rames\x18\x02 \x03(\x0b\x32!.bas_apg.telemetry.TelemetryFrame\x12;\n\x10kinematic_stream\x18\x03 \x03(\x0b\x32!.bas_apg.telemetry.KinematicFrameb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "telemetry_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals["_KINEMATICFRAME_TOOLSENTRY"]._loaded_options = None
    _globals["_KINEMATICFRAME_TOOLSENTRY"]._serialized_options = b"8\001"
    _globals["_DETECTION"]._serialized_start = 39
    _globals["_DETECTION"]._serialized_end = 174
    _globals["_INTERACTION"]._serialized_start = 176
    _globals["_INTERACTION"]._serialized_end = 245
    _globals["_FSMSTATE"]._serialized_start = 247
    _globals["_FSMSTATE"]._serialized_end = 341
    _globals["_TELEMETRYFRAME"]._serialized_start = 344
    _globals["_TELEMETRYFRAME"]._serialized_end = 564
    _globals["_TRANSFORM3D"]._serialized_start = 566
    _globals["_TRANSFORM3D"]._serialized_end = 654
    _globals["_KINEMATICFRAME"]._serialized_start = 657
    _globals["_KINEMATICFRAME"]._serialized_end = 884
    _globals["_KINEMATICFRAME_TOOLSENTRY"]._serialized_start = 808
    _globals["_KINEMATICFRAME_TOOLSENTRY"]._serialized_end = 884
    _globals["_TELEMETRYLOG"]._serialized_start = 887
    _globals["_TELEMETRYLOG"]._serialized_end = 1037

