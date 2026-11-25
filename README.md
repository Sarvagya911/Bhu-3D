# भू-3D | Bhu-3D Cadastre
## 3D ULPIN Generation & Vertical Property Mapping System
**Organization:** Ministry of Rural Development, Department of Land Resources (DoLR), Government of India  
**Problem Statement (Serial No. 11):** *3D ULPIN Generation and vertical Property Mapping System*  
**Standard Compliance:** ISO 19152 (Land Administration Domain Model - LADM 3D Cadastre) & Digital India Land Records Modernization Programme (DILRMP)

---

## 🏛️ Executive Summary

Under the Digital India Land Records Modernization Programme (DILRMP), the Government of India introduced the **Unique Land Parcel Identification Number (ULPIN)**, or **Bhu-Aadhaar**, as a 14-digit alphanumeric identification for 2D land surface parcels.

However, modern urban and peri-urban centers have high-density vertical developments:
- **Subterranean Strata (-Z):** Underground Metro rail tunnels, multi-tier basements, automated parking bays, and underground retail concourses.
- **Surface Plinth (Z=0):** Ground level retail showrooms and public plazas.
- **Superstructure (+Z):** Multi-story residential condominiums, high-rise apartments, and commercial office towers.
- **Air Rights / Aerial Strata (Top):** Rooftop solar power generation grids, helipads, and telecommunication infrastructure.

Traditional 2D land records club multiple vertical owners under a single ground parcel or completely lack volumetric legal definition. **Bhu-3D** solves this national challenge by extending Bhu-Aadhaar into a full **3D ULPIN Generation and Vertical Property Mapping System**.

---

## 📐 3D ULPIN Standard Specification Format

Each volumetric unit receives a cryptographically deterministic 3D ULPIN:

```
<BASE_14_DIGIT_ULPIN>-<STRATA_REALM>-<FLOOR_CODE>-<UNIT_ID>-<Z_BOUNDS>-<CHECKSUM>
```

### Breakdown Example: `06GG0184920184-V3-F05-U502-Z1518-8A`

| Component | Code | Meaning |
| :--- | :--- | :--- |
| **1. 2D Base ULPIN** | `06GG0184920184` | 14-Digit Land Parcel Cadastre (State 06: Haryana, Gurugram centroid) |
| **2. Strata Realm** | `V3` | Superstructure Strata (+Z: Upper Floors) |
| **3. Floor Code** | `F05` | 5th Floor (`B01`=Basement 1, `G00`=Ground, `F01`..`F99`=Upper) |
| **4. Unit Identifier** | `U502` | Volumetric Sub-Parcel ID (Flat 502) |
| **5. Z-Bounds Code** | `Z1518` | Vertical extent: $Z_{min}=15.0m$ to $Z_{max}=18.3m$ above ground datum |
| **6. Checksum** | `8A` | 2-character polynomial verification parity (Luhn-Mod-36 / CRC) |

### Strata Realms Defined:
- `V1`: **Subterranean Strata (-Z):** Basements, Metro stations, subterranean parking.
- `V2`: **Ground Plane Strata (Plinth level):** Ground floor retail, lobby, open plaza.
- `V3`: **Superstructure Strata (+Z):** High-rise residential flats, corporate office suites.
- `V4`: **Air Rights / Rooftop Strata:** Rooftop solar installations, helipads, antennas.

---

## 🚀 Key System Features

1. **Interactive 3D Cadastre WebGL Explorer (Three.js)**:
   - Full 3D rendering of parcels, building footprints, and extruded volumetric units.
   - **Exploded View Slider**: Separates vertical floors along the Z-axis in real time to visually inspect interior units.
   - **Floor-by-Floor Slicing**: Inspect individual floor plans in 3D isolation.
   - **Strata Domain Filters**: Toggle Subterranean (-Z), Ground (0), Superstructure (+Z), and Air Rights.
   - **Color Modes**: By Strata Realm, By Unit Type, By Legal Status (Clear / Mortgaged / Disputed), or By Tax Compliance.
   - **Raycaster Inspection**: Click any 3D unit to pull up immediate cadastral metadata, volumetric dimensions, Undivided Share of Land (UDS %), and owner deeds.

2. **3D ULPIN Generation Engine & Batch Synthesizer**:
   - Single Unit Generator with real-time coordinate math and parity check.
   - Batch Synthesizer: 1-click generation of entire high-rise schedules with CSV export.

3. **Digital 3D Bhu-Aadhaar Certificate (e-RoR / Record of Rights)**:
   - Official Ministry of Rural Development e-RoR certificate layout.
   - Dynamic QR Code encoding official verification URL.
   - 3D Isometric schematic wireframe rendered on HTML5 canvas.
   - Complete legal chain of title, Undivided Share of Land (UDS %), and encumbrance certificate.
   - Print-ready and exportable to PDF.

4. **Automated Spatial Audit & Volumetric Conflict Detection**:
   - Master Plan building height violation audit (detects unauthorized vertical floor extensions).
   - Floor Area Ratio (FAR) compliance verification.
   - Volumetric overlap collision detection in $(X, Y, Z)$ coordinate space.

5. **Citizen & Registrar Property Verification Portal**:
   - Public search by 3D ULPIN, 2D ULPIN, Owner Name, Khasra Number, or Street Address.

---

## 🛠️ Quick Start Instructions

### 1. Requirements
- Python 3.10+ (Tested on Python 3.14)
- Django 6.1+

### 2. Run Database Migrations & Seed Data
```bash
# Apply database schema
python manage.py migrate

# Seed realistic 3D Cadastre demo data
python manage.py seed_cadastre
```

### 3. Launch the Server
```bash
python manage.py runserver 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

### 4. Admin Credentials
- **URL:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)
- **Username:** `admin`
- **Password:** `adminpassword123`

---

## 🧪 Automated Test Suite

Run the comprehensive unit and integration test suite:
```bash
python manage.py test
```
All 10 tests verify 2D ULPIN generation, 3D ULPIN encoding/decoding, checksum calculation, volumetric views, and REST API endpoints.

---

## 📁 Project Architecture

```
Bhu-3D/
│
├── manage.py                          # Django management CLI
├── db.sqlite3                         # SQLite database
├── README.md                          # Comprehensive documentation
│
├── bhu3d_core/                        # Project configuration
│   ├── settings.py                    # Django settings & installed apps
│   ├── urls.py                        # Root URL routing
│   └── wsgi.py
│
├── cadastre/                          # Core Cadastre & 3D ULPIN Application
│   ├── admin.py                       # Django Admin configuration
│   ├── models.py                      # ISO 19152 LADM 3D Cadastre models
│   ├── ulpin_engine.py                # 3D ULPIN mathematical generation engine
│   ├── views.py                       # Web views & REST API endpoints
│   ├── urls.py                        # Application URL routes
│   ├── tests.py                       # Automated test suite (10 tests)
│   └── management/commands/
│       └── seed_cadastre.py           # Realistic multi-strata demo seed script
│
├── templates/                         # User Interface Templates
│   ├── base.html                      # Government of India theme & navigation
│   ├── dashboard.html                 # Executive statistics & live syntax decoder
│   ├── explorer_3d.html               # Flagship Three.js WebGL 3D Cadastre Explorer
│   ├── ulpin_generator.html           # Interactive & Batch 3D ULPIN Generator
│   ├── bhu_aadhaar_card.html          # Digital 3D Bhu-Aadhaar Certificate (e-RoR)
│   ├── spatial_audit.html             # Automated Height & Volumetric Conflict Audit
│   ├── public_search.html             # Citizen Property Verification Search
│   └── parcel_builder.html            # 3D Strata & Multi-Story Parcel Builder
│
└── static/                            # Static asset directory
```

---

## 🇮🇳 Alignment with Government of India Initiatives

- **Ministry of Rural Development:** Fulfilling Problem Statement Serial No. 11 for modernizing land administration beyond 2D boundaries.
- **Department of Land Resources (DoLR):** Extending DILRMP Bhu-Aadhaar to vertical apartment units, condominiums, and subterranean assets.
- **Ease of Doing Business & Transparent Real Estate:** Eliminating fraudulent double-mortgaging of apartments through unambiguous volumetric 3D ULPIN title records.
