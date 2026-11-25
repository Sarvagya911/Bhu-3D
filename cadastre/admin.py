from django.contrib import admin
from .models import (
    CadastralZone,
    LandParcel,
    BuildingStructure,
    VerticalPropertyUnit,
    PropertyOwnership,
    EncumbranceDispute,
    SpatialEncroachmentLog,
)

@admin.register(CadastralZone)
class CadastralZoneAdmin(admin.ModelAdmin):
    list_display = ('village_or_ward', 'district', 'state_name', 'state_code', 'master_plan_zone')
    search_fields = ('village_or_ward', 'district', 'pincode')


@admin.register(LandParcel)
class LandParcelAdmin(admin.ModelAdmin):
    list_display = ('ulpin_2d', 'khasra_survey_no', 'zone', 'land_use', 'total_area_sqm', 'sanctioned_max_height_m')
    search_fields = ('ulpin_2d', 'khasra_survey_no', 'address')
    list_filter = ('land_use', 'zone__district')


@admin.register(BuildingStructure)
class BuildingStructureAdmin(admin.ModelAdmin):
    list_display = ('name', 'parcel', 'structure_type', 'total_floors_above_ground', 'basement_levels', 'total_height_m', 'occupancy_certificate_status')
    search_fields = ('name', 'parcel__ulpin_2d', 'sanction_order_no')
    list_filter = ('structure_type', 'occupancy_certificate_status')


@admin.register(VerticalPropertyUnit)
class VerticalPropertyUnitAdmin(admin.ModelAdmin):
    list_display = ('ulpin_3d', 'unit_number', 'building', 'strata_type', 'floor_number', 'unit_type', 'built_up_area_sqm', 'status', 'property_tax_status')
    search_fields = ('ulpin_3d', 'unit_number', 'building__name', 'building__parcel__ulpin_2d')
    list_filter = ('strata_type', 'unit_type', 'status', 'property_tax_status')


@admin.register(PropertyOwnership)
class PropertyOwnershipAdmin(admin.ModelAdmin):
    list_display = ('owner_name', 'unit', 'owner_type', 'ownership_share_pct', 'registered_deed_no', 'registration_date')
    search_fields = ('owner_name', 'unit__ulpin_3d', 'registered_deed_no', 'identity_masked')
    list_filter = ('owner_type',)


@admin.register(EncumbranceDispute)
class EncumbranceDisputeAdmin(admin.ModelAdmin):
    list_display = ('unit', 'dispute_type', 'filing_authority', 'case_reference_no', 'status', 'reported_date')
    search_fields = ('unit__ulpin_3d', 'case_reference_no', 'filing_authority')
    list_filter = ('dispute_type', 'status')


@admin.register(SpatialEncroachmentLog)
class SpatialEncroachmentLogAdmin(admin.ModelAdmin):
    list_display = ('building', 'conflict_type', 'severity', 'overlap_volume_m3', 'detected_at')
    list_filter = ('conflict_type', 'severity')
