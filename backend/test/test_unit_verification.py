import copy
import unittest

from src.rag import unit_verification
from src.rag.unit_verification import (
    STAGES, block_coverage, characters, classify, compare_units, evidence_presence, relevant,
    source_accounting, squash, stage_summary,
)


def extraction():
    return {
        'sections': [{
            'id': 'S1', 'title': 'Status messages', 'start_pdf_page': 1,
            'blocks': [
                {'id': 'B1', 'type': 'paragraph', 'pdf_page': 1, 'text': 'Check the ﬁle.'},
                {'id': 'B2', 'type': 'table', 'pdf_page': 1, 'raw_header': ['Message', 'Cause'],
                 'rows': [{'id': 'R1', 'cells': ['"Offline"', 'Printer\nis offline.']},
                          {'id': 'R2', 'cells': ['"Job Suspended..."', 'Paused.']}]},
                {'id': 'B3', 'type': 'table', 'pdf_page': 2, 'raw_header': ['Icon'],
                 'rows': [{'id': 'R3', 'cells': ['']}]},
            ]}],
        'excluded_layout_text': [{'pdf_page': 1, 'text': '9'}],
    }


def units():
    common = {'section_id': 'S1', 'section_title': 'Status messages'}
    return [
        {**common, 'unit_id': 'U1', 'kind': 'section_text', 'body': 'Check the ﬁle.',
         'source_blocks': [{'id': 'B1'}], 'row': None},
        {**common, 'unit_id': 'U2', 'kind': 'table_row', 'body': 'Message: "Offline"\nCause: Printer is offline.',
         'source_blocks': [{'id': 'B2'}], 'row': {'table_id': 'B2', 'id': 'R1', 'cells': ['"Offline"', 'Printer\nis offline.']}},
        {**common, 'unit_id': 'U3', 'kind': 'table_row', 'body': 'Message: "Job Suspended..."\nCause: Paused.',
         'source_blocks': [{'id': 'B2'}], 'row': {'table_id': 'B2', 'id': 'R2', 'cells': ['"Job Suspended..."', 'Paused.']}},
    ]


def two_paragraph_extraction():
    data = extraction()
    data['sections'][0]['blocks'].insert(1, {'id': 'B4', 'type': 'paragraph', 'pdf_page': 1, 'text': 'Then retry.'})
    data['sections'].append({'id': 'S2', 'title': 'Other', 'start_pdf_page': 2,
                             'blocks': [{'id': 'B5', 'type': 'paragraph', 'pdf_page': 2, 'text': 'Unrelated.'}]})
    return data


def two_paragraph_units():
    result = units()
    result[0] = {**result[0], 'body': 'Check the ﬁle.\n\nThen retry.', 'source_blocks': [{'id': 'B1'}, {'id': 'B4'}]}
    result.append({'section_id': 'S2', 'section_title': 'Other', 'unit_id': 'U5', 'kind': 'section_text',
                   'body': 'Unrelated.', 'source_blocks': [{'id': 'B5'}], 'row': None})
    return result


EXCLUDED = [{'block_id': 'B3', 'pdf_page': 2, 'reason': ['graphics']}]
PAGE_TEXT = {1: 'Status messages Check the file. Message Cause "Offline" Printer is offline. '
                '"Job Suspended..." Paused. 9', 2: 'Icon'}


def legacy_relevance(unit, case):
    # Inline rule used by evaluate_ricoh_local before step 8; kept to prove the refactor is neutral.
    row_text = ' '.join(' '.join(cell.split()) for cell in unit['row']['cells']) if unit['row'] else ''
    return (unit['section_title'] == case['expected_section']
            and (not case.get('expected_row_contains') or case['expected_row_contains'] in row_text))


class NormalizationTests(unittest.TestCase):
    def test_characters_fold_ligatures_and_compatibility_forms(self):
        self.assertEqual(characters('ﬁ１'), characters('fi1'))

    def test_characters_ignore_every_kind_of_whitespace(self):
        self.assertEqual(characters('a\tb\nc d e'), characters('abcde'))

    def test_characters_preserve_case_digits_and_punctuation(self):
        self.assertNotEqual(characters('Offline'), characters('offline'))
        self.assertNotEqual(characters('v1.2'), characters('v12'))

    def test_characters_and_squash_accept_missing_text(self):
        self.assertEqual(characters(None), {})
        self.assertEqual(squash(None), '')

    def test_squash_collapses_internal_and_edge_whitespace(self):
        self.assertEqual(squash('  Printer\n is\t offline. '), 'Printer is offline.')


class SourceAccountingTests(unittest.TestCase):
    def test_all_characters_accounted_with_ligatures_and_layout_text(self):
        result = source_accounting(extraction(), PAGE_TEXT)
        self.assertTrue(result['complete'])
        self.assertEqual((result['missing_characters'], result['extra_characters']), (0, 0))
        self.assertEqual(result['pages_checked'], 2)
        self.assertEqual(result['source_characters'], sum(characters(t).total() for t in PAGE_TEXT.values()))

    def test_dropped_text_is_reported_per_page(self):
        data = extraction()
        data['excluded_layout_text'] = []
        result = source_accounting(data, PAGE_TEXT)
        self.assertFalse(result['complete'])
        self.assertEqual(result['pages_with_differences'], [{'pdf_page': 1, 'missing': {'9': 1}, 'extra': {}}])

    def test_invented_text_is_reported_as_extra(self):
        data = extraction()
        data['sections'][0]['blocks'][0]['text'] += ' Reboot.'
        result = source_accounting(data, PAGE_TEXT)
        self.assertEqual(result['extra_characters'], len('Reboot.'))
        self.assertFalse(result['complete'])

    def test_text_moved_to_another_page_is_missing_and_extra(self):
        data = extraction()
        data['excluded_layout_text'][0]['pdf_page'] = 2
        result = source_accounting(data, PAGE_TEXT)
        self.assertEqual((result['missing_characters'], result['extra_characters']), (1, 1))
        self.assertEqual([p['pdf_page'] for p in result['pages_with_differences']], [1, 2])

    def test_section_titles_count_as_source_text(self):
        data = extraction()
        data['sections'][0]['title'] = 'Status'
        self.assertEqual(source_accounting(data, PAGE_TEXT)['missing_characters'], len('messages'))

    def test_text_attributed_outside_checked_pages_is_not_complete(self):
        result = source_accounting(extraction(), {1: PAGE_TEXT[1]})
        self.assertEqual(result['accounted_pages_outside_check'], [2])
        self.assertFalse(result['complete'])

    def test_checked_page_without_any_extracted_text_is_fully_missing(self):
        result = source_accounting(extraction(), {**PAGE_TEXT, 3: 'Lost page'})
        self.assertEqual(result['missing_characters'], len('Lostpage'))

    def test_string_page_numbers_none_headers_and_none_cells_are_handled(self):
        data = extraction()
        table = data['sections'][0]['blocks'][1]
        table['pdf_page'] = '1'
        table['raw_header'] = ['Message', None, 'Cause']
        table['rows'][0]['cells'].append(None)
        self.assertTrue(source_accounting(data, PAGE_TEXT)['complete'])

    def test_unknown_block_type_fails_instead_of_being_skipped(self):
        data = extraction()
        data['sections'][0]['blocks'].append({'id': 'B9', 'type': 'figure', 'pdf_page': 1})
        with self.assertRaisesRegex(ValueError, 'contabilidad'):
            source_accounting(data, PAGE_TEXT)

    def test_empty_document_and_no_pages_is_trivially_complete(self):
        result = source_accounting({'sections': [], 'excluded_layout_text': []}, {})
        self.assertTrue(result['complete'])
        self.assertEqual(result['source_characters'], 0)


class BlockCoverageTests(unittest.TestCase):
    def test_every_block_is_in_one_unit_or_explicitly_excluded(self):
        result = block_coverage(extraction(), units(), EXCLUDED)
        self.assertTrue(result['complete'])
        self.assertEqual(result['status'], {'paragraphs_in_units': 1, 'table_rows_in_units': 2,
                                            'excluded_table_rows': 1})

    def test_multi_paragraph_units_across_sections(self):
        result = block_coverage(two_paragraph_extraction(), two_paragraph_units(), EXCLUDED)
        self.assertTrue(result['complete'])
        self.assertEqual(result['status']['paragraphs_in_units'], 3)

    def test_excluded_paragraph_is_counted_not_reported(self):
        result = block_coverage(extraction(), units()[1:], [*EXCLUDED, {'block_id': 'B1', 'reason': ['glyphs']}])
        self.assertTrue(result['complete'])
        self.assertEqual(result['status']['excluded_paragraphs'], 1)

    def test_missing_row_unit_is_a_problem_not_an_exclusion(self):
        result = block_coverage(extraction(), units()[:2], EXCLUDED)
        self.assertEqual(result['problems'], [{'block_id': 'B2', 'row_id': 'R2', 'issue': 'row_not_in_single_unit'}])

    def test_missing_paragraph_unit_is_reported(self):
        result = block_coverage(extraction(), units()[1:], EXCLUDED)
        self.assertEqual(result['problems'], [{'block_id': 'B1', 'issue': 'paragraph_not_in_single_unit'}])

    def test_truncated_paragraph_body_is_detected(self):
        changed = units()
        changed[0]['body'] = 'Check the'
        self.assertFalse(block_coverage(extraction(), changed, EXCLUDED)['complete'])

    def test_body_with_extra_text_is_not_accepted_as_substring(self):
        changed = units()
        changed[0]['body'] = 'Check the ﬁle. Then call the vendor.'
        self.assertFalse(block_coverage(extraction(), changed, EXCLUDED)['complete'])

    def test_paragraph_order_inside_unit_is_enforced(self):
        changed = two_paragraph_units()
        changed[0]['body'] = 'Then retry.\n\nCheck the ﬁle.'
        self.assertFalse(block_coverage(two_paragraph_extraction(), changed, EXCLUDED)['complete'])

    def test_paragraph_attributed_to_another_section_is_detected(self):
        changed = units()
        changed[0]['section_id'] = 'S9'
        self.assertFalse(block_coverage(extraction(), changed, EXCLUDED)['complete'])

    def test_paragraph_in_two_units_is_detected(self):
        self.assertFalse(block_coverage(extraction(), units() + [{**units()[0], 'unit_id': 'U9'}], EXCLUDED)['complete'])

    def test_duplicated_row_unit_is_detected(self):
        self.assertFalse(block_coverage(extraction(), units() + [units()[1]], EXCLUDED)['complete'])

    def test_row_unit_with_altered_cells_is_detected_even_if_body_matches(self):
        changed = units()
        changed[1]['row'] = {**changed[1]['row'], 'cells': ['"Offline"', 'Printer is offline.']}
        self.assertFalse(block_coverage(extraction(), changed, EXCLUDED)['complete'])

    def test_row_body_missing_a_cell_is_detected(self):
        changed = units()
        changed[2]['body'] = 'Message: "Job Suspended..."'
        self.assertFalse(block_coverage(extraction(), changed, EXCLUDED)['complete'])

    def test_row_body_accepts_whitespace_normalized_cells(self):
        self.assertIn('Printer is offline.', units()[1]['body'])
        self.assertTrue(block_coverage(extraction(), units(), EXCLUDED)['complete'])

    def test_unexcluded_graphic_table_without_units_is_detected(self):
        result = block_coverage(extraction(), units(), [])
        self.assertEqual(result['problems'], [{'block_id': 'B3', 'row_id': 'R3', 'issue': 'row_not_in_single_unit'}])


class UnitComparisonTests(unittest.TestCase):
    def test_identical_units(self):
        result = compare_units(units(), copy.deepcopy(units()))
        self.assertTrue(result['identical'])
        self.assertEqual((result['added'], result['removed'], result['changed'], result['duplicated']), ([], [], [], []))

    def test_added_removed_and_changed_units_are_listed(self):
        after = copy.deepcopy(units()[1:])
        after[0]['body'] += ' x'
        after.append({**units()[0], 'unit_id': 'U9'})
        result = compare_units(units(), after)
        self.assertEqual((result['removed'], result['added'], result['changed']), (['U1'], ['U9'], ['U2']))
        self.assertFalse(result['identical'])

    def test_duplicated_ids_are_reported_and_never_identical(self):
        for before, after in ((units() + [units()[0]], units()), (units(), units() + [units()[0]])):
            with self.subTest(before=len(before), after=len(after)):
                result = compare_units(before, after)
                self.assertEqual(result['duplicated'], ['U1'])
                self.assertFalse(result['identical'])
        self.assertEqual(compare_units(units() + [units()[0]], units())['before'], 4)

    def test_reordering_changes_index_order_and_is_not_identical(self):
        result = compare_units(units(), list(reversed(units())))
        self.assertFalse(result['identical'])
        self.assertEqual((result['added'], result['removed'], result['changed']), ([], [], []))

    def test_empty_sets(self):
        self.assertTrue(compare_units([], [])['identical'])
        self.assertEqual(compare_units([], units())['added'], ['U1', 'U2', 'U3'])


class RelevanceTests(unittest.TestCase):
    CASE = {'id': 'RIC-09', 'expected_section': 'Status messages', 'expected_row_contains': '"Offline"'}

    def test_relevance_uses_whitespace_normalized_row_cells(self):
        self.assertTrue(relevant(units()[1], {**self.CASE, 'expected_row_contains': 'Printer is offline.'}))
        self.assertTrue(relevant(units()[1], self.CASE))
        self.assertFalse(relevant(units()[2], self.CASE))

    def test_row_case_never_matches_a_text_unit(self):
        self.assertFalse(relevant(units()[0], self.CASE))

    def test_section_case_matches_text_and_row_units_of_that_section_only(self):
        case = {'expected_section': 'Status messages'}
        self.assertTrue(all(relevant(u, case) for u in units()))
        self.assertFalse(relevant(two_paragraph_units()[-1], case))

    def test_section_title_must_match_exactly(self):
        self.assertFalse(relevant(units()[1], {**self.CASE, 'expected_section': 'status messages'}))

    def test_empty_row_expectation_behaves_as_section_case(self):
        self.assertTrue(relevant(units()[0], {**self.CASE, 'expected_row_contains': ''}))

    def test_matches_previous_inline_rule_of_ricoh_evaluator(self):
        cases = [self.CASE, {'expected_section': 'Status messages'}, {'expected_section': 'Other'},
                 {**self.CASE, 'expected_row_contains': 'Printer is'},
                 {**self.CASE, 'expected_row_contains': '"Offline" Printer'},
                 {**self.CASE, 'expected_row_contains': 'printer'}, {**self.CASE, 'expected_row_contains': ''}]
        for unit in two_paragraph_units():
            for case in cases:
                with self.subTest(unit=unit['unit_id'], case=case):
                    self.assertEqual(relevant(unit, case), legacy_relevance(unit, case))


class EvidencePresenceTests(unittest.TestCase):
    CASE = RelevanceTests.CASE

    def test_row_case_locates_table_block_unit_and_fragment(self):
        present = evidence_presence(self.CASE, extraction(), units(), [{'unit_id': 'U2'}], EXCLUDED)
        self.assertEqual(present, {'extraction_sections': ['S1'], 'extraction_blocks': ['B2'], 'excluded_blocks': [],
                                   'relevant_units': ['U2'], 'relevant_units_with_fragments': ['U2']})

    def test_section_case_accepts_table_only_section(self):
        data = extraction()
        data['sections'][0]['blocks'] = data['sections'][0]['blocks'][1:2]
        present = evidence_presence({'expected_section': 'Status messages'}, data, units()[1:], [{'unit_id': 'U2'}], [])
        self.assertEqual(present['extraction_blocks'], ['B2'])
        self.assertEqual(classify(present, 1), 'retrieved')

    def test_excluded_evidence_is_listed_and_classified_as_unit_loss(self):
        data = extraction()
        case = {**self.CASE, 'expected_row_contains': '"Offline"'}
        present = evidence_presence(case, data, [], [], [{'block_id': 'B2', 'reason': ['review']}])
        self.assertEqual(present['excluded_blocks'], ['B2'])
        self.assertEqual(classify(present, None), 'unit_loss')

    def test_repeated_section_titles_are_all_searched(self):
        data = two_paragraph_extraction()
        data['sections'][1]['title'] = 'Status messages'
        present = evidence_presence({'expected_section': 'Status messages'}, data, [], [], [])
        self.assertEqual(present['extraction_sections'], ['S1', 'S2'])
        self.assertIn('B5', present['extraction_blocks'])

    def test_absent_section_or_row(self):
        for case in ({'expected_section': 'Missing'}, {**self.CASE, 'expected_row_contains': '"Toner Low"'}):
            with self.subTest(case=case):
                present = evidence_presence(case, extraction(), units(), [{'unit_id': 'U2'}], EXCLUDED)
                self.assertEqual(present['extraction_blocks'], [])
                self.assertEqual(classify(present, None), 'extraction_loss')

    def test_row_expectation_split_across_rows_does_not_match(self):
        case = {**self.CASE, 'expected_row_contains': 'offline. "Job'}
        self.assertEqual(evidence_presence(case, extraction(), units(), [], EXCLUDED)['extraction_blocks'], [])


class StageClassificationTests(unittest.TestCase):
    CASE = RelevanceTests.CASE

    def test_each_failure_stage_is_separated(self):
        fragments = [{'unit_id': 'U2'}]
        present = evidence_presence(self.CASE, extraction(), units(), fragments, EXCLUDED)
        self.assertEqual(classify(present, None), 'search_failure')
        for rank in (1, 2, 3):
            self.assertEqual(classify(present, rank), 'retrieved')
        self.assertEqual(classify(evidence_presence(self.CASE, extraction(), units(), [], EXCLUDED), 1), 'fragment_loss')
        self.assertEqual(classify(evidence_presence(self.CASE, extraction(), [], [], EXCLUDED), None), 'unit_loss')

    def test_earliest_loss_wins_even_if_search_reports_a_rank(self):
        present = {'extraction_blocks': [], 'relevant_units': ['U2'], 'relevant_units_with_fragments': ['U2']}
        self.assertEqual(classify(present, 1), 'extraction_loss')

    def test_fragments_of_unrelated_units_do_not_count(self):
        present = evidence_presence(self.CASE, extraction(), units(), [{'unit_id': 'U3'}], EXCLUDED)
        self.assertEqual(classify(present, None), 'fragment_loss')

    def test_all_classifications_belong_to_declared_stages(self):
        self.assertEqual(STAGES, unit_verification.STAGES)
        self.assertEqual(len(set(STAGES)), 5)


class StageSummaryTests(unittest.TestCase):
    def test_search_metric_excludes_pre_search_losses_from_denominator(self):
        rows = [{'id': 'A', 'stage': 'retrieved'}, {'id': 'B', 'stage': 'search_failure'},
                {'id': 'C', 'stage': 'extraction_loss'}, {'id': 'D', 'stage': 'fragment_loss'}]
        summary = stage_summary(rows)
        self.assertEqual(summary['cases'], 4)
        self.assertEqual(summary['searchable_cases'], 2)
        self.assertEqual(summary['hit_at_3_given_evidence_indexed'], .5)
        self.assertEqual(summary['search_failure_ids'], ['B'])
        self.assertEqual(summary['pre_search_loss_ids'], ['C', 'D'])

    def test_every_stage_is_reported_even_with_zero_cases(self):
        summary = stage_summary([{'id': 'A', 'stage': 'retrieved'}])
        self.assertEqual(summary['by_stage'], {s: int(s == 'retrieved') for s in STAGES})
        self.assertEqual(summary['hit_at_3_given_evidence_indexed'], 1)

    def test_no_searchable_cases_has_no_invented_rate(self):
        self.assertIsNone(stage_summary([{'id': 'C', 'stage': 'unit_loss'}])['hit_at_3_given_evidence_indexed'])
        self.assertIsNone(stage_summary([])['hit_at_3_given_evidence_indexed'])

    def test_unknown_stage_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Etapa desconocida'):
            stage_summary([{'id': 'A', 'stage': 'ok'}])


if __name__ == '__main__':
    unittest.main()
