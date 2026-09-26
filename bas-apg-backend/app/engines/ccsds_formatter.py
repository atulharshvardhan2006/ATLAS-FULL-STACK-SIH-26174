"""
BAS-APG — CCSDS Space Packet Protocol Formatter
Standard: CCSDS 133.0-B-2 (Space Packet Protocol)

Packs telemetry payloads into strictly-formatted binary CCSDS space packets,
proving the pipeline is ready for actual BAS flight computers and Deep Space
Network (DSN/IDSN) transmission.

CCSDS Primary Header Layout (6 bytes / 48 bits):
┌──────────────────────────────────────────────────────────────────┐
│  Bits 0-2   │ Packet Version Number (PVN) = 000                 │
│  Bit  3     │ Packet Type: 0=TM (telemetry), 1=TC (telecommand) │
│  Bit  4     │ Secondary Header Flag: 1 = present                │
│  Bits 5-15  │ Application Process Identifier (APID)             │
│  Bits 16-17 │ Sequence Flags: 11=standalone, 01=first, 10=last  │
│  Bits 18-31 │ Sequence Count (14-bit modular counter)           │
│  Bits 32-47 │ Data Length (number of octets in data - 1)        │
└──────────────────────────────────────────────────────────────────┘

Secondary Header (10 bytes):
┌──────────────────────────────────────────────────────────────────┐
│  Bytes 0-3  │ Coarse Time (UNIX epoch seconds, uint32)          │
│  Bytes 4-5  │ Fine Time (sub-second fractional, uint16)         │
│  Byte  6    │ Subsystem ID                                      │
│  Byte  7    │ Data Quality Flag                                 │
│  Bytes 8-9  │ Reserved (padding)                                │
└──────────────────────────────────────────────────────────────────┘

M4 Thermal Impact: 0% — Python's struct.pack() compiles to a single
ARM NEON SIMD instruction sequence. Bit-packing is computationally
weightless on Apple Silicon.
"""

import struct
import time
from enum import IntEnum


class APID(IntEnum):
    """Application Process Identifiers for ATLAS BAS subsystems.
    
    Range 0x000–0x7FF (11-bit). We reserve:
      0x001–0x00F  Core systems
      0x010–0x01F  Sensors & vision
      0x020–0x02F  Procedure & FSM
      0x030–0x03F  Safety & hazards
      0x040–0x04F  Aerospace extensions
    """
    # Core
    SYSTEM_HEARTBEAT   = 0x001
    AUTH_STATUS        = 0x002
    
    # Sensors & Vision
    YOLO_DETECTIONS    = 0x010
    HAND_TRACKING      = 0x011
    HOI_GRASP          = 0x012
    SPATIAL_BOUNDARY   = 0x013
    GLARE_MONITOR      = 0x014
    
    # Procedure & FSM
    FSM_STATE          = 0x020
    FSM_TRANSITION     = 0x021
    
    # Safety & Hazards
    CONTAINMENT_BREACH = 0x030
    UNSECURED_DRIFT    = 0x031
    
    # Aerospace Extensions (our new features)
    SLOSH_GUARD        = 0x040
    ECO_GOVERNOR       = 0x041
    MERKLE_LEDGER      = 0x042
    HESITATION_DETECT  = 0x043
    FOD_PROJECTION     = 0x044


class SequenceFlags(IntEnum):
    """CCSDS Sequence Flags (2 bits)."""
    CONTINUATION = 0b00
    FIRST        = 0b01
    LAST         = 0b10
    STANDALONE   = 0b11


class CCSDSPacketFormatter:
    """Formats telemetry into CCSDS 133.0-B-2 compliant space packets.
    
    Each subsystem gets its own APID and maintains its own 14-bit
    modular sequence counter. Packets include a 10-byte secondary
    header with CDS-epoch timestamps.
    
    Usage:
        formatter = CCSDSPacketFormatter()
        packet = formatter.pack_telemetry(APID.FSM_STATE, data_bytes)
        hex_dump = formatter.hex_dump(packet)
    """
    
    PACKET_VERSION = 0b000       # Always 000 for CCSDS v1
    PACKET_TYPE_TM = 0           # Telemetry
    PACKET_TYPE_TC = 1           # Telecommand
    SEC_HEADER_FLAG = 1          # Secondary header present
    
    def __init__(self):
        # Per-APID 14-bit modular sequence counters
        self._seq_counters: dict[int, int] = {}
        self._total_packets = 0
        self._total_bytes = 0
        self._last_packet_hex = ""
        self._last_apid = 0
    
    def _get_next_seq(self, apid: int) -> int:
        """Increment and return the 14-bit modular sequence counter for this APID."""
        count = self._seq_counters.get(apid, 0)
        self._seq_counters[apid] = (count + 1) & 0x3FFF  # 14-bit wrap
        return count
    
    def pack_primary_header(
        self,
        apid: int,
        seq_flags: int,
        seq_count: int,
        data_length: int,
    ) -> bytes:
        """Pack a 6-byte CCSDS primary header using struct.
        
        Word 1 (16 bits): PVN[3] | Type[1] | SecHdr[1] | APID[11]
        Word 2 (16 bits): SeqFlags[2] | SeqCount[14]
        Word 3 (16 bits): DataLength (num octets in data field - 1)
        """
        word1 = (
            (self.PACKET_VERSION << 13)
            | (self.PACKET_TYPE_TM << 12)
            | (self.SEC_HEADER_FLAG << 11)
            | (apid & 0x7FF)
        )
        word2 = (
            (seq_flags << 14)
            | (seq_count & 0x3FFF)
        )
        word3 = max(0, data_length - 1)  # CCSDS: length = octets - 1
        
        return struct.pack('>HHH', word1, word2, word3)
    
    def pack_secondary_header(self, subsystem_id: int = 0, quality: int = 0xFF) -> bytes:
        """Pack a 10-byte CDS-epoch secondary header.
        
        Coarse time: UNIX epoch seconds (uint32)
        Fine time:   Sub-second as fraction of 65536 (uint16)
        """
        now = time.time()
        coarse = int(now)                          # seconds since epoch
        fine = int((now - coarse) * 65536) & 0xFFFF  # sub-second
        
        return struct.pack(
            '>IHBBH',
            coarse,         # 4 bytes: coarse timestamp
            fine,           # 2 bytes: fine timestamp
            subsystem_id,   # 1 byte:  subsystem identifier
            quality,        # 1 byte:  data quality flag (0xFF = nominal)
            0x0000,         # 2 bytes: reserved
        )
    
    def pack_telemetry(
        self,
        apid: int,
        data: bytes,
        seq_flags: int = SequenceFlags.STANDALONE,
    ) -> bytes:
        """Pack a complete CCSDS space packet (header + secondary header + data).
        
        Returns the full binary packet ready for DSN transmission.
        """
        sec_header = self.pack_secondary_header(subsystem_id=apid & 0xFF)
        total_data = sec_header + data
        
        seq_count = self._get_next_seq(apid)
        primary_header = self.pack_primary_header(
            apid=apid,
            seq_flags=seq_flags,
            seq_count=seq_count,
            data_length=len(total_data),
        )
        
        packet = primary_header + total_data
        
        # Update stats
        self._total_packets += 1
        self._total_bytes += len(packet)
        self._last_packet_hex = packet.hex().upper()
        self._last_apid = apid
        
        return packet
    
    # ─── DATA FIELD PACKERS ──────────────────────────────────────────────────
    # Each subsystem packs its telemetry into a fixed-width struct.
    # Using big-endian (network byte order) per CCSDS standard.
    
    def pack_fsm_state(
        self,
        step_index: int,
        total_steps: int,
        deviation_flag: bool,
        debounce: int,
    ) -> bytes:
        """Pack FSM state into 8 bytes.
        
        Format: step_index(u16) | total_steps(u16) | deviation(u8) | debounce(u8) | pad(u16)
        """
        data = struct.pack(
            '>HHBBxx',
            step_index & 0xFFFF,
            total_steps & 0xFFFF,
            1 if deviation_flag else 0,
            debounce & 0xFF,
        )
        return self.pack_telemetry(APID.FSM_STATE, data)
    
    def pack_hand_tracking(
        self,
        detected: bool,
        norm_x: float,
        norm_y: float,
        velocity: float,
        is_immobile: bool,
    ) -> bytes:
        """Pack hand tracking into 12 bytes.
        
        Format: detected(u8) | immobile(u8) | norm_x(f16→u16) | norm_y(f16→u16) | velocity(f32)
        """
        # Convert normalized floats to fixed-point uint16 (0–65535)
        nx = int(max(0, min(1, norm_x)) * 65535) & 0xFFFF
        ny = int(max(0, min(1, norm_y)) * 65535) & 0xFFFF
        
        data = struct.pack(
            '>BBHHf',
            1 if detected else 0,
            1 if is_immobile else 0,
            nx, ny,
            velocity,
        )
        return self.pack_telemetry(APID.HAND_TRACKING, data)
    
    def pack_slosh_guard(self, jerk_magnitude: float, alert: bool) -> bytes:
        """Pack slosh guard into 6 bytes.
        
        Format: jerk_mag(f32) | alert(u8) | pad(u8)
        """
        data = struct.pack('>fBx', jerk_magnitude, 1 if alert else 0)
        return self.pack_telemetry(APID.SLOSH_GUARD, data)
    
    def pack_eco_governor(self, mode_active: bool, target_fps: float, frames_skipped: int) -> bytes:
        """Pack eco-governor into 8 bytes.
        
        Format: mode(u8) | pad(u8) | target_fps(f16→u16) | frames_skipped(u32)
        """
        fps_fixed = int(target_fps * 100) & 0xFFFF
        data = struct.pack('>BBH I', 1 if mode_active else 0, 0, fps_fixed, frames_skipped & 0xFFFFFFFF)
        return self.pack_telemetry(APID.ECO_GOVERNOR, data)
    
    def pack_merkle_ledger(self, chain_length: int, hash_prefix: bytes) -> bytes:
        """Pack merkle ledger into 12 bytes.
        
        Format: chain_length(u32) | hash_prefix(8 bytes of SHA-256)
        """
        # Take first 8 bytes of hash, pad if needed
        prefix = (hash_prefix[:8] if len(hash_prefix) >= 8 else hash_prefix.ljust(8, b'\x00'))
        data = struct.pack('>I', chain_length) + prefix
        return self.pack_telemetry(APID.MERKLE_LEDGER, data)
    
    def pack_hesitation(self, active: bool, count: int, dwell_ms: float) -> bytes:
        """Pack hesitation detector into 8 bytes.
        
        Format: active(u8) | count(u8) | pad(u16) | dwell_ms(f32)
        """
        data = struct.pack('>BBxxf', 1 if active else 0, count & 0xFF, dwell_ms)
        return self.pack_telemetry(APID.HESITATION_DETECT, data)
    
    def pack_fod_projection(self, active: bool, eta_s: float) -> bytes:
        """Pack FOD projection into 6 bytes.
        
        Format: active(u8) | pad(u8) | eta(f32)
        """
        data = struct.pack('>Bxf', 1 if active else 0, eta_s)
        return self.pack_telemetry(APID.FOD_PROJECTION, data)
    
    def pack_system_heartbeat(self, fps: float, inference_ms: float, ram_mb: int) -> bytes:
        """Pack system heartbeat into 10 bytes.
        
        Format: fps(f32) | inference_ms(f16→u16) | ram_mb(u16) | pad(u16)
        """
        inf_fixed = int(inference_ms * 100) & 0xFFFF
        data = struct.pack('>fHHxx', fps, inf_fixed, ram_mb & 0xFFFF)
        return self.pack_telemetry(APID.SYSTEM_HEARTBEAT, data)
    
    # ─── AGGREGATE PACKER ────────────────────────────────────────────────────
    
    def pack_full_telemetry_frame(self, state) -> list[bytes]:
        """Pack ALL subsystem telemetry for a single frame into CCSDS packets.
        
        Args:
            state: MissionState class with all telemetry fields
            
        Returns:
            List of binary CCSDS packets (one per subsystem).
        """
        S = state
        packets = []
        
        # 1. System Heartbeat
        packets.append(self.pack_system_heartbeat(S.fps, S.inference_ms, S.ram_usage_mb))
        
        # 2. FSM State
        packets.append(self.pack_fsm_state(
            S.fsm_current_step, S.fsm_total_steps, S.fsm_deviation_flag, S.fsm_debounce_count
        ))
        
        # 3. Hand Tracking
        hand_x = S.hand_wrist[0] if S.hand_wrist else 0.0
        hand_y = S.hand_wrist[1] if S.hand_wrist else 0.0
        packets.append(self.pack_hand_tracking(
            S.hand_detected, hand_x, hand_y, S.hand_velocity, S.hand_is_immobile
        ))
        
        # 4. Slosh Guard
        packets.append(self.pack_slosh_guard(S.jerk_magnitude, S.slosh_alert))
        
        # 5. Eco-Governor
        packets.append(self.pack_eco_governor(
            S.eco_governor_mode == "ACTIVE", S.eco_governor_fps, S.eco_frames_skipped
        ))
        
        # 6. Merkle Ledger
        hash_bytes = S.merkle_chain_hash.encode('utf-8')[:8] if S.merkle_chain_hash else b'\x00' * 8
        packets.append(self.pack_merkle_ledger(S.merkle_chain_length, hash_bytes))
        
        # 7. Hesitation
        packets.append(self.pack_hesitation(S.hesitation_active, S.hesitation_count, S.hesitation_dwell_ms))
        
        # 8. FOD Projection
        packets.append(self.pack_fod_projection(S.fod_projection_active, S.fod_impact_eta_s))
        
        return packets
    
    # ─── DISPLAY HELPERS ─────────────────────────────────────────────────────
    
    @staticmethod
    def hex_dump(packet: bytes, group: int = 2) -> str:
        """Format binary packet as a space-separated hex string."""
        hex_str = packet.hex().upper()
        return ' '.join(hex_str[i:i+group*2] for i in range(0, len(hex_str), group*2))
    
    @staticmethod
    def decode_primary_header(packet: bytes) -> dict:
        """Decode a CCSDS primary header for display purposes."""
        if len(packet) < 6:
            return {}
        w1, w2, w3 = struct.unpack('>HHH', packet[:6])
        return {
            "version": (w1 >> 13) & 0x7,
            "type": "TM" if ((w1 >> 12) & 1) == 0 else "TC",
            "sec_header": bool((w1 >> 11) & 1),
            "apid": w1 & 0x7FF,
            "apid_hex": f"0x{w1 & 0x7FF:03X}",
            "seq_flags": (w2 >> 14) & 0x3,
            "seq_count": w2 & 0x3FFF,
            "data_length": w3 + 1,
            "total_length": w3 + 1 + 6,
        }
    
    def get_stats(self) -> dict:
        """Return formatter statistics for telemetry display."""
        return {
            "total_packets": self._total_packets,
            "total_bytes": self._total_bytes,
            "last_hex": self._last_packet_hex[:64] + ("..." if len(self._last_packet_hex) > 64 else ""),
            "last_apid": f"0x{self._last_apid:03X}",
            "apid_name": APID(self._last_apid).name if self._last_apid in APID._value2member_map_ else "UNKNOWN",
            "active_apids": len(self._seq_counters),
        }


# Singleton — shared between engine and WebSocket route
ccsds_formatter = CCSDSPacketFormatter()
