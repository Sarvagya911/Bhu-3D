from django.db import models
from django.utils import timezone
import json
from .ulpin_engine import generate_3d_ulpin, parse_3d_ulpin, STRATA_LABELS


class CadastralZone(models.Model):
    """
    Administrative and Master Plan Cadastral Zone.
    """
    state_name = models.CharField(max_length=64, default="Delhi")
    state_code = models.CharField(max_length=4, default="07")
    district = models.CharField(max_length=64, default="South West Delhi")
    tehsil = models.CharField(max_length=64, default="Vasant Vihar")
    village_or_ward = models.CharField(max_length=128, default="Sector 21 Urban Estate")
    pincode = models.CharField(max_length=10, default="110077")
    master_plan_zone = models.CharField(max_length=32, default="Zone K-II (Mixed Use)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.village_or_ward}, {self.district} ({self.state_code})"


class LandParcel(models.Model):
    """
    2D Base Land Parcel representing terrestrial cadastral surface boundary.
    """
    LAND_USE_CHOICES = [
        ('RESIDENTIAL', 'Residential'),
        ('COMMERCIAL', 'Commercial'),
        ('MIXED_USE', 'Mixed-Use (Commercial & Residential)'),
        ('INSTITUTIONAL', 'Institutional / Government'),
        ('INDUSTRIAL', 'Industrial'),
        ('AGRICULTURAL', 'Agricultural'),
    ]

    ulpin_2d = models.CharField(max_length=20, unique=True, db_index=True, verbose_name="Base 14-Digit ULPIN")
    khasra_survey_no = models.CharField(max_length=64, verbose_name="Khasra / Survey Number")
    zone = models.ForeignKey(CadastralZone, on_delete=models.CASCADE, related_name='parcels')
    address = models.CharField(max_length=255)
    land_use = models.CharField(max_length=32, choices=LAND_USE_CHOICES, default='MIXED_USE')
    total_area_sqm = models.FloatField(help_text="Total ground surface area in square meters")
    centroid_lat = models.FloatField()
    centroid_lng = models.FloatField()
    boundary_geojson = models.TextField(help_text="GeoJSON Polygon coordinates [[lng, lat], ...]")
    
    # Master Plan Regulatory Limits
    sanctioned_max_height_m = models.FloatField(default=45.0, help_text="Maximum permissible building height (m)")
    sanctioned_far = models.FloatField(default=3.0, help_text="Sanctioned Floor Area Ratio")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ULPIN {self.ulpin_2d} - {self.khasra_survey_no}"

    @property
    def boundary_coords(self):
        try:
            return json.loads(self.boundary_geojson)
        except Exception:
            return []


class BuildingStructure(models.Model):
    """
    Physical structure constructed over the 2D parcel containing 3D vertical strata.
    """
    STRUCTURE_TYPE_CHOICES = [
        ('HIGH_RISE_RESIDENTIAL', 'High-Rise Residential Tower'),
        ('COMMERCIAL_COMPLEX', 'Commercial IT / Retail Mall'),
        ('MIXED_TOWER', 'Mixed Use Residential & Retail'),
        ('INSTITUTIONAL', 'Institutional / Public Infrastructure'),
    ]

    OC_STATUS_CHOICES = [
        ('APPROVED', 'Occupancy Certificate Issued'),
        ('PROVISIONAL', 'Provisional / In Progress'),
        ('PENDING', 'Pending Fire / Safety Clearance'),
        ('VIOLATION', 'Notice Issued for Height/FAR Violation'),
    ]

    parcel = models.ForeignKey(LandParcel, on_delete=models.CASCADE, related_name='buildings')
    name = models.CharField(max_length=128, verbose_name="Structure / Tower Name")
    structure_type = models.CharField(max_length=32, choices=STRUCTURE_TYPE_CHOICES, default='HIGH_RISE_RESIDENTIAL')
    footprint_geojson = models.TextField(help_text="Building ground footprint coordinates")
    ground_elevation_msl = models.FloatField(default=214.0, help_text="Plinth elevation above Mean Sea Level (meters)")
    total_floors_above_ground = models.IntegerField(default=10)
    basement_levels = models.IntegerField(default=2, help_text="Number of subterranean basement levels")
    total_height_m = models.FloatField(default=35.0, help_text="Total structural height above ground (meters)")
    sanction_order_no = models.CharField(max_length=64, default="DTCP/ND/2023/BLD-4910")
    occupancy_certificate_status = models.CharField(max_length=20, choices=OC_STATUS_CHOICES, default='APPROVED')
    completion_year = models.IntegerField(default=2024)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} on Parcel {self.parcel.ulpin_2d}"

    @property
    def footprint_coords(self):
        try:
            return json.loads(self.footprint_geojson)
        except Exception:
            return []


class VerticalPropertyUnit(models.Model):
    """
    The Volumetric 3D Property Parcel Unit (ISO 19152 LADM 3D Cadastre compliant).
    """
    STRATA_CHOICES = [
        ('V1', 'Subterranean Strata (-Z: Basement/Underground)'),
        ('V2', 'Ground Plane Strata (Plinth level)'),
        ('V3', 'Superstructure Strata (+Z: Floors 1..N)'),
        ('V4', 'Air Rights / Rooftop Strata'),
    ]

    UNIT_TYPE_CHOICES = [
        ('RESIDENTIAL_2BHK', 'Residential Flat (2 BHK)'),
        ('RESIDENTIAL_3BHK', 'Residential Flat (3 BHK)'),
        ('RESIDENTIAL_4BHK', 'Residential Flat (4 BHK Deluxe)'),
        ('PENTHOUSE', 'Penthouse Suite'),
        ('COMMERCIAL_OFFICE', 'Commercial Office Space'),
        ('RETAIL_SHOP', 'Retail Shop / Showroom'),
        ('BASEMENT_PARKING', 'Subterranean Parking Bay'),
        ('COMMON_UTILITY', 'Common Facilities / Club / Service Area'),
        ('AIR_ROOFTOP', 'Rooftop Solar & Telecommunication Strata'),
    ]

    STATUS_CHOICES = [
        ('REGISTERED', 'Registered & Clear Title'),
        ('MORTGAGED', 'Mortgaged / Lien Enforced'),
        ('DISPUTED', 'Litigation / Disputed Title'),
        ('GOVERNMENT', 'Government / Common Public Property'),
    ]

    TAX_STATUS_CHOICES = [
        ('PAID', 'Property Tax Fully Paid'),
        ('DUE', 'Assessment Due / In Arrears'),
        ('EXEMPT', 'Exempted (Common Facility)'),
    ]

    building = models.ForeignKey(BuildingStructure, on_delete=models.CASCADE, related_name='units')
    ulpin_3d = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="3D ULPIN")
    unit_number = models.CharField(max_length=32, verbose_name="Unit / Flat / Office Number")
    strata_type = models.CharField(max_length=4, choices=STRATA_CHOICES, default='V3')
    floor_number = models.IntegerField(default=1, help_text="Floor index: -2, -1, 0, 1, 2... etc")
    floor_name = models.CharField(max_length=32, default="1st Floor")
    unit_type = models.CharField(max_length=32, choices=UNIT_TYPE_CHOICES, default='RESIDENTIAL_3BHK')
    
    # 3D Volumetric Extents
    z_min_meters = models.FloatField(help_text="Lower vertical elevation boundary in meters above building datum")
    z_max_meters = models.FloatField(help_text="Upper vertical elevation boundary in meters above building datum")
    z_min_msl = models.FloatField(null=True, blank=True, help_text="Lower elevation above Mean Sea Level (m)")
    z_max_msl = models.FloatField(null=True, blank=True, help_text="Upper elevation above Mean Sea Level (m)")
    
    # Spatial Areas and Volumes
    carpet_area_sqm = models.FloatField(help_text="Net usable carpet area in square meters")
    built_up_area_sqm = models.FloatField(help_text="Plinth/Super built-up area in square meters")
    volume_cubic_meters = models.FloatField(help_text="Volumetric spatial capacity (m3)")
    undivided_share_land_pct = models.FloatField(default=0.0, help_text="Proportional Undivided Share of Land (UDS %)")
    
    unit_footprint_geojson = models.TextField(blank=True, null=True, help_text="Horizontal 2D footprint slice of this unit")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REGISTERED')
    property_tax_status = models.CharField(max_length=10, choices=TAX_STATUS_CHOICES, default='PAID')
    market_valuation_inr = models.DecimalField(max_digits=14, decimal_places=2, default=7500000.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['floor_number', 'unit_number']

    def __str__(self):
        return f"{self.unit_number} ({self.ulpin_3d})"

    @property
    def height_meters(self):
        return round(self.z_max_meters - self.z_min_meters, 2)

    @property
    def strata_label(self):
        return STRATA_LABELS.get(self.strata_type, self.strata_type)

    def save(self, *args, **kwargs):
        # Auto-calculate MSL if not set
        if self.building and self.building.ground_elevation_msl:
            if not self.z_min_msl:
                self.z_min_msl = round(self.building.ground_elevation_msl + self.z_min_meters, 2)
            if not self.z_max_msl:
                self.z_max_msl = round(self.building.ground_elevation_msl + self.z_max_meters, 2)
        
        # Auto-compute volume if not provided
        if not self.volume_cubic_meters and self.built_up_area_sqm:
            h = max(0.5, self.z_max_meters - self.z_min_meters)
            self.volume_cubic_meters = round(self.built_up_area_sqm * h, 2)

        # Auto-generate 3D ULPIN if not present
        if not self.ulpin_3d and self.building and self.building.parcel:
            self.ulpin_3d = generate_3d_ulpin(
                base_2d_ulpin=self.building.parcel.ulpin_2d,
                floor_number=self.floor_number,
                unit_identifier=self.unit_number,
                z_min_meters=self.z_min_meters,
                z_max_meters=self.z_max_meters,
                unit_type=self.unit_type
            )
            
        super().save(*args, **kwargs)


class PropertyOwnership(models.Model):
    """
    Legal ownership rights linked to the 3D Volumetric Unit.
    """
    OWNER_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual Citizen'),
        ('JOINT', 'Joint Ownership'),
        ('CORPORATE', 'Corporate / Company'),
        ('GOVERNMENT', 'Government Department'),
        ('RWA', 'Resident Welfare Association / Society'),
    ]

    unit = models.ForeignKey(VerticalPropertyUnit, on_delete=models.CASCADE, related_name='ownerships')
    owner_name = models.CharField(max_length=128)
    owner_type = models.CharField(max_length=20, choices=OWNER_TYPE_CHOICES, default='INDIVIDUAL')
    identity_masked = models.CharField(max_length=32, help_text="Masked Aadhaar (e.g. XXXX-XXXX-8912) or PAN")
    registered_deed_no = models.CharField(max_length=64, default="REG/2024/SRO-IV/7841")
    registration_date = models.DateField(default=timezone.now)
    registration_authority = models.CharField(max_length=128, default="Sub-Registrar Office IV, South West Delhi")
    ownership_share_pct = models.FloatField(default=100.0)
    is_primary_owner = models.BooleanField(default=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=16, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner_name} - {self.unit.unit_number} ({self.ownership_share_pct}%)"


class EncumbranceDispute(models.Model):
    """
    Mortgages, Bank Liens, Court Stays, or Municipal notices on a 3D unit.
    """
    DISPUTE_TYPE_CHOICES = [
        ('MORTGAGE', 'Bank Home Loan Mortgage / Charge'),
        ('COURT_STAY', 'Civil Court Injunction / Stay Order'),
        ('ENCROACHMENT', 'Volumetric Overlap / Encroachment Notice'),
        ('UNAUTHORIZED_EXTENSION', 'Unauthorized Vertical Strata Extension'),
        ('TAX_DEFAULT', 'Municipal Property Tax Default Notice'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active / In Force'),
        ('RESOLVED', 'Discharged / Released'),
        ('HEARING', 'Under Judicial Hearing'),
    ]

    unit = models.ForeignKey(VerticalPropertyUnit, on_delete=models.CASCADE, related_name='disputes')
    dispute_type = models.CharField(max_length=32, choices=DISPUTE_TYPE_CHOICES, default='MORTGAGE')
    filing_authority = models.CharField(max_length=128, default="State Bank of India (RACPC New Delhi)")
    case_reference_no = models.CharField(max_length=64, default="SBI/HL/2023/90124")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='ACTIVE')
    description = models.TextField()
    reported_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_dispute_type_display()} on {self.unit.unit_number}"


class SpatialEncroachmentLog(models.Model):
    """
    Automated Volumetric Conflict & Height Limit Violation Detection Log.
    """
    CONFLICT_TYPE_CHOICES = [
        ('VOLUMETRIC_OVERLAP', '3D Volumetric Overlap between Adjacent Units'),
        ('MAX_HEIGHT_EXCEEDED', 'Building Exceeds Master Plan Sanctioned Height'),
        ('FAR_VIOLATION', 'Floor Area Ratio Exceeds Permissible Limit'),
        ('STRATA_ENCROACHMENT', 'Unauthorized Strata Intrusion into Public Air Rights / Subsurface'),
    ]

    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical Regulatory Violation'),
        ('WARNING', 'Warning / Minor Boundary Deviation'),
        ('COMPLIANT', 'Spatial Verification Passed'),
    ]

    building = models.ForeignKey(BuildingStructure, on_delete=models.CASCADE, related_name='encroachment_logs')
    unit_primary = models.ForeignKey(VerticalPropertyUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='primary_conflicts')
    unit_secondary = models.ForeignKey(VerticalPropertyUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='secondary_conflicts')
    conflict_type = models.CharField(max_length=32, choices=CONFLICT_TYPE_CHOICES)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default='CRITICAL')
    overlap_volume_m3 = models.FloatField(default=0.0)
    details = models.TextField()
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.conflict_type} ({self.severity}) in {self.building.name}"
