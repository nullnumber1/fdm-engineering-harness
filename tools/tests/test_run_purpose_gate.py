"""Synthetic purpose/coupon regressions; never real manufacturing evidence."""
from copy import deepcopy
import json
import subprocess
import sys
import unittest

import test_engineering_harness as fixture

eh = fixture.eh


class RunPurposeGateTests(unittest.TestCase):
    def setUp(self):
        fixture.EngineeringHarnessTests.setUp(self)

    def complete(self):
        fixture.EngineeringHarnessTests.complete(self)

    def restamp(self):
        """Simulate direct JSON stamping to test the gate independently of mark."""
        catalog = {c['id']: c for c in self.h.catalog}
        for row in self.run['checks']:
            row['basis_sha256'] = self.h.basis(self.run, catalog[row['id']]['stage'])

    def ref(self, key):
        return {'artifact': key, 'sha256': self.run['artifacts'][key]['sha256'],
                'locator': 'TEST ONLY bounded coupon scope and exact synthetic geometry'}

    def coupon_scope(self):
        return {'kind': 'surface-coupon', 'full_product_part': False, 'part_ids': ['bracket'],
                'hypothesis': 'TEST ONLY separately bounded physical surface experiment',
                'limits': 'TEST ONLY isolated coupon, no complete product or assembly fit claim',
                'acceptance': 'TEST ONLY concrete coupon finish and dimensional observations',
                'evidence': self.ref('proof'), 'geometry_evidence': self.ref('mesh')}

    def direct_surface(self, strategy='direct-print'):
        quality = self.run['manufacturing_quality']
        surface = quality['parts']['bracket']['surfaces'][0]
        surface.update({'formation': 'build-plate', 'strategy': strategy})
        surface.pop('physical_validation', None)
        if strategy == 'assessed-noncritical':
            surface.update({'class': 'noncritical',
                            'noncritical_reason': 'TEST ONLY independently classified coupon surface'})
        quality['parts']['bracket']['edges'][0]['forming_base'] = 'build-plate'
        quality['plates']['plate01'].update({'has_supports': False, 'support_groups': []})
        for row in self.run['checks']:
            if row['id'] in ('supported-surface-quality', 'native-support-stability'):
                row['status'] = 'N/A'

    def complete_direct_coupon(self):
        self.run['component_control']['decision'] = 'unchanged'
        for check, target in self.h.required(self.run, 'release'):
            independent = check['id'] == 'independent-review'
            status = 'N/A' if check['id'] in ('supported-surface-quality', 'native-support-stability') else 'PASS'
            self.h.mark(self.run, check['id'], target, status,
                        'TEST ONLY synthetic coupon observations, not physical manufacturing evidence',
                        'review-agent' if independent else self.run['owner'],
                        'independent-review' if independent else 'inspection',
                        list(self.run['artifacts']), 'TEST ONLY complete coupon inventory and actual file links')

    def test_complete_production_review_passes_every_stage(self):
        self.assertEqual(self.run['purpose'], 'production')
        self.complete()
        for stage in eh.STAGES:
            result = self.h.validate(self.run, stage)
            self.assertTrue(result['passed'], result['errors'])

    def test_new_api_rejects_prototype_and_unknown_purposes(self):
        for purpose in ('prototype', 'unknown', None):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(eh.HarnessError, 'production or calibration'):
                self.h.create('invalid-purpose', ['part'], ['plate'], 'other-petg', purpose)

    def test_cli_rejects_prototype_without_creating_a_record(self):
        name = 'harness/runs/forbidden-prototype.json'
        result = subprocess.run([sys.executable, str(self.root / 'tools/engineering_harness.py'),
                                 'new', '--run', name, '--part', 'coupon', '--plate', 'plate',
                                 '--material', 'other-petg', '--purpose', 'prototype'],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid choice', result.stderr)
        self.assertFalse((self.root / name).exists())

    def test_cli_creates_only_unchecked_production_or_calibration(self):
        for purpose in ('production', 'calibration'):
            with self.subTest(purpose=purpose):
                name = f'harness/runs/new-{purpose}.json'
                result = subprocess.run([sys.executable, str(self.root / 'tools/engineering_harness.py'),
                                         'new', '--run', name, '--part', 'coupon', '--plate', 'plate',
                                         '--material', 'other-petg', '--purpose', purpose],
                                        cwd=self.root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                created = json.loads((self.root / name).read_text())
                self.assertEqual(created['purpose'], purpose)
                self.assertEqual(created['artifacts'], {})
                self.assertIsNone(created['manufacturing_quality']['calibration_scope'])
                self.assertTrue(all(row['status'] == 'UNKNOWN' for row in created['checks']))

    def test_legacy_prototype_is_readable_but_renaming_and_restamping_cannot_pass(self):
        self.complete()
        self.run['purpose'] = 'prototype'
        self.run['run_id'] = 'renamed-final-production-part'
        for row in self.run['checks']:
            row['reason'] = 'TEST ONLY final production item, checked and renamed for current release'
        self.restamp()
        path = self.root / 'harness/runs/renamed-production.json'
        eh.atomic_json(path, self.run)
        before = path.read_bytes()
        loaded = self.h.load(path)
        self.assertEqual(loaded['purpose'], 'prototype')
        self.assertTrue(all(row['status'] == 'PASS' for row in loaded['checks']))
        for stage in eh.STAGES:
            result = self.h.validate(loaded, stage)
            self.assertFalse(result['passed'])
            self.assertTrue(any('prototype purpose is historical-only' in e for e in result['errors']))
        self.assertEqual(self.h.checklist(loaded).count('— BLOCKED'), len(eh.STAGES))
        self.assertEqual(path.read_bytes(), before)

    def test_legacy_prototype_cannot_mark_pass_or_na_but_can_record_diagnosis(self):
        self.run['purpose'] = 'prototype'
        check, target = self.h.required(self.run, 'intake')[0]
        for status in ('PASS', 'N/A'):
            with self.subTest(status=status), self.assertRaisesRegex(eh.HarnessError, 'historical-only'):
                self.h.mark(self.run, check['id'], target, status, 'TEST ONLY actual legacy review observation',
                            self.run['owner'], 'inspection', ['proof'], 'TEST ONLY legacy diagnosis')
        for status in ('FAIL', 'UNKNOWN'):
            self.h.mark(self.run, check['id'], target, status, 'TEST ONLY unresolved legacy record diagnosis',
                        self.run['owner'], 'inspection', ['proof'], 'TEST ONLY legacy diagnosis')
            self.assertFalse(self.h.validate(self.run, 'intake')['passed'])

    def test_purpose_rename_to_production_does_not_inherit_legacy_passes(self):
        self.complete()
        self.run['purpose'] = 'prototype'
        self.restamp()
        self.run['purpose'] = 'production'
        for stage in eh.STAGES:
            result = self.h.validate(self.run, stage)
            self.assertFalse(result['passed'])
            self.assertTrue(any('stale review basis' in e for e in result['errors']))

    def test_calibration_intake_does_not_require_finished_coupon_geometry(self):
        fresh = self.h.create('calibration-intake', ['bracket'], ['plate01'],
                              'bambu-petg-basic', 'calibration')
        self.run['purpose'] = 'calibration'
        self.run['manufacturing_quality'] = fresh['manufacturing_quality']
        self.run['artifacts'].pop('mesh')
        self.run['parts']['bracket']['artifacts'] = []
        self.run['component_control']['decision'] = 'unchanged'
        for check, target in self.h.required(self.run, 'intake'):
            self.h.mark(self.run, check['id'], target, 'PASS',
                        'TEST ONLY bounded investigation intake, geometry not yet produced',
                        self.run['owner'], 'inspection', list(self.run['artifacts']), 'TEST ONLY intake evidence')
        intake = self.h.validate(self.run, 'intake')
        self.assertTrue(intake['passed'], intake['errors'])
        self.assertIsNone(self.run['manufacturing_quality']['calibration_scope'])
        self.assertFalse(self.h.validate(self.run, 'design')['passed'])

    def test_calibration_missing_or_full_product_scope_blocks_all_later_gates(self):
        self.complete()
        self.run['purpose'] = 'calibration'
        baseline = deepcopy(self.run)
        valid = self.coupon_scope()
        for scope in (None, {}, {**valid, 'full_product_part': True},
                      {**valid, 'part_ids': []}, {**valid, 'part_ids': ['bracket', 'extra']}):
            with self.subTest(scope=scope):
                self.run = deepcopy(baseline)
                self.run['manufacturing_quality']['calibration_scope'] = scope
                self.restamp()
                self.assertTrue(self.h.validate(self.run, 'intake')['passed'])
                for stage in ('design', 'slice', 'release'):
                    result = self.h.validate(self.run, stage)
                    self.assertFalse(result['passed'])
                    self.assertTrue(any('bounded surface-coupon scope' in e for e in result['errors']))

    def test_direct_print_or_noncritical_names_do_not_bypass_calibration_scope(self):
        self.complete()
        baseline = deepcopy(self.run)
        for strategy in ('direct-print', 'assessed-noncritical'):
            for full_product in (None, True):
                with self.subTest(strategy=strategy, full_product=full_product):
                    self.run = deepcopy(baseline)
                    self.run['purpose'] = 'calibration'
                    self.direct_surface(strategy)
                    self.run['manufacturing_quality']['calibration_scope'] = (
                        None if full_product is None else {**self.coupon_scope(), 'full_product_part': full_product})
                    self.restamp()
                    with self.assertRaisesRegex(eh.HarnessError, 'bounded surface-coupon scope'):
                        self.h.mark(self.run, 'surface-quality-strategy', 'part:bracket', 'PASS',
                                    'TEST ONLY direct surface and no supported faces', self.run['owner'],
                                    'inspection', list(self.run['artifacts']), 'TEST ONLY direct surface inventory')
                    for stage in ('design', 'slice', 'release'):
                        self.assertFalse(self.h.validate(self.run, stage)['passed'])

    def test_valid_bounded_coupon_can_use_direct_print_without_a_surface_waiver(self):
        self.run['purpose'] = 'calibration'
        self.direct_surface()
        self.run['manufacturing_quality']['calibration_scope'] = self.coupon_scope()
        self.complete_direct_coupon()
        for stage in eh.STAGES:
            result = self.h.validate(self.run, stage)
            self.assertTrue(result['passed'], result['errors'])

    def test_calibration_scope_requires_current_role_correct_bound_evidence(self):
        self.run['purpose'] = 'calibration'
        self.direct_surface()
        self.run['manufacturing_quality']['calibration_scope'] = self.coupon_scope()
        self.complete_direct_coupon()
        baseline = deepcopy(self.run)
        for field, bad in (('evidence', None), ('geometry_evidence', self.ref('proof')),
                           ('geometry_evidence', {**self.ref('mesh'), 'sha256': '0' * 64}),
                           ('evidence', {**self.ref('proof'), 'locator': ''})):
            with self.subTest(field=field, bad=bad):
                self.run = deepcopy(baseline)
                self.run['manufacturing_quality']['calibration_scope'][field] = bad
                self.restamp()
                for stage in ('design', 'slice', 'release'):
                    self.assertFalse(self.h.validate(self.run, stage)['passed'])


if __name__ == '__main__':
    unittest.main()
