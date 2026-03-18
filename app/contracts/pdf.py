import io
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

NAVY = HexColor('#1A2F4A')
GREY = HexColor('#666666')
LIGHT_GREY = HexColor('#CCCCCC')


def render_pdf(lead, contract) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=1.25*inch, rightMargin=1.25*inch,
        topMargin=1.25*inch, bottomMargin=1.25*inch,
    )

    title_style    = ParagraphStyle('Title',    fontName='Helvetica-Bold', fontSize=16, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6)
    sub_style      = ParagraphStyle('Sub',      fontName='Helvetica',      fontSize=11, textColor=GREY, alignment=TA_CENTER, spaceAfter=4)
    heading_style  = ParagraphStyle('Heading',  fontName='Helvetica-Bold', fontSize=13, textColor=NAVY, spaceBefore=14, spaceAfter=4)
    body_style     = ParagraphStyle('Body',     fontName='Helvetica',      fontSize=11, leading=16,     spaceAfter=8)
    muted_style    = ParagraphStyle('Muted',    fontName='Helvetica',      fontSize=9,  textColor=GREY)
    sig_label      = ParagraphStyle('SigLabel', fontName='Helvetica-Bold', fontSize=10, textColor=NAVY)
    sig_line       = ParagraphStyle('SigLine',  fontName='Helvetica',      fontSize=10)
    center_style   = ParagraphStyle('Center',   fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER)

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph('ComfortLighting.net', title_style))
    story.append(Paragraph('Professional LED Lighting Solutions', sub_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(HRFlowable(width='100%', thickness=2, color=NAVY))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph('LED LIGHTING SERVICES AGREEMENT', center_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f'Client: {lead.company_name}', sub_style))
    story.append(Paragraph(f'Date: {date.today().strftime("%B %d, %Y")}', sub_style))
    story.append(Paragraph(f'Version: {contract.version}', sub_style))
    story.append(Paragraph('CONFIDENTIAL', ParagraphStyle('conf', fontName='Helvetica-Bold', fontSize=10, textColor=GREY, alignment=TA_CENTER, spaceBefore=12)))

    if not contract.approved:
        story.append(Paragraph('— DRAFT — NOT FOR TRANSMISSION —', ParagraphStyle('draft', fontName='Helvetica-Bold', fontSize=12, textColor=HexColor('#CC0000'), alignment=TA_CENTER, spaceBefore=8)))

    story.append(PageBreak())

    # ── Contract sections ─────────────────────────────────────────────────────
    section_labels = [
        ('1. PARTIES',                    contract.section_parties),
        ('2. RECITALS',                   contract.section_recitals),
        ('3. SCOPE OF WORK',              contract.section_scope),
        ('4. COMPENSATION & PAYMENT',     contract.section_compensation),
        ('5. PROJECT TIMELINE',           contract.section_timeline),
        ('6. WARRANTIES',                 contract.section_warranties),
        ('7. PERFORMANCE GUARANTEE',      contract.section_performance),
        ('8. INDEMNIFICATION',            contract.section_indemnification),
        ('9. LIMITATION OF LIABILITY',    contract.section_liability),
        ('10. TERMINATION',               contract.section_termination),
        ('11. DISPUTE RESOLUTION',        contract.section_dispute),
        ('12. GOVERNING LAW',             contract.section_governing_law),
        ('13. NOTICES',                   contract.section_notices),
        ('14. ENTIRE AGREEMENT',          contract.section_entire_agreement),
    ]

    for label, content in section_labels:
        if content:
            story.append(Paragraph(label, heading_style))
            story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GREY, spaceAfter=4))
            story.append(Paragraph(content or '', body_style))

    # ── Signature page ─────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph('15. SIGNATURE BLOCK', heading_style))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT_GREY, spaceAfter=8))
    if contract.section_signatures:
        story.append(Paragraph(contract.section_signatures, body_style))
    story.append(Spacer(1, 0.4*inch))

    sig_data = [
        [Paragraph('SERVICE PROVIDER', sig_label),  Paragraph('CLIENT', sig_label)],
        [Paragraph('ComfortLighting.net LLC', sig_line), Paragraph(lead.company_name, sig_line)],
        [Spacer(1, 0.5*inch), Spacer(1, 0.5*inch)],
        [Paragraph('Signature: ________________________', sig_line), Paragraph('Signature: ________________________', sig_line)],
        [Paragraph('Name: ____________________________', sig_line),  Paragraph('Name: ____________________________', sig_line)],
        [Paragraph('Title: ___________________________', sig_line),  Paragraph('Title: ___________________________', sig_line)],
        [Paragraph('Date:  ___________________________', sig_line),  Paragraph('Date:  ___________________________', sig_line)],
    ]
    sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
    sig_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 0)]))
    story.append(sig_table)

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(f'Contract Ref: {contract.id}-v{contract.version}  |  Effective Date: _______________', muted_style))

    def add_header_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(GREY)
        # Header (skip cover page)
        if doc.page > 1:
            canvas.drawString(1.25*inch, letter[1] - 0.7*inch, 'ComfortLighting.net')
            canvas.drawRightString(letter[0] - 1.25*inch, letter[1] - 0.7*inch, f'Page {doc.page}')
        # Footer
        footer = f'Contract ID: {contract.id}  |  Version {contract.version}  |  {date.today().strftime("%Y-%m-%d")}  |  CONFIDENTIAL'
        canvas.drawCentredString(letter[0]/2, 0.6*inch, footer)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return buf.getvalue()
