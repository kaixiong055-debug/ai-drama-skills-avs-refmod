"""Version provenance and transitive invalidation without inventing legacy history."""
import copy
from collections import Counter
from .common import GateError, index

STATUSES = {'VALID', 'STALE', 'MISSING', 'UNVERIFIED'}
VERSION_FIELDS = {'version', 'derived_from', 'source_version', 'source_versions', 'generated_from_version'}


def _version(value):
    return value is None or (isinstance(value, (int, str)) and not isinstance(value, bool) and str(value) != '')


def _version_map(value, parents):
    if value is None:
        return {}
    if isinstance(value, dict):
        return copy.deepcopy(value)
    if len(parents) == 1 and _version(value):
        return {parents[0]: value}
    raise GateError('ASSET_SOURCE_VERSION_AMBIGUOUS')


def _normalize(asset):
    a = copy.deepcopy(asset)
    parents = a.get('derived_from', [])
    if not isinstance(parents, list) or any(not isinstance(p, str) or not p for p in parents):
        raise GateError('ASSET_DERIVED_FROM_INVALID:' + str(a.get('asset_id')))
    if len(parents) != len(set(parents)):
        raise GateError('ASSET_DEPENDENCY_DUPLICATE:' + str(a.get('asset_id')))
    meaningful_metadata = a.get('version') is not None or bool(parents) or bool(a.get('source_versions')) or bool(a.get('source_version')) or bool(a.get('generated_from_version'))
    tracked = meaningful_metadata or (a.get('dependency_metadata_origin') != 'LEGACY_UNVERIFIED' and bool(VERSION_FIELDS & set(a)))
    a['dependency_metadata_origin'] = 'DECLARED' if tracked else 'LEGACY_UNVERIFIED'
    a.setdefault('version', None)
    if not _version(a['version']):
        raise GateError('ASSET_VERSION_INVALID:' + str(a.get('asset_id')))
    a['derived_from'] = parents
    a['source_versions'] = _version_map(a.get('source_versions', a.get('source_version')), parents)
    a['generated_from_version'] = _version_map(a.get('generated_from_version'), parents)
    if not a['source_versions'] and a['generated_from_version']:
        a['source_versions'] = copy.deepcopy(a['generated_from_version'])
    if not a['generated_from_version'] and a['source_versions']:
        a['generated_from_version'] = copy.deepcopy(a['source_versions'])
    for versions in [a['source_versions'], a['generated_from_version']]:
        if any(not isinstance(k, str) or not _version(v) for k, v in versions.items()):
            raise GateError('ASSET_SOURCE_VERSION_INVALID:' + str(a.get('asset_id')))
    a.setdefault('status', 'UNVERIFIED')
    if a['status'] not in STATUSES:
        raise GateError('ASSET_STATUS_INVALID:' + str(a.get('asset_id')))
    return a


def validate_asset_dependencies(assets, cast=(), scenes=(), bindings=None, allow_stale_asset=False):
    """Return a reproducible report; only explicit true permits STALE Picture bindings.

    UNVERIFIED legacy references remain usable and are never described as verified.
    Graph corruption, wrong family/wardrobe and MISSING bindings always block READY.
    """
    errors, warnings = [], []
    if not isinstance(allow_stale_asset, bool):
        errors.append('ALLOW_STALE_ASSET_MUST_BE_BOOLEAN')
        allow_stale_asset = False
    try:
        aa = index([_normalize(a) for a in assets], 'asset_id')
        cc = index(list(cast.values()) if isinstance(cast, dict) else cast, 'character_id')
        ss = index(list(scenes.values()) if isinstance(scenes, dict) else scenes, 'scene_id')
    except (GateError, TypeError, AttributeError) as exc:
        return {'schema_version': '5.1', 'status': 'FAIL', 'errors': [str(exc)], 'warnings': [], 'assets': [], 'counts': {}}
    ancestors, visits = {}, {}

    def lineage(aid, trail=()):
        if aid in ancestors:
            return ancestors[aid]
        if aid in trail:
            errors.append('ASSET_DEPENDENCY_CYCLE:' + '->'.join(trail + (aid,)))
            return set()
        result = set()
        for parent in aa[aid]['derived_from']:
            if parent not in aa:
                errors.append('ASSET_DEPENDENCY_MISSING:' + aid + ':' + parent)
                continue
            result.add(parent)
            result.update(lineage(parent, trail + (aid,)))
        ancestors[aid] = result
        return result

    for aid in aa:
        lineage(aid)

    def unique_role(role, key, value, wardrobe=None):
        matches = [a['asset_id'] for a in aa.values() if a.get('role') == role and a.get(key) == value
                   and (wardrobe is None or a.get('wardrobe') == wardrobe)]
        return matches[0] if len(matches) == 1 else None

    def require_ancestor(aid, parent, code):
        if not parent or parent not in aa or parent not in ancestors[aid]:
            errors.append(code + ':' + aid + ':' + str(parent))

    for aid, a in aa.items():
        parents = a['derived_from']
        tracked = a['dependency_metadata_origin'] != 'LEGACY_UNVERIFIED'
        for field in ['source_versions', 'generated_from_version']:
            if set(a[field]) - set(parents):
                errors.append('ASSET_VERSION_SOURCE_NOT_PARENT:' + aid + ':' + field)
        if a['source_versions'] != a['generated_from_version']:
            errors.append('ASSET_GENERATION_VERSION_CONFLICT:' + aid)
        cid = a.get('character_id')
        character = cc.get(cid, {})
        master = character.get('master_asset_id') or unique_role('MASTER', 'character_id', cid) if cid else None
        if cid and a['role'] in {'FACE4', 'BODY', 'WARDROBE', 'H3_RUNTIME'}:
            for ancestor in ancestors[aid]:
                if aa[ancestor].get('character_id') not in {None, cid}:
                    errors.append('CHARACTER_DEPENDENCY_FAMILY_CONFLICT:' + aid + ':' + ancestor)
            if tracked or master:
                require_ancestor(aid, master, 'CHARACTER_MASTER_DEPENDENCY_INVALID')
                if master in aa and aa[master].get('character_id') != cid:
                    errors.append('CHARACTER_MASTER_FAMILY_CONFLICT:' + aid)
            if a['role'] in {'WARDROBE', 'H3_RUNTIME'}:
                wardrobe = a.get('wardrobe')
                outfit = character.get('wardrobes', {}).get(wardrobe, {})
                if cid in cc and not outfit:
                    errors.append('ASSET_WARDROBE_UNKNOWN:' + aid)
                if a['role'] == 'H3_RUNTIME':
                    if outfit and outfit.get('runtime_asset_id') != aid:
                        errors.append('RUNTIME_WARDROBE_ASSET_CONFLICT:' + aid)
                    wa = outfit.get('wardrobe_asset_id') or outfit.get('asset_id') or unique_role('WARDROBE', 'character_id', cid, wardrobe)
                    if tracked or master or wa:
                        require_ancestor(aid, wa, 'RUNTIME_WARDROBE_DEPENDENCY_INVALID')
                    for ancestor in ancestors[aid]:
                        src = aa[ancestor]
                        if src.get('role') == 'WARDROBE' and (src.get('character_id') != cid or src.get('wardrobe') != wardrobe):
                            errors.append('RUNTIME_WRONG_WARDROBE_DEPENDENCY:' + aid + ':' + ancestor)
        if a['role'] == 'AREA':
            scene_master = ss.get(a.get('scene_id'), {}).get('master_asset_id') or a.get('master_asset_id')
            if tracked or (scene_master in aa and aa[scene_master]['version'] is not None):
                require_ancestor(aid, scene_master, 'SCENE_AREA_MASTER_DEPENDENCY_INVALID')
                for ancestor in ancestors[aid]:
                    if aa[ancestor].get('role') == 'MASTER' and aa[ancestor].get('scene_id') and ancestor != scene_master:
                        errors.append('SCENE_AREA_WRONG_MASTER:' + aid + ':' + ancestor)
        if a['role'] in {'PROP_VARIANT', 'PROP_STATE'} or (a['role'] == 'PROP' and a.get('variant')):
            prop_master = a.get('master_asset_id') or unique_role('PROP', 'prop_id', a.get('prop_id'))
            if tracked or prop_master:
                require_ancestor(aid, prop_master, 'PROP_VARIANT_MASTER_DEPENDENCY_INVALID')

    def status(aid, trail=()):
        if aid in visits:
            return visits[aid]
        a = aa[aid]
        reasons = []
        current = a['status']
        if aid in trail:
            return 'UNVERIFIED', ['DEPENDENCY_CYCLE']
        if current not in {'STALE', 'MISSING'} and a['version'] is None:
            current = 'UNVERIFIED'
            reasons.append('VERSION_UNVERIFIED')
        for parent in a['derived_from']:
            if parent not in aa:
                if current != 'MISSING': current = 'STALE'
                reasons.append('MISSING_SOURCE:' + parent)
                continue
            pstatus, _ = status(parent, trail + (aid,))
            recorded = a['source_versions'].get(parent)
            actual = aa[parent]['version']
            if recorded is not None and actual is not None and (type(recorded) is not type(actual) or recorded != actual):
                if current != 'MISSING': current = 'STALE'
                reasons.append('SOURCE_VERSION_CHANGED:' + parent)
            elif recorded is None or actual is None:
                if current == 'VALID': current = 'UNVERIFIED'
                reasons.append('SOURCE_VERSION_UNVERIFIED:' + parent)
            if pstatus in {'STALE', 'MISSING'}:
                if current != 'MISSING': current = 'STALE'
                reasons.append('UPSTREAM_' + pstatus + ':' + parent)
            elif pstatus == 'UNVERIFIED' and current == 'VALID':
                current = 'UNVERIFIED'
                reasons.append('UPSTREAM_UNVERIFIED:' + parent)
        visits[aid] = current, reasons
        return visits[aid]

    used = set()
    if bindings is not None:
        units = bindings.get('units', bindings)
        for uid, pictures in units.items():
            for slot, row in pictures.items():
                aid = row.get('asset_id')
                if aid not in aa:
                    errors.append('PICTURE_ASSET_UNKNOWN:' + str(uid) + ':' + str(slot))
                else:
                    used.add(aid)
    rows = []
    for aid, a in aa.items():
        computed, reasons = status(aid)
        if computed == 'UNVERIFIED': warnings.append('ASSET_PROVENANCE_UNVERIFIED:' + aid)
        if aid in used:
            if computed == 'MISSING': errors.append('MISSING_ASSET_BOUND:' + aid)
            if computed == 'STALE':
                if allow_stale_asset: warnings.append('STALE_ASSET_EXPLICITLY_ALLOWED:' + aid)
                else: errors.append('STALE_ASSET_BOUND:' + aid)
        rows.append({'asset_id': aid, 'version': a['version'], 'derived_from': a['derived_from'],
                     'source_versions': a['source_versions'], 'generated_from_version': a['generated_from_version'],
                     'status': computed, 'declared_status': a['status'], 'dependency_metadata_origin': a['dependency_metadata_origin'],
                     'bound': aid in used, 'reasons': reasons})
    return {'schema_version': '5.1', 'status': 'FAIL' if errors else 'PASS', 'errors': list(dict.fromkeys(errors)),
            'warnings': list(dict.fromkeys(warnings)), 'allow_stale_asset': allow_stale_asset,
            'counts': dict(Counter(row['status'] for row in rows)), 'assets': rows,
            'meaning': 'Dependency and version checks only; image identity/content review is separate.'}


def prepare_asset_dependencies(request):
    r = copy.deepcopy(request)
    r.setdefault('project', {}).setdefault('allow_stale_asset', False)
    r['assets'] = [_normalize(a) for a in r.get('assets', [])]
    report = validate_asset_dependencies(r['assets'], r.get('cast', []), r.get('scenes', []),
                                         allow_stale_asset=r['project']['allow_stale_asset'])
    if report['errors']:
        raise GateError('\n'.join(report['errors']))
    computed = {row['asset_id']: row['status'] for row in report['assets']}
    for a in r['assets']:
        a['status'] = computed[a['asset_id']]
    return r, report


def assert_asset_bindable(asset, allow_stale_asset=False):
    aid = asset.get('asset_id', '?')
    if asset.get('status') == 'MISSING':
        raise GateError('MISSING_ASSET_BOUND:' + aid)
    if asset.get('status') == 'STALE' and allow_stale_asset is not True:
        raise GateError('STALE_ASSET_BOUND:' + aid)
