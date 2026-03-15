from io import BytesIO
from datetime import date

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT

BRAND_BLUE = colors.HexColor('#1F4E79')
GREY = colors.HexColor('#888888')
LIGHT_GREY = colors.HexColor('#CCCCCC')

SECTION_ORDER = [
    ('GREETING',   'greeting'),
    ('PROBLEM',    'problem'),
    ('SOLUTION',   'solution'),
    ('VALUE',      'value_prop'),
    ('NEXT STEP',  'next_step'),
]


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 9)
    canvas.setFillColor(GREY)
    y = 0.5 * inch
    canvas.drawString(doc.leftMargin, y, 'www.comfortlighting.net')
    canvas.drawRightString(letter[0] - doc.rightMargin, y, f'Page {doc.page}')
    canvas.restoreState()


def render_pdf(lead, proposal) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    styles = getSampleStyleSheet()

    style_brand_bold_16 = ParagraphStyle(
        'BrandBold16',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=BRAND_BLUE,
        alignment=TA_LEFT,
    )
    style_grey_right = ParagraphStyle(
        'GreyRight',
        fontName='Helvetica',
        fontSize=11,
        textColor=GREY,
        alignment=TA_RIGHT,
    )
    style_grey_9 = ParagraphStyle(
        'Grey9',
        fontName='Helvetica',
        fontSize=9,
        textColor=GREY,
        alignment=TA_LEFT,
    )
    style_title = ParagraphStyle(
        'Title14',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=BRAND_BLUE,
        alignment=TA_LEFT,
    )
    style_section_label = ParagraphStyle(
        'SectionLabel',
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=BRAND_BLUE,
        alignment=TA_LEFT,
    )
    style_body = ParagraphStyle(
        'Body11',
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        alignment=TA_LEFT,
    )

    story = []

    # 1. Header row
    header_data = [[
        Paragraph('ComfortLighting.net', style_brand_bold_16),
        Paragraph('Professional LED Lighting Solutions', style_grey_right),
    ]]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)

    # 2. HR brand blue
    story.append(HRFlowable(width='100%', thickness=2, color=BRAND_BLUE, spaceAfter=4))

    # 3. Date
    today_str = date.today().strftime('%B %d, %Y')
    story.append(Paragraph(today_str, style_grey_9))

    # 4. Spacer 6
    story.append(Spacer(1, 6))

    # 5. Proposal title
    company = lead.company_name or ''
    story.append(Paragraph(f'Lighting Proposal for {company}', style_title))

    # 6. Address
    if lead.address:
        story.append(Paragraph(lead.address.replace('\n', '<br/>'), style_grey_9))

    # 7. Spacer 12
    story.append(Spacer(1, 12))

    # 8. HR grey thin
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GREY, spaceAfter=6))

    # 9. Sections
    for label, key in SECTION_ORDER:
        content = getattr(proposal, key, '') or ''
        content = content.strip()
        if not content:
            continue
        story.append(Paragraph(label, style_section_label))
        story.append(Paragraph(content.replace('\n', '<br/>'), style_body))
        story.append(Spacer(1, 8))

    # 10. Spacer 20
    story.append(Spacer(1, 20))

    # 11. HR grey thin
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GREY, spaceAfter=6))

    # 12. Footer brand line
    story.append(Paragraph('<b>ComfortLighting.net</b>', style_body))
    story.append(Paragraph('www.comfortlighting.net', style_grey_9))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
