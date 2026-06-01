"""Pure-Python PDF generation using reportlab (no system libraries required)."""
import re
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

_PRIMARY    = colors.HexColor('#1e40af')
_SLATE_800  = colors.HexColor('#1e293b')
_SLATE_600  = colors.HexColor('#475569')
_SLATE_200  = colors.HexColor('#e2e8f0')
_SLATE_50   = colors.HexColor('#f8fafc')


def _s():
    return {
        'title':  ParagraphStyle('title',  fontName='Helvetica-Bold', fontSize=16,
                                  textColor=_PRIMARY, spaceAfter=3),
        'meta':   ParagraphStyle('meta',   fontName='Helvetica', fontSize=8,
                                  textColor=_SLATE_600, spaceAfter=10),
        'h1':     ParagraphStyle('h1',     fontName='Helvetica-Bold', fontSize=14,
                                  textColor=_SLATE_800, spaceAfter=6, spaceBefore=14),
        'h2':     ParagraphStyle('h2',     fontName='Helvetica-Bold', fontSize=11,
                                  textColor=_SLATE_800, spaceAfter=4, spaceBefore=10),
        'h3':     ParagraphStyle('h3',     fontName='Helvetica-BoldOblique', fontSize=9.5,
                                  textColor=_SLATE_800, spaceAfter=3, spaceBefore=8),
        'body':   ParagraphStyle('body',   fontName='Helvetica', fontSize=9,
                                  textColor=_SLATE_800, spaceAfter=5, leading=13),
        'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=9,
                                  textColor=_SLATE_800, leftIndent=12, spaceAfter=2, leading=13),
    }


def _tbl_style():
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  _PRIMARY),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 0), (-1, -1), 7),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, _SLATE_50]),
        ('GRID',          (0, 0), (-1, -1), 0.3, _SLATE_200),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
    ])


def _safe(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _inline(text: str) -> str:
    """Escape XML then apply markdown inline → reportlab XML tags."""
    text = _safe(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    text = re.sub(r'`(.+?)`', lambda m: f'<font face="Courier" size="7">{_safe(m.group(1))}</font>', text)
    return text


_SEP_RE = re.compile(r'^\|[-: |]+\|$')


def md_to_pdf(markdown_text: str, title: str, meta: str) -> bytes:
    """Render a Markdown string as a PDF and return the bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm,
    )
    s = _s()
    story: list = [
        Paragraph(title, s['title']),
        Paragraph(meta,  s['meta']),
        HRFlowable(width='100%', color=_SLATE_200, spaceAfter=8),
    ]

    lines = markdown_text.split('\n')
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith('### '):
            story.append(Paragraph(_inline(stripped[4:]), s['h3']))
        elif stripped.startswith('## '):
            story.append(Paragraph(_inline(stripped[3:]), s['h2']))
        elif stripped.startswith('# '):
            story.append(Paragraph(_inline(stripped[2:]), s['h1']))
        elif stripped.startswith(('- ', '* ')):
            story.append(Paragraph(f'• {_inline(stripped[2:])}', s['bullet']))
        elif re.match(r'^\d+\. ', stripped):
            num, rest = stripped.split('. ', 1)
            story.append(Paragraph(f'{_safe(num)}. {_inline(rest)}', s['bullet']))
        elif stripped.startswith('|') and not _SEP_RE.match(stripped):
            # Collect all rows in this markdown table
            table_rows = []
            while i < len(lines):
                row = lines[i].strip()
                if not row.startswith('|'):
                    break
                if not _SEP_RE.match(row):
                    cells = [_safe(c.strip()) for c in row.split('|')[1:-1]]
                    table_rows.append(cells)
                i += 1
            if table_rows:
                t = Table(table_rows)
                t.setStyle(_tbl_style())
                story.append(t)
                story.append(Spacer(1, 6))
            continue
        elif stripped in ('---', '___', '***'):
            story.append(HRFlowable(width='100%', color=_SLATE_200))
        elif stripped:
            story.append(Paragraph(_inline(stripped), s['body']))
        else:
            story.append(Spacer(1, 4))

        i += 1

    doc.build(story)
    return buf.getvalue()


_RED    = colors.HexColor('#dc2626')
_PURPLE = colors.HexColor('#7c3aed')
_AMBER  = colors.HexColor('#d97706')


def _desc_paragraphs(text: str, style) -> list:
    """Split description on blank lines; preserve single-line breaks within blocks."""
    result = []
    for block in re.split(r'\n{2,}', text.strip()):
        block = block.strip()
        if block:
            result.append(Paragraph(_safe(block).replace('\n', '<br/>'), style))
    return result


def talks_to_pdf(rows: list, title: str, meta: str) -> bytes:
    """Render a list of talk dicts as a full-detail per-talk PDF."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm, topMargin=20*mm, bottomMargin=20*mm,
    )

    talk_title_st = ParagraphStyle('et', fontName='Helvetica-Bold', fontSize=11,
                                     textColor=_PRIMARY, spaceAfter=3, spaceBefore=0)
    meta_st        = ParagraphStyle('em', fontName='Helvetica', fontSize=8,
                                     textColor=_SLATE_600, spaceAfter=2, leading=12)
    desc_st        = ParagraphStyle('ed', fontName='Helvetica', fontSize=9,
                                     textColor=_SLATE_800, spaceAfter=0, leading=13,
                                     leftIndent=0)
    s = _s()

    story: list = [
        Paragraph(title, s['title']),
        Paragraph(meta,  s['meta']),
        HRFlowable(width='100%', color=_SLATE_200, spaceAfter=10),
    ]

    for i, r in enumerate(rows):
        if i > 0:
            story.append(HRFlowable(width='100%', color=_SLATE_200,
                                    spaceBefore=10, spaceAfter=10))

        story.append(Paragraph(
            _safe(r['talk_title']),
            talk_title_st,
        ))

        meta1_parts = [
            f'<b>Status:</b> {_safe(r["status"])}',
            f'<b>Type:</b> {_safe(r["type"])}',
            f'<b>Conference:</b> {_safe(r["conference_title"])}',
            f'<b>Assigned:</b> {_safe(r["assigned_to"] or "Unassigned")}',
        ]
        story.append(Paragraph('  |  '.join(meta1_parts), meta_st))

        meta2_parts = [
            f'<b>Conference dates:</b> {_safe(r["conference_start"])} - {_safe(r["conference_end"])}',
            f'<b>DocDB:</b> {_safe(r["docdb_number"] or "-")}',
            f'<b>Plenary:</b> {_safe(r["plenary"])}',
            f'<b>Parallel:</b> {_safe(r["parallel"])}',
            f'<b>Practice:</b> {_safe(r["practice_talk_date"] or "-")}',
            f'<b>Approval:</b> {_safe(r["final_approval"])}',
            f'<b>Given:</b> {_safe(r["complete_given"])}',
        ]
        story.append(Paragraph('  |  '.join(meta2_parts), meta_st))

        desc = (r.get('comments') or '').strip()
        if desc:
            story.append(Spacer(1, 3))
            story.extend(_desc_paragraphs(desc, desc_st))

    if not rows:
        story.append(Paragraph('No talks matched the selected filters.', s['body']))

    doc.build(story)
    return buf.getvalue()
