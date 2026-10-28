import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('evaluation', Path(__file__).parents[1] / 'scripts/pilot_evaluation.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def case(self, **changes):
        return dict(dict(tenant_id='synthetic-tenant', case_id='fixture-1', authorized=True,
                         human_reviewed=True, dataset='synthetic', helpful=True, abstained=False), **changes)

    def test_no_data_produces_no_performance_claim(self):
        self.assertIsNone(evaluation.summarize([])['helpful_fraction'])
        self.assertIsNone(evaluation.summarize([])['median_observed_minutes_difference'])

    def test_missing_timing_is_not_zero(self):
        self.assertEqual(evaluation.summarize([self.case()])['paired_timing_cases'], 0)

    def test_unreviewed_or_unauthorized_rejected(self):
        for change in ({'authorized': False}, {'human_reviewed': False}):
            with self.assertRaises(ValueError):
                evaluation.summarize([self.case(**change)])

    def test_duplicate_and_mixed_datasets_rejected(self):
        for cases in ([self.case(), self.case()],
                      [self.case(), self.case(case_id='2', dataset='pilot')],
                      [self.case(), self.case(case_id='2', tenant_id='other')]):
            with self.assertRaises(ValueError):
                evaluation.summarize(cases)

    def test_incomplete_invalid_or_unlabelled_timing_rejected(self):
        for changes in ({'baseline_minutes': 5},
                        {'baseline_minutes': float('nan'), 'assisted_minutes': 3},
                        {'baseline_minutes': 5, 'assisted_minutes': 3}):
            with self.assertRaises(ValueError):
                evaluation.summarize([self.case(**changes)])

    def test_regressions_are_retained(self):
        result = evaluation.summarize([self.case(baseline_minutes=5, assisted_minutes=7, timing_protocol_id='synthetic-protocol')])
        self.assertEqual(result['median_observed_minutes_difference'], -2)


if __name__ == '__main__':
    unittest.main()
