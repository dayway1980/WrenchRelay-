"""Professional closeout and pick-list PDF rendering."""

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _paragraph(text: str, style) -> Paragraph:
    return Paragraph(escape(text or "Not recorded.").replace("\n", "<br/>"), style)


def _document(title: str) -> tuple[BytesIO, list, dict]:
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    story = [_paragraph(title, styles["Title"]), Spacer(1, 0.18 * inch)]
    return buffer, story, styles


def _build(buffer: BytesIO, story: list) -> bytes:
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="WrenchRelay AI record",
        author="WrenchRelay AI",
    )
    document.build(story)
    return buffer.getvalue()


def closeout_pdf(work_order: dict, closeout: dict) -> bytes:
    buffer, story, styles = _document(f"Maintenance Record \u00b7 {work_order['work_order_number']}")
    metadata = [["Work order", work_order["work_order_number"]], ["Title", work_order["title"]], ["Status", work_order["status"]], ["Priority", work_order["priority"]]]
    table = Table(metadata, colWidths=[1.25 * inch, 5.65 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 0.25 * inch)])
    sections = [("Technician Summary", "technician_summary"), ("Problem Reported", "problem_reported"), ("Observations and Measurements", "observations"), ("Corrective Action", "corrective_action"), ("Verification and Testing", "verification"), ("Unresolved Conditions", "unresolved_conditions")]
    for heading, key in sections:
        story.extend([_paragraph(heading, styles["Heading3"]), _paragraph(closeout.get(key, ""), styles["BodyText"]), Spacer(1, 0.13 * inch)])
    story.append(_paragraph("Human review is required. This record does not establish equipment safety or work authorization.", styles["Italic"]))
    return _build(buffer, story)


def pick_list_pdf(work_order: dict, kit_items: list[dict]) -> bytes:
    buffer, story, styles = _document(f"Parts Pick List \u00b7 {work_order['work_order_number']}")
    story.extend([_paragraph(work_order["title"], styles["Heading2"]), Spacer(1, 0.15 * inch)])
    rows = [["Item", "Suggested", "Picked", "Used", "Returned", "Provenance"]]
    for item in kit_items or []:
        rows.append([item.get("name", "Part"), str(item.get("suggested", 0)), str(item.get("picked", 0)), str(item.get("used", 0)), str(item.get("returned", 0)), item.get("provenance", "Technician requested")])
    if len(rows) == 1:
        rows.append(["No planned parts", "0", "0", "0", "0", "Work order has no planned parts"])
    table = Table(rows, colWidths=[1.65 * inch, 0.65 * inch, 0.58 * inch, 0.55 * inch, 0.7 * inch, 2.8 * inch], repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("PADDING", (0, 0), (-1, -1), 6), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]))
    story.extend([table, Spacer(1, 0.2 * inch), _paragraph("Quantities are reconciliation fields only. Suggested or picked items do not reduce stock.", styles["Italic"])])
    return _build(buffer, story)
