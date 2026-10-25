"""Shared, deterministic rules for extraction and text-index eligibility."""


def normalize_text(text):
    return ' '.join(text.split())


def table_review_flags(headers, grid):
    flags = []
    if any(not h for h in headers) or any(c is None for row in grid for c in row):
        flags.append('complex_or_merged_header_or_cell')
    if any(not normalize_text(c or '') for row in grid[1:] for c in row):
        flags.append('empty_text_cells_may_contain_graphics_or_continuation')
    if any(len(row) != len(headers) for row in grid):
        flags.append('inconsistent_column_count')
    return flags


def render_block_text(block):
    if block['type'] == 'paragraph':
        return block['text']
    return '\n\n'.join('\n'.join(
        f'{header or "Column " + str(i + 1)}: {normalize_text(value) if value is not None else "[merged cell; review raw table]"}'
        for i, (header, value) in enumerate(zip(block['headers'], row['cells'])))
        for row in block['rows'])


def block_indexing_decision(block, *, text_only=False):
    """Review of a continuation link does not merge or disqualify complete rows."""
    reasons = []
    error = False
    if block['type'] == 'table':
        headers = block['headers']
        grid = [headers, *[row['cells'] for row in block['rows']]]
        inferred = table_review_flags(headers, grid)
        reasons.extend(block.get('review_flags', []))
        reasons.extend(code for code in inferred if code not in reasons)
        if block['text_index_eligible'] and (reasons or len(headers) < 2 or not block['rows']):
            error = True
            reasons.append('unsafe_table_index_eligibility')
        if not block['text_index_eligible'] and not reasons:
            reasons.append('table_not_text_index_eligible')
        if block.get('continuation_candidate_of'):
            reasons.append('table_continuation_unconfirmed')
    elif block['type'] != 'paragraph':
        return {'status': 'error', 'text_index_eligible': False, 'reasons': ['unsupported_block_type']}
    text = render_block_text(block)
    if '\ufffd' in text or '(cid:' in text.lower():
        reasons.append('unresolved_glyphs')
    if text_only:
        reasons.append('table_structure_disabled')
    hard_review = any(code != 'table_continuation_unconfirmed' for code in reasons)
    eligible = not error and not hard_review
    if block['type'] == 'table':
        eligible = eligible and block['text_index_eligible']
    return {'status': 'error' if error else ('review' if reasons else 'accepted'),
            'text_index_eligible': eligible, 'reasons': reasons}
