"""Reproducible synthetic PDF fixtures; never registered as real external manuals."""
from io import BytesIO
from pathlib import Path


HEADERS = ['Message', 'Cause', 'Solution']
ROWS = [['Printer offline', 'Cable disconnected', 'Reconnect cable'],
        ['Paper jam', 'Obstructed paper path', 'Remove jammed paper']]
COLUMN_LINES = [['Left condition first.', 'Left action second.'],
                ['Right condition first.', 'Right action second.']]
SCAN_TEXT = ['SCAN CONTROL SAMPLE', 'Printer offline', 'Check the network cable', 'Restart the printer']


def profile():
    return {'parser': 'pdf-outline-tables-v1', 'content_pdf_page_range': [1, 1],
            'excluded_pdf_page_ranges': [], 'running_header_bottom': 75,
            'running_header_max_font_size': 20, 'footer_height': 50, 'right_sidebar_x0': 600}


def borderless_region():
    return {'bbox': [40, 110, 570, 230], 'tables': 'borderless_tables',
            'reason': 'Controlled sample: cell boundaries verified against drawn text.',
            'settings': {'vertical_strategy': 'explicit', 'horizontal_strategy': 'explicit',
                         'explicit_vertical_lines': [40, 210, 390, 570],
                         'explicit_horizontal_lines': [110, 150, 190, 230]}}


def sample_profile(case):
    value = profile()
    if case == 'borderless':
        value['strategies'] = {'pages': [{'first': 1, 'last': 1,
            'reason': 'Controlled borderless table.', 'regions': [borderless_region()]}]}
    elif case == 'columns':
        value['strategies'] = {'pages': [{'first': 1, 'last': 1, 'text': 'column_text',
            'reason': 'Controlled left-then-right reading order.',
            'columns': [[40, 80, 285, 700], [325, 80, 570, 700]]}]}
    elif case == 'continuation':
        value['content_pdf_page_range'] = [1, 2]
    return value


def build_samples(directory):
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {}

    def canvas(name):
        path = directory/(name+'.pdf')
        if path.exists():
            raise FileExistsError(path)
        paths[name] = path
        return Canvas(str(path), pagesize=(612, 792), invariant=1)

    def title(pdf, text, page):
        pdf.setFont('Helvetica-Bold', 14)
        pdf.drawString(40, 740, text)
        pdf.setFont('Helvetica', 10)
        pdf.drawString(300, 25, str(page))

    def table(pdf, rows, *, ruled):
        xs, ys = [40, 210, 390, 570], [110, 150, 190, 230]
        pdf.setFont('Helvetica', 10)
        for top, row in zip(ys, [HEADERS, *rows]):
            for x, cell in zip(xs, row):
                pdf.drawString(x+8, 792-top-23, cell)
        if ruled:
            for x in xs:
                pdf.line(x, 792-ys[0], x, 792-ys[-1])
            for y in ys:
                pdf.line(xs[0], 792-y, xs[-1], 792-y)

    pdf = canvas('borderless')
    title(pdf, 'CONTROLLED SAMPLE - BORDERLESS TABLE', 1)
    table(pdf, ROWS, ruled=False)
    pdf.showPage()
    pdf.save()

    pdf = canvas('columns')
    title(pdf, 'CONTROLLED SAMPLE - TWO COLUMNS', 1)
    pdf.setFont('Helvetica', 11)
    for x, lines in zip([40, 325], COLUMN_LINES):
        for top, text in zip([120, 135], lines):
            pdf.drawString(x, 792-top, text)
    pdf.showPage()
    pdf.save()

    pdf = canvas('continuation')
    for number, rows in enumerate([ROWS, [
            ['Toner low', 'Cartridge nearly empty', 'Replace cartridge'],
            ['Split row sample', '', 'Unconfirmed continuation']]], 1):
        title(pdf, 'CONTROLLED SAMPLE - CONTINUATION', number)
        table(pdf, rows, ruled=True)
        pdf.showPage()
    pdf.save()

    pdf = canvas('scan')
    # A real image-only PDF generated from known text, not a native text layer.
    image = Image.new('RGB', (1224, 1584), 'white')
    draw = ImageDraw.Draw(image)
    # A bundled ReportLab font avoids a system-font dependency.
    import reportlab
    font = ImageFont.truetype(str(Path(reportlab.__file__).parent/'fonts/Vera.ttf'), 36)
    for index, text in enumerate(SCAN_TEXT):
        draw.text((100, 130+index*80), text, fill='black', font=font)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    pdf.drawImage(ImageReader(buffer), 0, 0, width=612, height=792)
    pdf.showPage()
    pdf.save()
    return paths
