"""Step 8: complete-unit preservation and Spanish retrieval, measured per stage.

Extraction losses, unit/fragment losses and search failures are reported
separately. Nothing here builds indexes, calls providers or edits sources.
"""
from collections import Counter
import unicodedata

STAGES = ('extraction_loss', 'unit_loss', 'fragment_loss', 'search_failure', 'retrieved')


def characters(text):
    # NFKC folds ligatures; whitespace is layout, not content.
    return Counter(c for c in unicodedata.normalize('NFKC', text or '') if not c.isspace())


def squash(text):
    return ' '.join((text or '').split())


def source_accounting(extraction, page_text):
    """Every non-space source character must reappear in extracted or excluded text."""
    accounted = {}

    def add(page, text):
        accounted.setdefault(int(page), Counter()).update(characters(text))

    for section in extraction['sections']:
        add(section['start_pdf_page'], section['title'])
        for block in section['blocks']:
            if block['type'] == 'paragraph':
                add(block['pdf_page'], block['text'])
            elif block['type'] == 'table':
                add(block['pdf_page'], ' '.join(h or '' for h in block['raw_header']))
                for row in block['rows']:
                    add(block['pdf_page'], ' '.join(c or '' for c in row['cells']))
            else:
                raise ValueError(f'Tipo de bloque sin contabilidad: {block["type"]}.')
    for item in extraction['excluded_layout_text']:
        add(item['pdf_page'], item['text'])
    pages, totals = [], Counter()
    for number, text in sorted(page_text.items()):
        source = characters(text)
        found = accounted.get(number, Counter())
        missing, extra = source - found, found - source
        totals.update(source=sum(source.values()), missing=sum(missing.values()),
                      extra=sum(extra.values()))
        if missing or extra:
            pages.append({'pdf_page': number, 'missing': dict(missing), 'extra': dict(extra)})
    unexpected = sorted(set(accounted) - set(page_text))
    return {'pages_checked': len(page_text), 'source_characters': totals['source'],
            'missing_characters': totals['missing'], 'extra_characters': totals['extra'],
            'pages_with_differences': pages, 'accounted_pages_outside_check': unexpected,
            'complete': not pages and not unexpected}


def block_coverage(extraction, units, excluded):
    """Each paragraph and table row ends in a full unit or in an explicit exclusion."""
    reasons = {e['block_id']: e['reason'] for e in excluded}
    texts = {b['id']: b.get('text') for s in extraction['sections'] for b in s['blocks']}
    paragraph_units, row_units = {}, {}
    for unit in units:
        if unit['kind'] == 'section_text':
            for block in unit['source_blocks']:
                paragraph_units.setdefault(block['id'], []).append(unit)
        else:
            row_units.setdefault((unit['row']['table_id'], unit['row']['id']), []).append(unit)
    status, problems = Counter(), []
    for section in extraction['sections']:
        for block in section['blocks']:
            if block['id'] in reasons:
                count = len(block['rows']) if block['type'] == 'table' else 1
                status['excluded_' + block['type'] + ('_rows' if block['type'] == 'table' else 's')] += count
                continue
            if block['type'] == 'paragraph':
                found = paragraph_units.get(block['id'], [])
                # The body must be exactly its source paragraphs in order, not a substring match.
                if (len(found) != 1 or found[0]['section_id'] != section['id']
                        or found[0]['body'] != '\n\n'.join(texts.get(b['id']) or '' for b in found[0]['source_blocks'])):
                    problems.append({'block_id': block['id'], 'issue': 'paragraph_not_in_single_unit'})
                else:
                    status['paragraphs_in_units'] += 1
                continue
            for row in block['rows']:
                found = row_units.get((block['id'], row['id']), [])
                body = squash(found[0]['body']) if len(found) == 1 else ''
                if (len(found) != 1 or found[0]['row']['cells'] != row['cells']
                        or any(squash(c) not in body for c in row['cells'])):
                    problems.append({'block_id': block['id'], 'row_id': row['id'],
                                     'issue': 'row_not_in_single_unit'})
                else:
                    status['table_rows_in_units'] += 1
    return {'status': dict(status), 'problems': problems, 'complete': not problems}


def compare_units(before, after):
    old = {u['unit_id']: u for u in before}
    new = {u['unit_id']: u for u in after}
    duplicated = sorted({i for units in (before, after) for i, n in
                         Counter(u['unit_id'] for u in units).items() if n > 1})
    changed = sorted(i for i in old.keys() & new.keys() if old[i] != new[i])
    return {'before': len(before), 'after': len(after), 'removed': sorted(old.keys() - new.keys()),
            'added': sorted(new.keys() - old.keys()), 'changed': changed, 'duplicated': duplicated,
            'identical': before == after and not duplicated}


def relevant(unit, case):
    """Same relevance rule as the diagnostic Ricoh evaluation; no per-case synonyms."""
    if unit['section_title'] != case['expected_section']:
        return False
    wanted = case.get('expected_row_contains')
    if not wanted:
        return True
    row = unit['row']
    return bool(row) and wanted in ' '.join(squash(c) for c in row['cells'])


def evidence_presence(case, extraction, units, fragments, excluded):
    sections = [s for s in extraction['sections'] if s['title'] == case['expected_section']]
    wanted = case.get('expected_row_contains')
    # Mirrors `relevant`: a section-level case accepts any block of the section.
    blocks = [b for s in sections for b in s['blocks']
              if not wanted or (b['type'] == 'table'
                                and any(wanted in ' '.join(squash(c) for c in r['cells']) for r in b['rows']))]
    excluded_ids = {e['block_id'] for e in excluded}
    matching = [u['unit_id'] for u in units if relevant(u, case)]
    viewed = {f['unit_id'] for f in fragments}
    return {'extraction_sections': [s['id'] for s in sections],
            'extraction_blocks': [b['id'] for b in blocks],
            'excluded_blocks': [b['id'] for b in blocks if b['id'] in excluded_ids],
            'relevant_units': matching,
            'relevant_units_with_fragments': [u for u in matching if u in viewed]}


def classify(presence, rank):
    if not presence['extraction_blocks']:
        return 'extraction_loss'
    if not presence['relevant_units']:
        return 'unit_loss'
    if not presence['relevant_units_with_fragments']:
        return 'fragment_loss'
    return 'search_failure' if rank is None else 'retrieved'


def stage_summary(results):
    unknown = {r['stage'] for r in results} - set(STAGES)
    if unknown:
        raise ValueError(f'Etapa desconocida: {sorted(unknown)}.')
    counts = Counter(r['stage'] for r in results)
    reachable = [r for r in results if r['stage'] in ('search_failure', 'retrieved')]
    return {'cases': len(results), 'by_stage': {s: counts.get(s, 0) for s in STAGES},
            'searchable_cases': len(reachable),
            'hit_at_3_given_evidence_indexed': (sum(r['stage'] == 'retrieved' for r in reachable)
                                                / len(reachable)) if reachable else None,
            'search_failure_ids': [r['id'] for r in results if r['stage'] == 'search_failure'],
            'pre_search_loss_ids': [r['id'] for r in results
                                    if r['stage'] not in ('search_failure', 'retrieved')]}
