from pathlib import Path
import hashlib
from .common import GateError, index
from .asset_dependencies import assert_asset_bindable


def resolve_files(assets, asset_root):
    root = Path(asset_root).resolve()
    if not root.is_dir(): raise GateError('ASSET_ROOT_MISSING')
    files = [f for f in root.rglob('*') if f.is_file() and f.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.bmp'}]
    result = {}
    for aid, asset in index(assets, 'asset_id').items():
        # A planned, explicitly absent asset may remain in the registry. The
        # production binding gate rejects it if a unit actually needs it.
        if asset.get('status') == 'MISSING': continue
        output = asset['file']
        exact = [f for f in files if f.relative_to(root).as_posix() == output.replace('\\','/')]
        if not exact: exact = [f for f in files if f.name == Path(output).name]
        if not exact: exact = [f for f in files if f.stem.casefold() == aid.casefold()]
        if not exact: exact = [f for f in files if f.name in asset.get('aliases', [])]
        if len(exact) != 1: raise GateError(('ASSET_AMBIGUOUS:' if exact else 'ASSET_FILE_MISSING:') + aid)
        f = exact[0]
        try:
            from PIL import Image
            with Image.open(f) as im: im.verify()
        except ImportError as exc: raise GateError('DEPENDENCY_MISSING:Pillow') from exc
        except Exception as exc: raise GateError('ASSET_IMAGE_UNREADABLE:'+aid+':'+str(exc)) from exc
        result[aid] = {'file': f.relative_to(root).as_posix(), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
    return result


def bind_unit(state, scenes, cast, assets, files, unit, allow_stale_asset=False, is_lock=False, character_binding_mode="PICTURE"):
    if character_binding_mode not in {"PICTURE", "AVS_REFMOD"}: raise GateError("CHARACTER_BINDING_MODE_INVALID:" + str(character_binding_mode))
    selected = []
    def add(aid):
        if aid not in assets: raise GateError('ASSET_UNKNOWN:' + str(aid))
        assert_asset_bindable(assets[aid], allow_stale_asset)
        if aid not in files: raise GateError('ASSET_FILE_MISSING:' + str(aid))
        if aid not in selected: selected.append(aid)
    for cid in state['left_to_right_order']:
        wardrobe = state['characters'][cid]['wardrobe']
        outfits = cast[cid]['wardrobes']
        if wardrobe not in outfits: raise GateError('WARDROBE_UNKNOWN:' + cid + ':' + wardrobe)
        aid = outfits[wardrobe]['runtime_asset_id']
        asset = assets.get(aid, {})
        if asset.get('role') != 'H3_RUNTIME' or asset.get('character_id') != cid or asset.get('wardrobe') != wardrobe:
            raise GateError('WARDROBE_RUNTIME_BINDING_CONFLICT:' + cid)
        # AVS_REFMOD: character identity/wardrobe are applied by AI-Video-Studio
        # Identity RefMod + Clothing RefMod. The character runtime image remains
        # validated as a canonical asset, but it must NOT occupy a Picture slot.
        if character_binding_mode == "AVS_REFMOD":
            assert_asset_bindable(asset, allow_stale_asset)
            if aid not in files: raise GateError('ASSET_FILE_MISSING:' + str(aid))
        else:
            add(aid)
    scene = scenes[state['scene_id']]
    add(scene['master_asset_id'])
    required_areas = unit.get('required_area_ids', [])
    if unit.get('local_area_required') and not required_areas: raise GateError('LOCAL_AREA_ASSET_MISSING')
    for aid in required_areas:
        if assets.get(aid, {}).get('role') != 'AREA' or assets[aid].get('scene_id') != state['scene_id']:
            raise GateError('AREA_ROLE_CONFLICT:' + aid)
        add(aid)
    for pid in state['major_props']:
        aid = scene.get('prop_asset_ids', {}).get(pid)
        if not aid: raise GateError('PERSISTENT_PROP_ASSET_MISSING:' + pid)
        add(aid)
    for aid in unit.get('required_asset_ids', []):
        # Shot images control their own formal camera composition. Only an
        # explicitly spatial anchor image may condition the separate LOCK.
        if is_lock and assets.get(aid, {}).get('keyframe_type') not in {None, 'SPATIAL_ANCHOR_KEYFRAME'}:
            continue
        add(aid)
    if len(selected) > 9: raise GateError('PICTURE_LIMIT_EXCEEDED')
    for aid in selected:
        if assets[aid].get('direct_bindable') is not True: raise GateError('ASSET_NOT_DIRECT_BINDABLE:' + aid)
    result = {f'P{n}': {'asset_id': aid, **files[aid]} for n, aid in enumerate(selected, 1)}
    for row in result.values():
        asset = assets[row['asset_id']]
        if asset.get('keyframe_type'):
            row['keyframe_type'] = asset['keyframe_type']
            row['shot_id'] = asset['shot_id']
            row['reference_authority'] = asset['reference_authority']
    return result
