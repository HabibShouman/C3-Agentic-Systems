"""Rebuild the fictional business PDF from business_data.json; reportlab is a dev dependency."""
import json
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT):
    data = json.loads((root / "me" / "business_data.json").read_text(encoding="utf-8"))
    target = root / "me" / "about_business.pdf"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ProfileTitle", fontName="Helvetica-Bold", fontSize=25, leading=29,
                              textColor=colors.HexColor("#173F52"), spaceAfter=7))
    styles.add(ParagraphStyle(name="ProfileBody", fontName="Helvetica", fontSize=9.2, leading=13, spaceAfter=6))
    styles.add(ParagraphStyle(name="ProfileHeading", fontName="Helvetica-Bold", fontSize=11, leading=14,
                              textColor=colors.HexColor("#127C80"), spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name="ProfileSmall", fontName="Helvetica", fontSize=8, leading=10.5))
    body = lambda text: Paragraph(escape(text), styles["ProfileBody"])
    small = lambda text: Paragraph(escape(text), styles["ProfileSmall"])
    story = [Paragraph(escape(data["name"]), styles["ProfileTitle"]),
             body("Fictional business profile | Agentic Systems | Habib Shouman"),
             Paragraph("Purpose and customers", styles["ProfileHeading"]),
             body(data["mission"] + " " + data["audience"]), body(data["value_proposition"]),
             Paragraph("Workshop catalog", styles["ProfileHeading"])]
    rows = [[small(x) for x in ["Workshop", "Delivery and sessions", "Tuition", "Prerequisites and outcome"]]]
    for service in data["services"].values():
        rows.append([small(service["name"]), small(f"{service['delivery']}; {service['sessions']} sessions"),
                     small(f"USD {service['price_usd']} per learner"),
                     small(service["prerequisites"] + ". " + service["outcome"] + ".")])
    table = Table(rows, colWidths=[32*mm, 42*mm, 27*mm, 67*mm], hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E2F1F2")),
                               ("VALIGN", (0,0), (-1,-1), "TOP"),
                               ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#C8D8DD")),
                               ("INNERGRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D5E0E3")),
                               ("LEFTPADDING", (0,0), (-1,-1), 7),
                               ("RIGHTPADDING", (0,0), (-1,-1), 7),
                               ("TOPPADDING", (0,0), (-1,-1), 7),
                               ("BOTTOMPADDING", (0,0), (-1,-1), 7)]))
    story += [table, Paragraph("Fictional team", styles["ProfileHeading"])]
    for person in data["team"]:
        story.append(body(person["name"] + " - " + person["role"] + ". " + person["profile"]))
    story.append(Paragraph("Operating policies and boundaries", styles["ProfileHeading"]))
    for key in ["hours", "group_discount", "reschedule", "quotes", "availability", "unknowns", "contact", "privacy"]:
        story.append(body(data["policies"][key]))
    def footer(canvas, doc):
        canvas.setStrokeColor(colors.HexColor("#127C80"))
        canvas.line(20*mm, 18*mm, 190*mm, 18*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#4D6672"))
        canvas.drawString(20*mm, 13*mm, "Teaching scenario only | All business and team details are invented")
        canvas.drawRightString(190*mm, 13*mm, str(doc.page))
    SimpleDocTemplate(str(target), pagesize=(210*mm, 297*mm), rightMargin=20*mm,
                      leftMargin=20*mm, topMargin=17*mm, bottomMargin=23*mm,
                      title="CircuitBridge Learning - Fictional Business Profile", author="Habib Shouman").build(story, onFirstPage=footer, onLaterPages=footer)
    return target


if __name__ == "__main__":
    print(build())
