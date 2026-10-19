"""V5.1 synthetic engineering fixtures, never evidence of real H3 video quality."""
from engine.common import bi
from engine.keyframes import REFERENCE_AUTHORITY
from examples.fixtures import fixture, materialize
import copy


def versioned_fixture(count=2, segments=3):
    """Declared synthetic version history for character and scene dependencies."""
    r = fixture(count, segments)
    r['schema_version'] = '5.1'
    r['source']['description'] = 'Synthetic engineering fixture with declared test-only asset versions; no real H3 inference or asset-content quality claim.'
    for c in r['cast']:
        cid = c['character_id']
        master, face, body, outfit = [cid + suffix for suffix in ['_MASTER', '_FACE4', '_BODY', '_WARDROBE_OFFICE']]
        c.update(master_asset_id=master, face4_asset_id=face, body_asset_id=body)
        c['wardrobes']['OFFICE']['wardrobe_asset_id'] = outfit
        for aid, role, parents in [(master, 'MASTER', []), (face, 'FACE4', [master]),
                                   (body, 'BODY', [face]), (outfit, 'WARDROBE', [body])]:
            asset = {'asset_id': aid, 'file': aid + '.png', 'role': role, 'character_id': cid,
                     'version': 3, 'derived_from': parents, 'source_versions': {p: 3 for p in parents},
                     'status': 'VALID', 'direct_bindable': False,
                     'description': bi('合成测试用人物分层资产', 'A synthetic character-layer reference for engineering tests')}
            if role == 'WARDROBE': asset['wardrobe'] = 'OFFICE'
            r['assets'].append(asset)
        runtime = next(a for a in r['assets'] if a['asset_id'] == c['wardrobes']['OFFICE']['runtime_asset_id'])
        runtime.update(version=3, derived_from=[master, outfit], source_versions={master: 3, outfit: 3}, status='VALID')
    for a in r['assets']:
        if a.get('role') == 'MASTER' and a.get('scene_id'):
            a.update(version=3, derived_from=[], source_versions={}, status='VALID')
    return r


def feature_fixture():
    """Scene AREA, prop states, two kinds of ready keyframe and persistent props."""
    r = versioned_fixture()
    r['project']['title'] = bi('V5.1资产依赖与关键帧合成示例', 'V5.1 synthetic asset-dependency and keyframe example')
    scene = r['scenes'][0]
    scene['initial_state']['door_states']['ENTRY_DOOR'] = 'half_open'
    scene['initial_state']['major_props']['LUGGAGE'] = {
        'holder': 'CHAR_A.right_hand', 'state': bi('右手持续握住关闭的行李箱拉杆', 'The right hand continuously holds the handle of the closed suitcase'),
        'valid_until_changed': True}
    scene['prop_asset_ids'] = {'LUGGAGE': 'PROP_LUGGAGE_CLOSED'}
    area = {'asset_id': 'SCN_LIVING_ENTRY', 'file': 'SCN_LIVING_ENTRY.png', 'role': 'AREA',
            'scene_id': scene['scene_id'], 'scene_family_id': 'LIVING', 'version': 1,
            'derived_from': [scene['master_asset_id']], 'source_versions': {scene['master_asset_id']: 3},
            'status': 'VALID', 'direct_bindable': True,
            'description': bi('继承客厅MASTER的入口门框与第二空间锚点', 'The entry doorframe and secondary spatial anchor inherited from the living-room MASTER')}
    r['assets'].append(area)
    r['assets'].append({'asset_id': 'PROP_LUGGAGE_MASTER', 'file': 'PROP_LUGGAGE_MASTER.png',
                        'role': 'PROP', 'prop_id': 'LUGGAGE', 'version': 2, 'derived_from': [],
                        'source_versions': {}, 'status': 'VALID', 'direct_bindable': False,
                        'description': bi('合成行李箱外观主资产', 'Synthetic suitcase appearance MASTER')})
    for variant in ['CLOSED', 'OPEN']:
        aid = 'PROP_LUGGAGE_' + variant
        r['assets'].append({'asset_id': aid, 'file': aid + '.png', 'role': 'PROP', 'prop_id': 'LUGGAGE',
                            'variant': variant, 'master_asset_id': 'PROP_LUGGAGE_MASTER', 'version': 1,
                            'derived_from': ['PROP_LUGGAGE_MASTER'], 'source_versions': {'PROP_LUGGAGE_MASTER': 2},
                            'status': 'VALID', 'direct_bindable': True,
                            'description': bi('行李箱' + ('关闭' if variant == 'CLOSED' else '打开') + '状态',
                                              'The suitcase in its ' + variant.lower() + ' state')})
    segment = r['segments'][0]
    segment.update(local_area_required=True, required_area_ids=['SCN_LIVING_ENTRY'])
    source = [c['wardrobes']['OFFICE']['runtime_asset_id'] for c in r['cast']]
    source += [scene['master_asset_id'], 'SCN_LIVING_ENTRY', 'PROP_LUGGAGE_CLOSED']
    versions = {a['asset_id']: a['version'] for a in r['assets']}
    segment['shot_keyframes'] = []
    for kind in ['SPATIAL_ANCHOR_KEYFRAME', 'SHOT_KEYFRAME']:
        aid = 'KF_SH001_' + kind
        r['assets'].append({'asset_id': aid, 'file': aid + '.png', 'role': 'STORYBOARD', 'version': 1,
                            'derived_from': source[:], 'source_versions': {p: versions[p] for p in source},
                            'status': 'VALID', 'direct_bindable': True,
                            'description': bi('合成关键帧，仅测试文件与权限绑定，不证明真实构图质量',
                                              'A synthetic keyframe testing file binding and authority, not real composition quality'),
                            'reference_authority': copy.deepcopy(REFERENCE_AUTHORITY)})
        segment['shot_keyframes'].append({'shot_id': 'SH001', 'keyframe_type': kind, 'keyframe_required': True,
                                          'source_assets': source[:], 'output': aid + '.png', 'asset_id': aid, 'status': 'AVAILABLE'})
    return r


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--family-only', action='store_true')
    args = parser.parse_args()
    assets = materialize(versioned_fixture() if args.family_only else feature_fixture(), args.output)
    print(str(assets.parent / 'project_input.json'))
