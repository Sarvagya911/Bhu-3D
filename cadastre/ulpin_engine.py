"""
3D ULPIN (Unique Land Parcel Identification Number) Generation Engine
Aligned with the Department of Land Resources (DoLR), Ministry of Rural Development,
Digital India Land Records Modernization Programme (DILRMP), and ISO 19152 LADM 3D Cadastre.

3D ULPIN Standard Format:
<BASE_14_DIGIT_ULPIN>-<STRATA>-<FLOOR>-<UNIT>-<Z_EXTENT>-<CHECK>

Example:
07DL4920183746-V3-F05-U502-Z1518-K4
"""

import math
import hashlib
import re

# Strata domain codes
STRATA_SUBTERRANEAN = "V1"   # Basements, Metro tunnels, subterranean utilities
STRATA_GROUND = "V2"          # Ground floor / surface plinth
STRATA_SUPERSTRUCTURE = "V3"  # Multi-story upper floors
STRATA_AIR_RIGHTS = "V4"      # Rooftop, solar installations, helipads, airspace

STRATA_MAP = {
    'subterranean': STRATA_SUBTERRANEAN,
    'ground': STRATA_GROUND,
    'superstructure': STRATA_SUPERSTRUCTURE,
    'air_rights': STRATA_AIR_RIGHTS,
}

STRATA_LABELS = {
    STRATA_SUBTERRANEAN: "Subterranean Strata (-Z)",
    STRATA_GROUND: "Ground Plane Strata (Plinth)",
    STRATA_SUPERSTRUCTURE: "Superstructure Strata (+Z)",
    STRATA_AIR_RIGHTS: "Air Rights / Aerial Strata",
}

# State code mapping for 2D ULPIN base
STATE_CODES = {
    'DELHI': '07',
    'HARYANA': '06',
    'UTTAR PRADESH': '09',
    'MAHARASHTRA': '27',
    'KARNATAKA': '29',
    'TAMIL NADU': '33',
    'GUJARAT': '24',
    'TELANGANA': '36',
    'RAJASTHAN': '08',
    'MADHYA PRADESH': '23',
}

ALPHANUM = "0123456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # Base32 excluding I and O to prevent confusion


def compute_luhn36_checksum(payload: str) -> str:
    """
    Computes a 2-character verification checksum using polynomial CRC/Luhn-like algorithm.
    """
    total = 0
    clean = re.sub(r'[^0-9A-Z]', '', payload.upper())
    for idx, char in enumerate(clean):
        factor = (idx % 5) + 2
        char_val = ALPHANUM.index(char) if char in ALPHANUM else ord(char) % 32
        total += char_val * factor
    
    char1 = ALPHANUM[total % len(ALPHANUM)]
    char2 = ALPHANUM[(total // len(ALPHANUM)) % len(ALPHANUM)]
    return f"{char1}{char2}"


def generate_2d_base_ulpin(state_code: str, centroid_lat: float, centroid_lng: float, survey_no: str = "") -> str:
    """
    Generates standard 14-digit alphanumeric 2D ULPIN based on geo-coordinates and state code.
    Formula translates lat/long grid to micro-coordinate indices with cryptographic determinism.
    """
    state_str = str(state_code).zfill(2)[:2]
    # Quantize coordinates to ~0.5m cadastral precision
    lat_int = int(round(abs(centroid_lat) * 100000))
    lng_int = int(round(abs(centroid_lng) * 100000))
    
    # Hash seed to produce deterministic standard 10-character alphanumeric body
    seed_str = f"{state_str}:{lat_int}:{lng_int}:{survey_no}"
    digest = hashlib.sha256(seed_str.encode('utf-8')).hexdigest().upper()
    
    # Convert hex digest slice into Base32 alphanumeric
    body = ""
    for i in range(0, 20, 2):
        byte_val = int(digest[i:i+2], 16)
        body += ALPHANUM[byte_val % len(ALPHANUM)]
        if len(body) == 10:
            break
            
    # Combine state code + 10-char body + 2-char parity checksum = 14 digits
    partial = f"{state_str}{body}"
    chk = compute_luhn36_checksum(partial)
    return f"{partial[:12]}{chk}"


def format_floor_code(floor_number: int) -> str:
    """
    Formats floor index into standardized floor code:
    e.g. -2 -> B02, -1 -> B01, 0 -> G00, 1 -> F01, 14 -> F14
    """
    if floor_number < 0:
        return f"B{abs(floor_number):02d}"
    elif floor_number == 0:
        return "G00"
    else:
        return f"F{floor_number:02d}"


def determine_strata_code(floor_number: int, unit_type: str = "") -> str:
    """
    Determines strata domain (V1 Subterranean, V2 Ground, V3 Superstructure, V4 Air Rights).
    """
    if floor_number < 0:
        return STRATA_SUBTERRANEAN
    elif floor_number == 0:
        return STRATA_GROUND
    elif "terrace" in unit_type.lower() or "rooftop" in unit_type.lower() or "air" in unit_type.lower():
        return STRATA_AIR_RIGHTS
    else:
        return STRATA_SUPERSTRUCTURE


def encode_z_extent(z_min: float, z_max: float) -> str:
    """
    Encodes vertical bounds (z_min, z_max) into 4-char string.
    e.g. 15.0 to 18.2 -> Z1518
    """
    z_min_int = max(0, int(round(z_min)))
    z_max_int = max(z_min_int, int(round(z_max)))
    return f"Z{z_min_int:02d}{z_max_int:02d}"


def sanitize_unit_code(unit_identifier: str) -> str:
    """
    Sanitizes unit identifier into a concise 2-6 character cadastral sub-code.
    e.g. Flat-501 -> U501, Shop-G02 -> G02, B2-P01 -> B2P01, PH-01 -> PH01
    """
    clean = re.sub(r'[^0-9A-Z]', '', unit_identifier.upper())
    for prefix in ['FLAT', 'UNIT', 'SHOP', 'OFFICE', 'ROOM', 'BAY', 'APARTMENT']:
        if clean.startswith(prefix) and len(clean) > len(prefix):
            clean = clean[len(prefix):]
            break
            
    if clean.isdigit():
        code = f"U{clean}"
    else:
        code = clean
        
    return code[:6]


def generate_3d_ulpin(
    base_2d_ulpin: str,
    floor_number: int,
    unit_identifier: str,
    z_min_meters: float,
    z_max_meters: float,
    unit_type: str = ""
) -> str:
    """
    Generates full 3D ULPIN:
    Format: <2D_ULPIN>-<STRATA>-<FLOOR>-<UNIT>-<Z_EXTENT>-<CHECK>
    Example: 07DL4920183746-V3-F05-U502-Z1518-K4
    """
    base_clean = base_2d_ulpin.strip().upper()
    strata = determine_strata_code(floor_number, unit_type)
    floor_code = format_floor_code(floor_number)
    unit_code = sanitize_unit_code(unit_identifier)
    z_code = encode_z_extent(z_min_meters, z_max_meters)
    
    # Body before checksum
    payload = f"{base_clean}-{strata}-{floor_code}-{unit_code}-{z_code}"
    chk = compute_luhn36_checksum(payload)
    
    return f"{payload}-{chk}"


def parse_3d_ulpin(ulpin_3d: str) -> dict:
    """
    Parses a 3D ULPIN into its constituent cadastral components.
    """
    pattern = r'^([0-9A-Z]{14})-(V[1-4])-([BGF][0-9]{2}|TER)-([0-9A-Z]{2,6})-(Z[0-9]{4})-([0-9A-Z]{2})$'
    match = re.match(pattern, ulpin_3d.strip().upper())
    
    if not match:
        # Fallback looser parser
        parts = ulpin_3d.strip().upper().split('-')
        if len(parts) >= 6:
            return {
                'valid': False,
                'base_2d_ulpin': parts[0],
                'strata_code': parts[1],
                'floor_code': parts[2],
                'unit_code': parts[3],
                'z_code': parts[4],
                'checksum': parts[5],
                'strata_label': STRATA_LABELS.get(parts[1], "Unknown Strata"),
                'error': 'Checksum or format mismatch'
            }
        return {'valid': False, 'error': 'Invalid 3D ULPIN structure'}
        
    base, strata, floor, unit, z_code, chk = match.groups()
    payload = f"{base}-{strata}-{floor}-{unit}-{z_code}"
    expected_chk = compute_luhn36_checksum(payload)
    
    z_min = float(z_code[1:3])
    z_max = float(z_code[3:5])
    
    return {
        'valid': (chk == expected_chk),
        'base_2d_ulpin': base,
        'strata_code': strata,
        'strata_label': STRATA_LABELS.get(strata, "Unknown Strata"),
        'floor_code': floor,
        'unit_code': unit,
        'z_code': z_code,
        'z_min_approx_m': z_min,
        'z_max_approx_m': z_max,
        'height_m': z_max - z_min,
        'checksum': chk,
        'checksum_valid': (chk == expected_chk)
    }
