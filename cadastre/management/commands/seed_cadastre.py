import json
import math
from django.core.management.base import BaseCommand
from django.utils import timezone
from cadastre.models import (
    CadastralZone,
    LandParcel,
    BuildingStructure,
    VerticalPropertyUnit,
    PropertyOwnership,
    EncumbranceDispute,
    SpatialEncroachmentLog,
)
from cadastre.ulpin_engine import (
    generate_2d_base_ulpin,
    generate_3d_ulpin,
    STRATA_SUBTERRANEAN,
    STRATA_GROUND,
    STRATA_SUPERSTRUCTURE,
    STRATA_AIR_RIGHTS,
)


class Command(BaseCommand):
    help = "Seeds realistic 3D Cadastre and Vertical Property Mapping demo data"

    def handle(self, *args, **options):
        self.stdout.write("Purging existing cadastre records...")
        SpatialEncroachmentLog.objects.all().delete()
        EncumbranceDispute.objects.all().delete()
        PropertyOwnership.objects.all().delete()
        VerticalPropertyUnit.objects.all().delete()
        BuildingStructure.objects.all().delete()
        LandParcel.objects.all().delete()
        CadastralZone.objects.all().delete()

        self.stdout.write("Creating Cadastral Zones...")
        zone_delhi = CadastralZone.objects.create(
            state_name="Delhi",
            state_code="07",
            district="South West Delhi",
            tehsil="Vasant Vihar",
            village_or_ward="Aerocity / Vasant Kunj Sector C",
            pincode="110037",
            master_plan_zone="Zone K-II (Urban Mixed Use)"
        )

        zone_haryana = CadastralZone.objects.create(
            state_name="Haryana",
            state_code="06",
            district="Gurugram",
            tehsil="Gurugram South",
            village_or_ward="Sector 54 Golf Course Road",
            pincode="122011",
            master_plan_zone="Zone R-High (High Density Residential & Commercial)"
        )

        zone_up = CadastralZone.objects.create(
            state_name="Uttar Pradesh",
            state_code="09",
            district="Gautam Buddha Nagar",
            tehsil="Dadri",
            village_or_ward="TechZone 4, Greater Noida West",
            pincode="201306",
            master_plan_zone="Zone C-3 (Commercial & High Rise IT Park)"
        )

        # -------------------------------------------------------------------------
        # PARCEL 1: Saraswati Heights & Sky Residency (Gurugram)
        # 14-story High-Rise + 2 Basements + Rooftop Air Rights
        # -------------------------------------------------------------------------
        self.stdout.write("Creating Parcel 1: Saraswati Heights (Gurugram)...")
        lat1, lng1 = 28.4595, 77.0266
        ulpin1_2d = generate_2d_base_ulpin("06", lat1, lng1, "KHASRA-842/1")
        
        boundary1 = [
            [lng1 - 0.0006, lat1 - 0.0006],
            [lng1 + 0.0006, lat1 - 0.0006],
            [lng1 + 0.0006, lat1 + 0.0006],
            [lng1 - 0.0006, lat1 + 0.0006],
            [lng1 - 0.0006, lat1 - 0.0006]
        ]
        
        parcel1 = LandParcel.objects.create(
            ulpin_2d=ulpin1_2d,
            khasra_survey_no="Khasra No. 842/1-Min",
            zone=zone_haryana,
            address="Plot No. 14, Golf Course Extension Road, Sector 54, Gurugram",
            land_use="MIXED_USE",
            total_area_sqm=4850.0,
            centroid_lat=lat1,
            centroid_lng=lng1,
            boundary_geojson=json.dumps(boundary1),
            sanctioned_max_height_m=52.0,
            sanctioned_far=3.25
        )

        bldg1 = BuildingStructure.objects.create(
            parcel=parcel1,
            name="Saraswati Heights - Tower Alpha",
            structure_type="HIGH_RISE_RESIDENTIAL",
            footprint_geojson=json.dumps([
                [lng1 - 0.0003, lat1 - 0.0003],
                [lng1 + 0.0003, lat1 - 0.0003],
                [lng1 + 0.0003, lat1 + 0.0003],
                [lng1 - 0.0003, lat1 + 0.0003],
                [lng1 - 0.0003, lat1 - 0.0003]
            ]),
            ground_elevation_msl=218.4,
            total_floors_above_ground=12,
            basement_levels=2,
            total_height_m=42.5,
            sanction_order_no="HSVP/GGN/2023/BP-9041",
            occupancy_certificate_status="APPROVED",
            completion_year=2024
        )

        # Generate Vertical Units for Building 1
        floor_specs = [
            # Basement 2 (Subterranean)
            {"floor": -2, "name": "Basement 2 (Lower)", "strata": "V1", "z_min": -6.4, "z_max": -3.2, "units": [
                {"unit_no": "B2-P01", "type": "BASEMENT_PARKING", "area": 35.0, "status": "REGISTERED", "tax": "PAID", "val": 600000.0, "owner": "Rajesh Kumar Sharma", "id": "XXXX-XXXX-4102", "deed": "REG/HR/2024/781"},
                {"unit_no": "B2-P02", "type": "BASEMENT_PARKING", "area": 35.0, "status": "REGISTERED", "tax": "PAID", "val": 600000.0, "owner": "Ananya Sen Gupta", "id": "XXXX-XXXX-9914", "deed": "REG/HR/2024/782"},
                {"unit_no": "B2-UTIL", "type": "COMMON_UTILITY", "area": 250.0, "status": "GOVERNMENT", "tax": "EXEMPT", "val": 2500000.0, "owner": "Saraswati Heights RWA", "id": "RWA-GGN-2024-09", "deed": "REG/HR/2024/700"}
            ]},
            # Basement 1 (Subterranean)
            {"floor": -1, "name": "Basement 1 (Upper)", "strata": "V1", "z_min": -3.2, "z_max": 0.0, "units": [
                {"unit_no": "B1-P01", "type": "BASEMENT_PARKING", "area": 38.0, "status": "REGISTERED", "tax": "PAID", "val": 650000.0, "owner": "Vikramaditya Roy", "id": "XXXX-XXXX-5521", "deed": "REG/HR/2024/810"},
                {"unit_no": "B1-P02", "type": "BASEMENT_PARKING", "area": 38.0, "status": "MORTGAGED", "tax": "PAID", "val": 650000.0, "owner": "Dr. Sunita Deshmukh", "id": "XXXX-XXXX-6612", "deed": "REG/HR/2024/811"},
            ]},
            # Ground Floor (Surface Plinth)
            {"floor": 0, "name": "Ground Floor (Plinth)", "strata": "V2", "z_min": 0.0, "z_max": 3.6, "units": [
                {"unit_no": "G-01", "type": "RETAIL_SHOP", "area": 115.0, "status": "REGISTERED", "tax": "PAID", "val": 16500000.0, "owner": "MedPlus Pharmacy Retail Ltd", "id": "CORP-CIN-89102", "deed": "REG/HR/2024/1101"},
                {"unit_no": "G-02", "type": "RETAIL_SHOP", "area": 95.0, "status": "REGISTERED", "tax": "PAID", "val": 14000000.0, "owner": "HDFC Bank ATM & Digital Branch", "id": "CORP-CIN-49210", "deed": "REG/HR/2024/1102"},
                {"unit_no": "G-LOBBY", "type": "COMMON_UTILITY", "area": 180.0, "status": "GOVERNMENT", "tax": "EXEMPT", "val": 5000000.0, "owner": "Saraswati Heights RWA", "id": "RWA-GGN-2024-09", "deed": "REG/HR/2024/701"}
            ]},
        ]

        # Add upper floors (1 to 10)
        for flr in range(1, 11):
            z_bottom = 3.6 + (flr - 1) * 3.3
            z_top = z_bottom + 3.3
            floor_specs.append({
                "floor": flr,
                "name": f"{flr}th Floor",
                "strata": "V3",
                "z_min": round(z_bottom, 2),
                "z_max": round(z_top, 2),
                "units": [
                    {"unit_no": f"Flat-{flr}01", "type": "RESIDENTIAL_3BHK", "area": 165.0, "status": "REGISTERED", "tax": "PAID", "val": 12500000.0 + flr*200000, "owner": f"Owner {flr}01 - Arvind Mehra", "id": f"XXXX-XXXX-{1000+flr}", "deed": f"REG/HR/2024/{2000+flr}"},
                    {"unit_no": f"Flat-{flr}02", "type": "RESIDENTIAL_3BHK", "area": 165.0, "status": "MORTGAGED" if flr % 3 == 0 else "REGISTERED", "tax": "PAID", "val": 12500000.0 + flr*200000, "owner": f"Owner {flr}02 - Neha Kashyap", "id": f"XXXX-XXXX-{2000+flr}", "deed": f"REG/HR/2024/{3000+flr}"},
                    {"unit_no": f"Flat-{flr}03", "type": "RESIDENTIAL_4BHK", "area": 220.0, "status": "REGISTERED", "tax": "PAID", "val": 17500000.0 + flr*250000, "owner": f"Owner {flr}03 - Col. R. S. Rathore (Retd)", "id": f"XXXX-XXXX-{3000+flr}", "deed": f"REG/HR/2024/{4000+flr}"},
                    {"unit_no": f"Flat-{flr}04", "type": "RESIDENTIAL_2BHK", "area": 110.0, "status": "DISPUTED" if flr == 7 else "REGISTERED", "tax": "DUE" if flr == 7 else "PAID", "val": 8500000.0 + flr*150000, "owner": f"Owner {flr}04 - Pooja Verma", "id": f"XXXX-XXXX-{4000+flr}", "deed": f"REG/HR/2024/{5000+flr}"},
                ]
            })

        # Penthouse Floor 11
        floor_specs.append({
            "floor": 11,
            "name": "11th Floor (Penthouse Level)",
            "strata": "V3",
            "z_min": 36.6,
            "z_max": 40.5,
            "units": [
                {"unit_no": "PH-01", "type": "PENTHOUSE", "area": 360.0, "status": "REGISTERED", "tax": "PAID", "val": 35000000.0, "owner": "Gautam Singhania Enterprises", "id": "CORP-CIN-77219", "deed": "REG/HR/2024/9901"},
                {"unit_no": "PH-02", "type": "PENTHOUSE", "area": 360.0, "status": "REGISTERED", "tax": "PAID", "val": 35000000.0, "owner": "Justice Alok Tandon (Retd)", "id": "XXXX-XXXX-7714", "deed": "REG/HR/2024/9902"}
            ]
        })

        # Rooftop (Air Rights & Solar Strata)
        floor_specs.append({
            "floor": 12,
            "name": "Terrace & Air Rights Strata",
            "strata": "V4",
            "z_min": 40.5,
            "z_max": 42.5,
            "units": [
                {"unit_no": "AIR-SOLAR", "type": "AIR_ROOFTOP", "area": 500.0, "status": "REGISTERED", "tax": "EXEMPT", "val": 4500000.0, "owner": "SunPower Solar Grid EPC Ltd", "id": "CORP-CIN-31849", "deed": "REG/HR/2024/9950"},
                {"unit_no": "AIR-TELECOM", "type": "AIR_ROOFTOP", "area": 80.0, "status": "REGISTERED", "tax": "PAID", "val": 1800000.0, "owner": "Bharti Airtel Infratel Ltd", "id": "CORP-CIN-12904", "deed": "REG/HR/2024/9951"}
            ]
        })

        # Persist units for Building 1
        total_units_b1 = sum(len(f['units']) for f in floor_specs)
        uds_share_b1 = round(100.0 / total_units_b1, 3)

        for fs in floor_specs:
            for u in fs['units']:
                ulpin_3d = generate_3d_ulpin(
                    base_2d_ulpin=parcel1.ulpin_2d,
                    floor_number=fs['floor'],
                    unit_identifier=u['unit_no'],
                    z_min_meters=fs['z_min'],
                    z_max_meters=fs['z_max'],
                    unit_type=u['type']
                )

                h = round(fs['z_max'] - fs['z_min'], 2)
                vol = round(u['area'] * h, 2)

                unit_obj = VerticalPropertyUnit.objects.create(
                    building=bldg1,
                    ulpin_3d=ulpin_3d,
                    unit_number=u['unit_no'],
                    strata_type=fs['strata'],
                    floor_number=fs['floor'],
                    floor_name=fs['name'],
                    unit_type=u['type'],
                    z_min_meters=fs['z_min'],
                    z_max_meters=fs['z_max'],
                    carpet_area_sqm=round(u['area'] * 0.78, 1),
                    built_up_area_sqm=u['area'],
                    volume_cubic_meters=vol,
                    undivided_share_land_pct=uds_share_b1,
                    status=u['status'],
                    property_tax_status=u['tax'],
                    market_valuation_inr=u['val']
                )

                # Create Ownership
                PropertyOwnership.objects.create(
                    unit=unit_obj,
                    owner_name=u['owner'],
                    owner_type='CORPORATE' if 'Ltd' in u['owner'] or 'Enterprises' in u['owner'] else ('RWA' if 'RWA' in u['owner'] else 'INDIVIDUAL'),
                    identity_masked=u['id'],
                    registered_deed_no=u['deed'],
                    registration_date=timezone.now().date(),
                    registration_authority="Sub-Registrar Office, Gurugram South",
                    ownership_share_pct=100.0,
                    is_primary_owner=True
                )

                # Add mortgage if status is MORTGAGED
                if u['status'] == 'MORTGAGED':
                    EncumbranceDispute.objects.create(
                        unit=unit_obj,
                        dispute_type='MORTGAGE',
                        filing_authority='State Bank of India (RACPC Gurugram)',
                        case_reference_no=f"SBI/HL/2024/{unit_obj.id*137}",
                        status='ACTIVE',
                        description=f"Home Loan Mortgage Charge created in favor of SBI against {unit_obj.unit_number}."
                    )

                # Add dispute if status is DISPUTED
                if u['status'] == 'DISPUTED':
                    EncumbranceDispute.objects.create(
                        unit=unit_obj,
                        dispute_type='COURT_STAY',
                        filing_authority='Civil Court Gurugram Senior Division',
                        case_reference_no=f"OS-314/2024",
                        status='ACTIVE',
                        description=f"Interim Injunction Stay Order passed regarding disputed title inheritance claim."
                    )

        # -------------------------------------------------------------------------
        # PARCEL 2: Pragati Metro Interchange & Subterranean Hub (Aerocity, Delhi)
        # Deep Subterranean (-Z) Metro Concourse + Commercial High Rise
        # -------------------------------------------------------------------------
        self.stdout.write("Creating Parcel 2: Pragati Metro Hub (Delhi Aerocity)...")
        lat2, lng2 = 28.5524, 77.1215
        ulpin2_2d = generate_2d_base_ulpin("07", lat2, lng2, "SURVEY-AEROCITY-44")
        
        boundary2 = [
            [lng2 - 0.0008, lat2 - 0.0008],
            [lng2 + 0.0008, lat2 - 0.0008],
            [lng2 + 0.0008, lat2 + 0.0008],
            [lng2 - 0.0008, lat2 + 0.0008],
            [lng2 - 0.0008, lat2 - 0.0008]
        ]
        
        parcel2 = LandParcel.objects.create(
            ulpin_2d=ulpin2_2d,
            khasra_survey_no="Survey Plot 104-BhuAerocity",
            zone=zone_delhi,
            address="Aerocity Worldmark Boulevard, Near Terminal 3 Metro, New Delhi",
            land_use="COMMERCIAL",
            total_area_sqm=8200.0,
            centroid_lat=lat2,
            centroid_lng=lng2,
            boundary_geojson=json.dumps(boundary2),
            sanctioned_max_height_m=45.0,
            sanctioned_far=3.50
        )

        bldg2 = BuildingStructure.objects.create(
            parcel=parcel2,
            name="Worldmark Aero-Transit Tower",
            structure_type="COMMERCIAL_COMPLEX",
            footprint_geojson=json.dumps([
                [lng2 - 0.0005, lat2 - 0.0005],
                [lng2 + 0.0005, lat2 - 0.0005],
                [lng2 + 0.0005, lat2 + 0.0005],
                [lng2 - 0.0005, lat2 + 0.0005],
                [lng2 - 0.0005, lat2 - 0.0005]
            ]),
            ground_elevation_msl=232.0,
            total_floors_above_ground=8,
            basement_levels=3,
            total_height_m=32.0,
            sanction_order_no="DDA/AERO/2022/COMM-184",
            occupancy_certificate_status="APPROVED",
            completion_year=2023
        )

        # Metro Deep Subterranean Units (-Z)
        metro_units = [
            {"floor": -3, "name": "Basement 3 (Metro Rail Concourse)", "strata": "V1", "z_min": -12.0, "z_max": -7.5, "unit_no": "B3-METRO-PLATFORM", "type": "COMMON_UTILITY", "area": 1200.0, "owner": "Delhi Metro Rail Corporation (DMRC)", "val": 85000000.0},
            {"floor": -2, "name": "Basement 2 (Automated Parking & Utilities)", "strata": "V1", "z_min": -7.5, "z_max": -3.8, "unit_no": "B2-AUTO-PARK", "type": "BASEMENT_PARKING", "area": 950.0, "owner": "Delhi International Airport Ltd (DIAL)", "val": 42000000.0},
            {"floor": -1, "name": "Basement 1 (Underground Food Court)", "strata": "V1", "z_min": -3.8, "z_max": 0.0, "unit_no": "B1-FOODCOURT", "type": "RETAIL_SHOP", "area": 850.0, "owner": "Haldiram Snacks & Dining Ltd", "val": 38000000.0},
            {"floor": 0, "name": "Ground Floor Plaza", "strata": "V2", "z_min": 0.0, "z_max": 4.5, "unit_no": "G-PLAZA-SHOWROOM", "type": "RETAIL_SHOP", "area": 750.0, "owner": "Tata Starbucks Pvt Ltd", "val": 45000000.0},
            {"floor": 1, "name": "1st Floor IT Hub", "strata": "V3", "z_min": 4.5, "z_max": 8.5, "unit_no": "OFFICE-101", "type": "COMMERCIAL_OFFICE", "area": 600.0, "owner": "Google Cloud Regional Hub India", "val": 52000000.0},
            {"floor": 2, "name": "2nd Floor Corporate Suite", "strata": "V3", "z_min": 8.5, "z_max": 12.5, "unit_no": "OFFICE-201", "type": "COMMERCIAL_OFFICE", "area": 600.0, "owner": "Microsoft Systems IDC", "val": 54000000.0},
            {"floor": 3, "name": "3rd Floor Fintech Wing", "strata": "V3", "z_min": 12.5, "z_max": 16.5, "unit_no": "OFFICE-301", "type": "COMMERCIAL_OFFICE", "area": 600.0, "owner": "Razorpay Software Pvt Ltd", "val": 55000000.0},
            {"floor": 4, "name": "Rooftop Helipad & Sky Lounge", "strata": "V4", "z_min": 16.5, "z_max": 20.0, "unit_no": "AIR-HELIPAD-01", "type": "AIR_ROOFTOP", "area": 400.0, "owner": "Pawan Hans Aviation / DIAL", "val": 22000000.0},
        ]

        for mu in metro_units:
            ulpin_3d = generate_3d_ulpin(
                base_2d_ulpin=parcel2.ulpin_2d,
                floor_number=mu['floor'],
                unit_identifier=mu['unit_no'],
                z_min_meters=mu['z_min'],
                z_max_meters=mu['z_max'],
                unit_type=mu['type']
            )

            h = round(mu['z_max'] - mu['z_min'], 2)
            vol = round(mu['area'] * h, 2)

            unit_obj = VerticalPropertyUnit.objects.create(
                building=bldg2,
                ulpin_3d=ulpin_3d,
                unit_number=mu['unit_no'],
                strata_type=mu['strata'],
                floor_number=mu['floor'],
                floor_name=mu['name'],
                unit_type=mu['type'],
                z_min_meters=mu['z_min'],
                z_max_meters=mu['z_max'],
                carpet_area_sqm=round(mu['area'] * 0.82, 1),
                built_up_area_sqm=mu['area'],
                volume_cubic_meters=vol,
                undivided_share_land_pct=round(100.0 / len(metro_units), 2),
                status="REGISTERED" if "Metro" not in mu['owner'] else "GOVERNMENT",
                property_tax_status="PAID" if "Metro" not in mu['owner'] else "EXEMPT",
                market_valuation_inr=mu['val']
            )

            PropertyOwnership.objects.create(
                unit=unit_obj,
                owner_name=mu['owner'],
                owner_type='GOVERNMENT' if 'Metro' in mu['owner'] or 'Aviation' in mu['owner'] else 'CORPORATE',
                identity_masked="CORP-CENTRAL-REG",
                registered_deed_no=f"REG/DEL/2023/MTR-{unit_obj.id}",
                registration_date=timezone.now().date(),
                registration_authority="Sub-Registrar Office IX, Vasant Vihar Delhi",
                ownership_share_pct=100.0,
                is_primary_owner=True
            )

        # -------------------------------------------------------------------------
        # PARCEL 3: Encroachment & Volumetric Violation Demo Tower (Greater Noida)
        # Built to demonstrate automated 3D spatial conflict & height breach detection!
        # -------------------------------------------------------------------------
        self.stdout.write("Creating Parcel 3: Spatial Conflict Violation Tower (Greater Noida)...")
        lat3, lng3 = 28.6012, 77.4428
        ulpin3_2d = generate_2d_base_ulpin("09", lat3, lng3, "KHASRA-GN-904")
        
        boundary3 = [
            [lng3 - 0.0005, lat3 - 0.0005],
            [lng3 + 0.0005, lat3 - 0.0005],
            [lng3 + 0.0005, lat3 + 0.0005],
            [lng3 - 0.0005, lat3 + 0.0005],
            [lng3 - 0.0005, lat3 - 0.0005]
        ]
        
        parcel3 = LandParcel.objects.create(
            ulpin_2d=ulpin3_2d,
            khasra_survey_no="Khasra No. 192/4, TechZone",
            zone=zone_up,
            address="Plot GH-08, TechZone 4, Greater Noida West",
            land_use="RESIDENTIAL",
            total_area_sqm=3600.0,
            centroid_lat=lat3,
            centroid_lng=lng3,
            boundary_geojson=json.dumps(boundary3),
            sanctioned_max_height_m=35.0,  # MAXIMUM PERMITTED: 35.0m
            sanctioned_far=2.75
        )

        bldg3 = BuildingStructure.objects.create(
            parcel=parcel3,
            name="Green Valley Apex Tower",
            structure_type="HIGH_RISE_RESIDENTIAL",
            footprint_geojson=json.dumps([
                [lng3 - 0.0003, lat3 - 0.0003],
                [lng3 + 0.0003, lat3 - 0.0003],
                [lng3 + 0.0003, lat3 + 0.0003],
                [lng3 - 0.0003, lat3 + 0.0003],
                [lng3 - 0.0003, lat3 - 0.0003]
            ]),
            ground_elevation_msl=201.0,
            total_floors_above_ground=14,  # Actual constructed floors
            basement_levels=1,
            total_height_m=44.8,  # VIOLATES 35.0m LIMIT BY +9.8m!
            sanction_order_no="GNIDA/PLG/2021/BP-3312",
            occupancy_certificate_status="VIOLATION",
            completion_year=2024
        )

        # Create basic floors + unauthorized upper floors
        # Normal floors 1 to 9 (Up to ~30m)
        unit_conflicts = []
        for flr in range(1, 10):
            z_b = (flr - 1) * 3.2
            z_t = z_b + 3.2
            u_obj = VerticalPropertyUnit.objects.create(
                building=bldg3,
                ulpin_3d=generate_3d_ulpin(parcel3.ulpin_2d, flr, f"U{flr}01", z_b, z_t, "RESIDENTIAL_2BHK"),
                unit_number=f"Flat-{flr}01",
                strata_type="V3",
                floor_number=flr,
                floor_name=f"{flr}th Floor",
                unit_type="RESIDENTIAL_2BHK",
                z_min_meters=round(z_b, 2),
                z_max_meters=round(z_t, 2),
                carpet_area_sqm=90.0,
                built_up_area_sqm=115.0,
                volume_cubic_meters=round(115.0 * 3.2, 2),
                undivided_share_land_pct=7.0,
                status="REGISTERED",
                property_tax_status="PAID",
                market_valuation_inr=6500000.0
            )
            PropertyOwnership.objects.create(
                unit=u_obj,
                owner_name=f"Resident {flr}01",
                owner_type="INDIVIDUAL",
                identity_masked=f"XXXX-XXXX-{6000+flr}",
                registered_deed_no=f"REG/UP/2024/{6000+flr}",
                registration_date=timezone.now().date(),
                registration_authority="Sub-Registrar Dadri",
                ownership_share_pct=100.0
            )

        # UNAUTHORIZED FLOORS 11, 12, 13, 14 (Exceeding 35m Sanctioned Height!)
        unauth_flrs = [
            (11, 35.2, 38.4, "Flat-1101 (Unauthorized Strata)"),
            (12, 38.4, 41.6, "Flat-1201 (Unauthorized Strata)"),
            (13, 41.6, 44.8, "Flat-1301 (Unauthorized Strata)"),
        ]

        for f_num, zb, zt, uname in unauth_flrs:
            u_viol = VerticalPropertyUnit.objects.create(
                building=bldg3,
                ulpin_3d=generate_3d_ulpin(parcel3.ulpin_2d, f_num, f"UNAUTH-{f_num}", zb, zt, "PENTHOUSE"),
                unit_number=uname,
                strata_type="V3",
                floor_number=f_num,
                floor_name=f"{f_num}th Floor (Unauthorized)",
                unit_type="PENTHOUSE",
                z_min_meters=round(zb, 2),
                z_max_meters=round(zt, 2),
                carpet_area_sqm=120.0,
                built_up_area_sqm=150.0,
                volume_cubic_meters=round(150.0 * 3.2, 2),
                undivided_share_land_pct=0.0,
                status="DISPUTED",
                property_tax_status="DUE",
                market_valuation_inr=9500000.0
            )
            unit_conflicts.append(u_viol)

            EncumbranceDispute.objects.create(
                unit=u_viol,
                dispute_type="UNAUTHORIZED_EXTENSION",
                filing_authority="Greater Noida Industrial Development Authority (GNIDA)",
                case_reference_no=f"GNIDA/ENF/2024/DEMO-NOTICE-{f_num}",
                status="ACTIVE",
                description=f"Demolition notice issued for constructing vertical strata exceeding sanctioned 35.0m building height."
            )

        # Log Spatial Encroachments
        SpatialEncroachmentLog.objects.create(
            building=bldg3,
            conflict_type="MAX_HEIGHT_EXCEEDED",
            severity="CRITICAL",
            overlap_volume_m3=1440.0,
            details=f"Structure height is 44.8m, exceeding sanctioned Master Plan height of 35.0m by 9.8m (+28% breach). Floors 11-13 encroach into regulated air space."
        )

        SpatialEncroachmentLog.objects.create(
            building=bldg3,
            unit_primary=unit_conflicts[0],
            conflict_type="STRATA_ENCROACHMENT",
            severity="CRITICAL",
            overlap_volume_m3=480.0,
            details=f"Unit {unit_conflicts[0].unit_number} (Z=35.2m to 38.4m) constructed outside sanctioned Master Plan envelope."
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded Cadastre database! "
            f"Parcels: {LandParcel.objects.count()}, "
            f"Buildings: {BuildingStructure.objects.count()}, "
            f"3D Units: {VerticalPropertyUnit.objects.count()}, "
            f"Ownerships: {PropertyOwnership.objects.count()}, "
            f"Disputes: {EncumbranceDispute.objects.count()}, "
            f"Spatial Conflicts: {SpatialEncroachmentLog.objects.count()}"
        ))
