import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Avg
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import (
    CadastralZone,
    LandParcel,
    BuildingStructure,
    VerticalPropertyUnit,
    PropertyOwnership,
    EncumbranceDispute,
    SpatialEncroachmentLog,
)
from .ulpin_engine import (
    generate_2d_base_ulpin,
    generate_3d_ulpin,
    parse_3d_ulpin,
    STRATA_LABELS,
    STATE_CODES,
    compute_luhn36_checksum,
)


def dashboard_view(request):
    """
    Executive National & Regional Cadastre Dashboard.
    """
    total_parcels = LandParcel.objects.count()
    total_buildings = BuildingStructure.objects.count()
    total_units = VerticalPropertyUnit.objects.count()
    total_volume = VerticalPropertyUnit.objects.aggregate(v=Sum('volume_cubic_meters'))['v'] or 0.0
    total_land_area = LandParcel.objects.aggregate(a=Sum('total_area_sqm'))['a'] or 0.0
    
    # Strata breakdown
    strata_counts = {
        'V1': VerticalPropertyUnit.objects.filter(strata_type='V1').count(),
        'V2': VerticalPropertyUnit.objects.filter(strata_type='V2').count(),
        'V3': VerticalPropertyUnit.objects.filter(strata_type='V3').count(),
        'V4': VerticalPropertyUnit.objects.filter(strata_type='V4').count(),
    }
    
    # Status breakdown
    registered_count = VerticalPropertyUnit.objects.filter(status='REGISTERED').count()
    mortgaged_count = VerticalPropertyUnit.objects.filter(status='MORTGAGED').count()
    disputed_count = VerticalPropertyUnit.objects.filter(status='DISPUTED').count()
    govt_count = VerticalPropertyUnit.objects.filter(status='GOVERNMENT').count()
    
    # Active conflicts
    conflicts_count = SpatialEncroachmentLog.objects.count()
    
    parcels = LandParcel.objects.select_related('zone').prefetch_related('buildings__units').all()
    recent_units = VerticalPropertyUnit.objects.select_related('building__parcel').order_by('-created_at')[:8]

    context = {
        'total_parcels': total_parcels,
        'total_buildings': total_buildings,
        'total_units': total_units,
        'total_volume': round(total_volume, 1),
        'total_land_area': round(total_land_area, 1),
        'strata_counts': strata_counts,
        'registered_count': registered_count,
        'mortgaged_count': mortgaged_count,
        'disputed_count': disputed_count,
        'govt_count': govt_count,
        'conflicts_count': conflicts_count,
        'parcels': parcels,
        'recent_units': recent_units,
    }
    return render(request, 'dashboard.html', context)


def explorer_3d_view(request):
    """
    Full 3D WebGL Geospatial Cadastre Explorer using Three.js.
    """
    parcels = LandParcel.objects.prefetch_related('buildings__units').all()
    selected_parcel_id = request.GET.get('parcel_id')
    selected_unit_id = request.GET.get('unit_id')
    
    if selected_parcel_id:
        active_parcel = get_object_or_404(LandParcel, id=selected_parcel_id)
    else:
        active_parcel = parcels.first()
        
    context = {
        'parcels': parcels,
        'active_parcel': active_parcel,
        'selected_unit_id': selected_unit_id or '',
    }
    return render(request, 'explorer_3d.html', context)


def officer_required(view_func):
    """Restricts access to authenticated government officers/staff."""
    return user_passes_test(
        lambda u: u.is_active and u.is_staff,
        login_url='/officer-login/'
    )(view_func)


def officer_login_view(request):
    """Login portal for authorized DoLR officers, surveyors, and registrars."""
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f"Signed in as Officer '{user.username}'.")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard')
        messages.error(request, "Invalid officer credentials or insufficient permissions.")

    return render(request, 'officer_login.html', {'next': next_url})


def officer_logout_view(request):
    """Logs out the currently signed-in officer."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, "You have been signed out.")
    return redirect('dashboard')


@officer_required
def ulpin_generator_view(request):
    """
    Interactive 3D ULPIN Generator & Batch Synthesis Tool.
    """
    parcels = LandParcel.objects.all()
    generated_result = None
    
    if request.method == 'POST' and 'generate_single' in request.POST:
        parcel_id = request.POST.get('parcel_id')
        floor_num = int(request.POST.get('floor_number', 1))
        unit_no = request.POST.get('unit_number', '101')
        z_min = float(request.POST.get('z_min', 3.0))
        z_max = float(request.POST.get('z_max', 6.2))
        unit_type = request.POST.get('unit_type', 'RESIDENTIAL_3BHK')
        
        parcel = get_object_or_404(LandParcel, id=parcel_id)
        ulpin_3d = generate_3d_ulpin(
            base_2d_ulpin=parcel.ulpin_2d,
            floor_number=floor_num,
            unit_identifier=unit_no,
            z_min_meters=z_min,
            z_max_meters=z_max,
            unit_type=unit_type
        )
        
        parsed = parse_3d_ulpin(ulpin_3d)
        generated_result = {
            'ulpin_3d': ulpin_3d,
            'parcel': parcel,
            'floor_num': floor_num,
            'unit_no': unit_no,
            'z_min': z_min,
            'z_max': z_max,
            'height': round(z_max - z_min, 2),
            'unit_type': unit_type,
            'parsed': parsed,
        }
        
        # Save to DB if requested
        if request.POST.get('save_to_db') == 'yes':
            building = parcel.buildings.first()
            if not building:
                building = BuildingStructure.objects.create(
                    parcel=parcel,
                    name=f"Structure on {parcel.khasra_survey_no}",
                    footprint_geojson=parcel.boundary_geojson,
                    ground_elevation_msl=210.0,
                    total_floors_above_ground=max(1, floor_num),
                    total_height_m=max(z_max, 10.0)
                )
                
            unit_obj, created = VerticalPropertyUnit.objects.get_or_create(
                ulpin_3d=ulpin_3d,
                defaults={
                    'building': building,
                    'unit_number': unit_no,
                    'strata_type': parsed['strata_code'],
                    'floor_number': floor_num,
                    'floor_name': f"Floor {floor_num}",
                    'unit_type': unit_type,
                    'z_min_meters': z_min,
                    'z_max_meters': z_max,
                    'carpet_area_sqm': 85.0,
                    'built_up_area_sqm': 110.0,
                    'volume_cubic_meters': round(110.0 * (z_max - z_min), 2),
                    'status': 'REGISTERED',
                    'property_tax_status': 'PAID',
                    'market_valuation_inr': 7500000.0,
                }
            )
            messages.success(request, f"3D ULPIN '{ulpin_3d}' generated and registered successfully in Cadastre!")
            return redirect('bhu_aadhaar_card', ulpin_3d=ulpin_3d)

    context = {
        'parcels': parcels,
        'state_codes': STATE_CODES,
        'generated_result': generated_result,
    }
    return render(request, 'ulpin_generator.html', context)


def bhu_aadhaar_card_view(request, ulpin_3d):
    """
    Official Digital 3D Bhu-Aadhaar Certificate (e-RoR / Record of Rights).
    """
    unit = get_object_or_404(VerticalPropertyUnit.objects.select_related('building__parcel__zone'), ulpin_3d=ulpin_3d)
    ownerships = unit.ownerships.all()
    disputes = unit.disputes.all()
    parsed_ulpin = parse_3d_ulpin(unit.ulpin_3d)
    
    verification_url = request.build_absolute_uri()
    
    context = {
        'unit': unit,
        'building': unit.building,
        'parcel': unit.building.parcel,
        'zone': unit.building.parcel.zone,
        'ownerships': ownerships,
        'disputes': disputes,
        'parsed_ulpin': parsed_ulpin,
        'verification_url': verification_url,
        'now': timezone.now(),
    }
    return render(request, 'bhu_aadhaar_card.html', context)


@officer_required
def spatial_audit_view(request):
    """
    Automated 3D Conflict, Height Limit & FAR Encroachment Detection Engine.
    """
    buildings = BuildingStructure.objects.select_related('parcel').prefetch_related('units').all()
    audit_results = []
    
    for bldg in buildings:
        parcel = bldg.parcel
        max_sanctioned_height = parcel.sanctioned_max_height_m
        actual_height = bldg.total_height_m
        
        height_violation = actual_height > max_sanctioned_height
        excess_height = round(actual_height - max_sanctioned_height, 2) if height_violation else 0.0
        
        # Check units constructed above sanctioned height
        violating_units = bldg.units.filter(z_max_meters__gt=max_sanctioned_height)
        
        # Calculate FAR
        total_builtup = bldg.units.aggregate(s=Sum('built_up_area_sqm'))['s'] or 0.0
        actual_far = round(total_builtup / parcel.total_area_sqm, 2) if parcel.total_area_sqm else 0.0
        far_violation = actual_far > parcel.sanctioned_far
        
        # Check for vertical elevation overlaps on same floor
        overlap_conflicts = []
        units_by_floor = {}
        for u in bldg.units.all():
            units_by_floor.setdefault(u.floor_number, []).append(u)
            
        audit_results.append({
            'building': bldg,
            'parcel': parcel,
            'sanctioned_height': max_sanctioned_height,
            'actual_height': actual_height,
            'height_violation': height_violation,
            'excess_height': excess_height,
            'violating_units': violating_units,
            'sanctioned_far': parcel.sanctioned_far,
            'actual_far': actual_far,
            'far_violation': far_violation,
            'total_units': bldg.units.count(),
            'status': 'VIOLATION' if (height_violation or far_violation) else 'COMPLIANT',
        })
        
    logs = SpatialEncroachmentLog.objects.select_related('building', 'unit_primary').order_by('-detected_at')[:20]
    
    context = {
        'audit_results': audit_results,
        'logs': logs,
    }
    return render(request, 'spatial_audit.html', context)


def public_search_view(request):
    """
    Public Citizen Verification Portal for 3D Land & Vertical Property.
    """
    query = request.GET.get('q', '').strip()
    units = []
    parcels = []
    
    if query:
        # Search in 3D units
        units = VerticalPropertyUnit.objects.filter(
            ulpin_3d__icontains=query
        ) | VerticalPropertyUnit.objects.filter(
            unit_number__icontains=query
        ) | VerticalPropertyUnit.objects.filter(
            ownerships__owner_name__icontains=query
        )
        units = units.distinct().select_related('building__parcel')[:20]
        
        # Search in 2D parcels
        parcels = LandParcel.objects.filter(
            ulpin_2d__icontains=query
        ) | LandParcel.objects.filter(
            khasra_survey_no__icontains=query
        ) | LandParcel.objects.filter(
            address__icontains=query
        )[:10]

    context = {
        'query': query,
        'units': units,
        'parcels': parcels,
    }
    return render(request, 'public_search.html', context)


@officer_required
def parcel_builder_view(request):
    """
    Surveyor / Administrator 3D Parcel & Vertical Strata Creator.
    """
    zones = CadastralZone.objects.all()
    
    if request.method == 'POST':
        khasra = request.POST.get('khasra_survey_no')
        zone_id = request.POST.get('zone_id')
        address = request.POST.get('address')
        land_use = request.POST.get('land_use', 'MIXED_USE')
        area = float(request.POST.get('total_area_sqm', 3000.0))
        lat = float(request.POST.get('lat', 28.5355))
        lng = float(request.POST.get('lng', 77.2410))
        sanctioned_height = float(request.POST.get('sanctioned_max_height_m', 45.0))
        sanctioned_far = float(request.POST.get('sanctioned_far', 3.0))
        
        # Structure specs
        building_name = request.POST.get('building_name', 'Bhu Heights')
        floors = int(request.POST.get('floors_above_ground', 5))
        basements = int(request.POST.get('basement_levels', 1))
        floor_height = float(request.POST.get('floor_height_m', 3.3))
        units_per_floor = int(request.POST.get('units_per_floor', 4))
        
        zone = get_object_or_404(CadastralZone, id=zone_id)
        
        # Generate 2D ULPIN
        ulpin_2d = generate_2d_base_ulpin(zone.state_code, lat, lng, khasra)
        
        boundary = [
            [lng - 0.0005, lat - 0.0005],
            [lng + 0.0005, lat - 0.0005],
            [lng + 0.0005, lat + 0.0005],
            [lng - 0.0005, lat + 0.0005],
            [lng - 0.0005, lat - 0.0005]
        ]
        
        parcel = LandParcel.objects.create(
            ulpin_2d=ulpin_2d,
            khasra_survey_no=khasra,
            zone=zone,
            address=address,
            land_use=land_use,
            total_area_sqm=area,
            centroid_lat=lat,
            centroid_lng=lng,
            boundary_geojson=json.dumps(boundary),
            sanctioned_max_height_m=sanctioned_height,
            sanctioned_far=sanctioned_far
        )
        
        bldg = BuildingStructure.objects.create(
            parcel=parcel,
            name=building_name,
            structure_type='HIGH_RISE_RESIDENTIAL',
            footprint_geojson=json.dumps(boundary),
            ground_elevation_msl=215.0,
            total_floors_above_ground=floors,
            basement_levels=basements,
            total_height_m=round(floors * floor_height, 2),
            sanction_order_no=f"SANC/2026/{parcel.id}",
            occupancy_certificate_status='APPROVED'
        )
        
        # Automatically generate units across basements and floors
        total_created = 0
        uds_share = round(100.0 / ((floors + basements) * units_per_floor), 3)
        
        # Basements
        for b in range(basements, 0, -1):
            flr_num = -b
            z_min = -b * floor_height
            z_max = z_min + floor_height
            for u in range(1, units_per_floor + 1):
                u_no = f"B{b}-P0{u}"
                u_ulpin = generate_3d_ulpin(ulpin_2d, flr_num, u_no, z_min, z_max, "BASEMENT_PARKING")
                VerticalPropertyUnit.objects.create(
                    building=bldg,
                    ulpin_3d=u_ulpin,
                    unit_number=u_no,
                    strata_type='V1',
                    floor_number=flr_num,
                    floor_name=f"Basement {b}",
                    unit_type='BASEMENT_PARKING',
                    z_min_meters=z_min,
                    z_max_meters=z_max,
                    carpet_area_sqm=30.0,
                    built_up_area_sqm=40.0,
                    volume_cubic_meters=round(40.0 * floor_height, 2),
                    undivided_share_land_pct=uds_share,
                    status='REGISTERED',
                    property_tax_status='PAID',
                    market_valuation_inr=500000.0
                )
                total_created += 1

        # Above ground floors
        for f in range(1, floors + 1):
            z_min = (f - 1) * floor_height
            z_max = z_min + floor_height
            for u in range(1, units_per_floor + 1):
                u_no = f"{f}0{u}"
                u_ulpin = generate_3d_ulpin(ulpin_2d, f, u_no, z_min, z_max, "RESIDENTIAL_3BHK")
                VerticalPropertyUnit.objects.create(
                    building=bldg,
                    ulpin_3d=u_ulpin,
                    unit_number=f"Flat-{u_no}",
                    strata_type='V3' if f > 0 else 'V2',
                    floor_number=f,
                    floor_name=f"Floor {f}",
                    unit_type='RESIDENTIAL_3BHK',
                    z_min_meters=z_min,
                    z_max_meters=z_max,
                    carpet_area_sqm=120.0,
                    built_up_area_sqm=150.0,
                    volume_cubic_meters=round(150.0 * floor_height, 2),
                    undivided_share_land_pct=uds_share,
                    status='REGISTERED',
                    property_tax_status='PAID',
                    market_valuation_inr=8500000.0
                )
                total_created += 1
                
        messages.success(request, f"New 3D Parcel {ulpin_2d} created with {total_created} vertical units and 3D ULPINs!")
        return redirect(f"/explorer-3d/?parcel_id={parcel.id}")
        
    context = {'zones': zones}
    return render(request, 'parcel_builder.html', context)


# -----------------------------------------------------------------------------
# REST API Endpoints for Three.js & Client Integrations
# -----------------------------------------------------------------------------

def api_parcel_3d_data(request, parcel_id):
    """
    Returns 3D meshes and volumetric coordinates for Three.js rendering.
    """
    parcel = get_object_or_404(LandParcel.objects.prefetch_related('buildings__units__ownerships', 'buildings__units__disputes'), id=parcel_id)
    
    buildings_data = []
    for bldg in parcel.buildings.all():
        units_data = []
        for u in bldg.units.all():
            owner = u.ownerships.first()
            dispute = u.disputes.first()
            units_data.append({
                'id': u.id,
                'ulpin_3d': u.ulpin_3d,
                'unit_number': u.unit_number,
                'strata_type': u.strata_type,
                'strata_label': u.strata_label,
                'floor_number': u.floor_number,
                'floor_name': u.floor_name,
                'unit_type': u.unit_type,
                'unit_type_display': u.get_unit_type_display(),
                'z_min': u.z_min_meters,
                'z_max': u.z_max_meters,
                'height': u.height_meters,
                'carpet_area': u.carpet_area_sqm,
                'built_up_area': u.built_up_area_sqm,
                'volume_m3': u.volume_cubic_meters,
                'uds_pct': u.undivided_share_land_pct,
                'status': u.status,
                'tax_status': u.property_tax_status,
                'valuation_inr': float(u.market_valuation_inr),
                'owner_name': owner.owner_name if owner else 'Government / Common Asset',
                'owner_masked_id': owner.identity_masked if owner else 'N/A',
                'has_dispute': bool(dispute),
                'dispute_summary': f"{dispute.get_dispute_type_display()}: {dispute.description[:60]}..." if dispute else None,
            })
            
        buildings_data.append({
            'id': bldg.id,
            'name': bldg.name,
            'structure_type': bldg.get_structure_type_display(),
            'footprint_coords': bldg.footprint_coords,
            'ground_elevation_msl': bldg.ground_elevation_msl,
            'total_floors': bldg.total_floors_above_ground,
            'basement_levels': bldg.basement_levels,
            'total_height_m': bldg.total_height_m,
            'sanction_order_no': bldg.sanction_order_no,
            'oc_status': bldg.occupancy_certificate_status,
            'units': units_data,
        })
        
    response_data = {
        'parcel': {
            'id': parcel.id,
            'ulpin_2d': parcel.ulpin_2d,
            'khasra': parcel.khasra_survey_no,
            'address': parcel.address,
            'zone': str(parcel.zone),
            'land_use': parcel.get_land_use_display(),
            'total_area_sqm': parcel.total_area_sqm,
            'centroid': [parcel.centroid_lng, parcel.centroid_lat],
            'boundary': parcel.boundary_coords,
            'sanctioned_max_height_m': parcel.sanctioned_max_height_m,
            'sanctioned_far': parcel.sanctioned_far,
        },
        'buildings': buildings_data,
    }
    return JsonResponse(response_data)


@csrf_exempt
def api_generate_ulpin_3d(request):
    """
    REST API to calculate 3D ULPIN on the fly (authorized officers only).
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'error': 'Authorized government officer credentials required.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST
        
    base_ulpin = data.get('base_2d_ulpin')
    floor = int(data.get('floor_number', 0))
    unit_id = data.get('unit_identifier', 'U01')
    z_min = float(data.get('z_min_meters', 0.0))
    z_max = float(data.get('z_max_meters', 3.0))
    unit_type = data.get('unit_type', '')
    
    if not base_ulpin:
        return JsonResponse({'error': 'base_2d_ulpin is required'}, status=400)
        
    ulpin_3d = generate_3d_ulpin(
        base_2d_ulpin=base_ulpin,
        floor_number=floor,
        unit_identifier=unit_id,
        z_min_meters=z_min,
        z_max_meters=z_max,
        unit_type=unit_type
    )
    
    parsed = parse_3d_ulpin(ulpin_3d)
    return JsonResponse({
        'ulpin_3d': ulpin_3d,
        'parsed': parsed,
    })


def api_verify_ulpin(request, ulpin_3d):
    """
    Validates and decodes any 3D ULPIN string.
    """
    parsed = parse_3d_ulpin(ulpin_3d)
    unit = VerticalPropertyUnit.objects.filter(ulpin_3d=ulpin_3d).first()
    
    return JsonResponse({
        'query': ulpin_3d,
        'is_registered_in_cadastre': bool(unit),
        'parsed_metadata': parsed,
        'unit_details': {
            'unit_number': unit.unit_number,
            'building': unit.building.name,
            'parcel_ulpin_2d': unit.building.parcel.ulpin_2d,
            'status': unit.status,
            'tax_status': unit.property_tax_status,
        } if unit else None
    })
