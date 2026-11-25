from django.test import TestCase, Client
from django.urls import reverse
import json

from .models import (
    CadastralZone,
    LandParcel,
    BuildingStructure,
    VerticalPropertyUnit,
    PropertyOwnership,
    SpatialEncroachmentLog
)
from .ulpin_engine import (
    generate_2d_base_ulpin,
    generate_3d_ulpin,
    parse_3d_ulpin,
    compute_luhn36_checksum,
    STRATA_SUBTERRANEAN,
    STRATA_SUPERSTRUCTURE,
)


class UlpinEngineTests(TestCase):
    def test_2d_base_ulpin_format(self):
        ulpin_2d = generate_2d_base_ulpin("07", 28.5355, 77.2410, "KHASRA-102")
        self.assertEqual(len(ulpin_2d), 14)
        self.assertTrue(ulpin_2d.startswith("07"))

    def test_3d_ulpin_generation_and_parsing(self):
        base_ulpin = "07DL4920183746"
        ulpin_3d = generate_3d_ulpin(
            base_2d_ulpin=base_ulpin,
            floor_number=5,
            unit_identifier="Flat-502",
            z_min_meters=15.0,
            z_max_meters=18.3,
            unit_type="RESIDENTIAL_3BHK"
        )
        self.assertIn(base_ulpin, ulpin_3d)
        self.assertIn("V3", ulpin_3d)
        self.assertIn("F05", ulpin_3d)
        self.assertIn("U502", ulpin_3d)

        # Parse back
        parsed = parse_3d_ulpin(ulpin_3d)
        self.assertTrue(parsed['valid'])
        self.assertEqual(parsed['base_2d_ulpin'], base_ulpin)
        self.assertEqual(parsed['strata_code'], "V3")
        self.assertEqual(parsed['floor_code'], "F05")
        self.assertTrue(parsed['checksum_valid'])

    def test_subterranean_strata_code(self):
        base_ulpin = "06GG0184920184"
        ulpin_sub = generate_3d_ulpin(
            base_2d_ulpin=base_ulpin,
            floor_number=-2,
            unit_identifier="B2-P01",
            z_min_meters=-6.4,
            z_max_meters=-3.2,
            unit_type="BASEMENT_PARKING"
        )
        self.assertIn("V1", ulpin_sub)
        self.assertIn("B02", ulpin_sub)


class CadastreViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.zone = CadastralZone.objects.create(
            state_name="Delhi",
            state_code="07",
            district="South West Delhi",
            village_or_ward="Aerocity Ward",
            pincode="110037"
        )
        self.parcel = LandParcel.objects.create(
            ulpin_2d="07DL0149021842",
            khasra_survey_no="Khasra 42/1",
            zone=self.zone,
            address="Plot 42, Aerocity Hub",
            total_area_sqm=5000.0,
            centroid_lat=28.5524,
            centroid_lng=77.1215,
            boundary_geojson="[[77.12, 28.55], [77.13, 28.55], [77.13, 28.56], [77.12, 28.56], [77.12, 28.55]]",
            sanctioned_max_height_m=45.0,
            sanctioned_far=3.0
        )
        self.building = BuildingStructure.objects.create(
            parcel=self.parcel,
            name="Aerocity Tower Alpha",
            footprint_geojson="[[77.12, 28.55], [77.13, 28.55], [77.13, 28.56], [77.12, 28.56], [77.12, 28.55]]",
            ground_elevation_msl=220.0,
            total_floors_above_ground=8,
            basement_levels=1,
            total_height_m=28.0
        )
        self.unit = VerticalPropertyUnit.objects.create(
            building=self.building,
            ulpin_3d="07DL0149021842-V3-F02-U201-Z0609-AB",
            unit_number="Flat-201",
            strata_type="V3",
            floor_number=2,
            floor_name="2nd Floor",
            unit_type="RESIDENTIAL_3BHK",
            z_min_meters=6.0,
            z_max_meters=9.3,
            carpet_area_sqm=110.0,
            built_up_area_sqm=140.0,
            volume_cubic_meters=462.0,
            undivided_share_land_pct=5.0,
            status="REGISTERED",
            property_tax_status="PAID",
            market_valuation_inr=9000000.0
        )
        self.ownership = PropertyOwnership.objects.create(
            unit=self.unit,
            owner_name="Vikram Seth",
            owner_type="INDIVIDUAL",
            identity_masked="XXXX-XXXX-4412",
            registered_deed_no="REG/DEL/2024/9912",
            ownership_share_pct=100.0
        )

    def test_dashboard_page(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "3D ULPIN & Vertical Property Mapping")
        self.assertContains(response, self.parcel.ulpin_2d)

    def test_explorer_3d_page(self):
        response = self.client.get(reverse('explorer_3d'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "3D Cadastre Explorer")
        self.assertContains(response, "canvas-container")

    def test_bhu_aadhaar_card(self):
        response = self.client.get(reverse('bhu_aadhaar_card', kwargs={'ulpin_3d': self.unit.ulpin_3d}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.unit.ulpin_3d)
        self.assertContains(response, "Vikram Seth")
        self.assertContains(response, "DIGITAL 3D BHU-AADHAAR PROPERTY CERTIFICATE")

    def test_spatial_audit_page(self):
        response = self.client.get(reverse('spatial_audit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Spatial Audit")

    def test_public_search_page(self):
        response = self.client.get(reverse('public_search') + f"?q={self.unit.ulpin_3d}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.unit.ulpin_3d)

    def test_api_parcel_3d_data(self):
        response = self.client.get(reverse('api_parcel_3d_data', kwargs={'parcel_id': self.parcel.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('parcel', data)
        self.assertIn('buildings', data)
        self.assertEqual(len(data['buildings'][0]['units']), 1)
        self.assertEqual(data['buildings'][0]['units'][0]['ulpin_3d'], self.unit.ulpin_3d)

    def test_api_verify_ulpin(self):
        response = self.client.get(reverse('api_verify_ulpin', kwargs={'ulpin_3d': self.unit.ulpin_3d}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_registered_in_cadastre'])
