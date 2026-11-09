"""
Generate Smart_Share_Final_Project_Report_Updated.pdf
Matches the exact academic style, color palette, headers, footers, tables,
and typography of the original NOVEX 2026 report, while embedding genuine screenshots
and updating Phase 5B/5C status consistently.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# Page geometry
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 56.69  # 20 mm
RIGHT_MARGIN = 56.69
TOP_MARGIN = 50.0
BOTTOM_MARGIN = 48.0
USABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# Color palette
C_NAVY = colors.HexColor("#0B1F3A")      # Primary deep navy
C_CYAN = colors.HexColor("#00A8CC")      # Accent cyan / bright teal
C_AMBER = colors.HexColor("#E5A823")     # Warning / highlight amber
C_SLATE = colors.HexColor("#5B6B7F")     # Muted slate gray
C_BODY = colors.HexColor("#1F2937")      # Dark charcoal body text
C_LIGHT_BG = colors.HexColor("#F5F8FB")  # Table alternating row
C_BORDER = colors.HexColor("#E2E8F0")    # Subtle border gray
C_BOX_BG = colors.HexColor("#F8FAFC")    # Placeholder box bg


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that adds:
    - Cover page background styling (page 1)
    - Running headers, accent rules, running footers, and page numbers (pages 2+)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        page_num = self._pageNumber
        if page_num == 1:
            # Cover page background
            self.saveState()
            self.setFillColor(C_NAVY)
            self.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
            
            # Cyan top rule
            self.setFillColor(C_CYAN)
            self.rect(0, PAGE_HEIGHT - 39.7, PAGE_WIDTH, 3.0, fill=True, stroke=False)
            
            # Decorative network graph on cover
            self.setStrokeColor(C_CYAN)
            self.setLineWidth(2.2)
            nodes = [(113.4, 501.7), (212.6, 558.4), (311.8, 479.1), (425.2, 547.1)]
            for i in range(len(nodes) - 1):
                self.line(nodes[i][0], nodes[i][1], nodes[i+1][0], nodes[i+1][1])
            self.setFillColor(C_NAVY)
            for nx, ny in nodes:
                self.circle(nx, ny, 5.0, fill=True, stroke=True)
            self.restoreState()
        else:
            # Running header for pages 2+
            self.saveState()
            header_y = 807.87
            header_h = 34.02
            
            # Header dark navy bar
            self.setFillColor(C_NAVY)
            self.rect(0, header_y, PAGE_WIDTH, header_h, fill=True, stroke=False)
            
            # Cyan accent line at bottom of header
            self.setFillColor(C_CYAN)
            self.rect(0, header_y, PAGE_WIDTH, 1.6, fill=True, stroke=False)
            
            # Header text (white)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 9.0)
            self.drawString(LEFT_MARGIN, 819.21, "SMART SHARE")
            self.setFont("Helvetica", 8.0)
            self.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 819.21, "NOVEX 2026  |  Final Project Report")
            
            # Footer text (slate gray)
            self.setFillColor(C_SLATE)
            self.setFont("Helvetica", 8.0)
            self.drawString(LEFT_MARGIN, 28.35, "Same Direction. Similar Timing. One Shared Ride.")
            self.drawRightString(PAGE_WIDTH - RIGHT_MARGIN, 28.35, f"Page {page_num}")
            self.restoreState()


def build_pdf(filename="Smart_Share_Final_Project_Report_Updated.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    style_cover_cat = ParagraphStyle(
        'CoverCat',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=C_CYAN,
        spaceAfter=15
    )
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=34,
        leading=40,
        textColor=colors.white,
        spaceAfter=10
    )
    style_cover_subtitle = ParagraphStyle(
        'CoverSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=18,
        textColor=C_CYAN,
        spaceAfter=15
    )
    style_cover_tagline = ParagraphStyle(
        'CoverTagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=12,
        leading=16,
        textColor=colors.white,
        spaceAfter=40
    )
    style_cover_meta = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=colors.HexColor("#CBD5E1")
    )
    style_cover_meta_label = ParagraphStyle(
        'CoverMetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=16,
        textColor=colors.white
    )
    style_cover_status = ParagraphStyle(
        'CoverStatus',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#94A3B8"),
        alignment=TA_LEFT
    )

    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=C_NAVY,
        spaceBefore=14,
        spaceAfter=4
    )
    style_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=C_NAVY,
        spaceBefore=10,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=C_BODY,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    style_bullet = ParagraphStyle(
        'ReportBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=C_BODY,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )
    style_caption = ParagraphStyle(
        'ReportCaption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.8,
        leading=10.5,
        textColor=C_SLATE,
        alignment=TA_CENTER,
        spaceBefore=3,
        spaceAfter=8
    )
    style_table_header = ParagraphStyle(
        'ReportTableH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10.0,
        textColor=colors.white
    )
    style_table_cell = ParagraphStyle(
        'ReportTableC',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.8,
        textColor=C_BODY
    )
    style_table_cell_bold = ParagraphStyle(
        'ReportTableCBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.8,
        textColor=C_BODY
    )
    style_callout = ParagraphStyle(
        'ReportCallout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11.5,
        textColor=C_SLATE,
        spaceBefore=4,
        spaceAfter=6
    )
    style_placeholder = ParagraphStyle(
        'ReportPlaceholder',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.0,
        leading=11.0,
        textColor=C_SLATE,
        alignment=TA_CENTER
    )

    def heading_with_accent(title_text):
        """Creates an H1 heading with the signature 40mm cyan accent line underneath."""
        return [
            Paragraph(title_text, style_h1),
            Table([['']], colWidths=[113.4], rowHeights=[2.2], style=[
                ('BACKGROUND', (0,0), (-1,-1), C_CYAN),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ]),
            Spacer(1, 6)
        ]

    story = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("NOVEX 2026  |  FINAL PROJECT REPORT", style_cover_cat))
    story.append(Spacer(1, 20))
    story.append(Paragraph("SMART SHARE", style_cover_title))
    story.append(Paragraph("Intelligent, location-based cab pooling for Mumbai", style_cover_subtitle))
    story.append(Paragraph("Same Direction. Similar Timing. One Shared Ride.", style_cover_tagline))
    story.append(Spacer(1, 160))
    
    meta_table_data = [
        [Paragraph("Team name:", style_cover_meta_label), Paragraph("Terminal 1", style_cover_meta)],
        [Paragraph("Category:", style_cover_meta_label), Paragraph("Smart Automation", style_cover_meta)],
        [Paragraph("Submission date:", style_cover_meta_label), Paragraph("November 2026", style_cover_meta)],
        [Paragraph("Target Geography:", style_cover_meta_label), Paragraph("Mumbai, Maharashtra, India", style_cover_meta)],
    ]
    t_meta = Table(meta_table_data, colWidths=[120, 300])
    t_meta.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 30))
    story.append(Paragraph(
        "<b>Status statement:</b> Ride-matching suggestions, statutory fare estimation (Phase 5B), and "
        "solo-proportional fare allocation with DEC-013 consent (Phase 5C) are implemented locally; "
        "ride acceptance, cab booking, payments and hosted two-user acceptance testing are pending.",
        style_cover_status
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: CONTENTS & READING GUIDE
    # =========================================================================
    story.extend(heading_with_accent("Contents"))
    contents_items = [
        ("1. Abstract", "Page 3"),
        ("2. Problem Statement", "Page 4"),
        ("3. Proposed Solution", "Page 5"),
        ("4. Objectives", "Page 6"),
        ("5. Key Features", "Page 7"),
        ("6. Technology / Tech Stack", "Page 8"),
        ("7. System Architecture", "Page 9"),
        ("8. Implementation", "Page 10"),
        ("9. Results / Screenshots & Test Evidence", "Page 11"),
        ("10. Innovation", "Page 14"),
        ("11. Impact", "Page 14"),
        ("12. Future Scope", "Page 15"),
        ("13. References", "Page 15"),
    ]
    toc_data = [[Paragraph(f"<b>{c[0]}</b>", style_body), Paragraph(c[1], style_callout)] for c in contents_items]
    t_toc = Table(toc_data, colWidths=[380, 100])
    t_toc.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(t_toc)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(
        "<b>Reading guide.</b> This report separates intended design from what has been built and verified. "
        "Every feature carries one of three labels: <i>Implemented and tested</i>, "
        "<i>Implemented, awaiting complete end-to-end verification</i>, or <i>Planned</i>. "
        "Test figures come from the project's own verification reports; nothing here is an unverified user outcome.",
        style_callout
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: SECTION 1 | ABSTRACT
    # =========================================================================
    story.extend(heading_with_accent("Section 1  |  Abstract"))
    story.append(Paragraph(
        "Smart Share is a mobile-first platform that helps people discover others whose journeys are compatible with "
        "theirs, so that they can share a cab instead of booking separate ones. People leaving the same station, airport, "
        "event or business district at about the same time, heading in a similar direction, rarely know about each other. "
        "Smart Share lets a user post a ride request (pickup, destination, departure window, seats, and the maximum extra "
        "minutes they accept) and returns a ranked list of compatible requests with an explanation of why each was suggested.",
        style_body
    ))
    story.append(Paragraph(
        "The matching engine is location-aware and time-aware. It uses PostGIS to shortlist nearby pickups, then checks "
        "departure-window overlap, travel direction and seat capacity. It evaluates the valid pickup and drop-off orders for "
        "a pair, using OSRM road-network durations (with a clearly labelled approximate fallback), and keeps only pairings "
        "that stay inside each rider's detour limit. Pre-trip fare estimation (Phase 5B) implements the official Mumbai "
        "black-and-yellow taxi tariff with continuous linear calculation and Asia/Kolkata night surcharge windows. Pairwise "
        "cost allocation (Phase 5C) computes proportional shares based on solo baselines, conserving exact integer paise "
        "down to ₹0.00 while strictly gating exact contribution disclosures behind DEC-013 bilateral affirmative consent.",
        style_body
    ))
    story.append(Paragraph(
        "The stack is React, TypeScript and Vite on the front end; Python, FastAPI and SQLAlchemy 2 on the back end; "
        "PostgreSQL 17 with PostGIS 3.3 hosted on Supabase; and Supabase Auth with backend ES256 JWT verification via JWKS.",
        style_body
    ))
    story.append(Paragraph(
        "Expected benefits are lower individual fares, better seat utilisation and fewer separate trips. These are expected "
        "benefits and have not been measured. Smart Share currently produces ranked suggestions and fare estimates; it does "
        "not book cabs, assign drivers or process payments.",
        style_body
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: SECTION 2 | PROBLEM STATEMENT
    # =========================================================================
    story.extend(heading_with_accent("Section 2  |  Problem Statement"))
    story.append(Paragraph(
        "In dense cities such as Mumbai, many people start journeys from the same place, at nearly the same time, "
        "towards the same or neighbouring destinations. Yet each person typically books a separate cab, because there is "
        "no easy way to find out who else is going their way.",
        style_body
    ))
    story.append(Paragraph("<b>Typical situations:</b>", style_h2))
    story.append(Paragraph("• <b>Railway stations</b> (for example Dadar or CSMT): many commuters leave the same exit within minutes of each other.", style_bullet))
    story.append(Paragraph("• <b>Airports</b> (for example Mumbai T2 CSMIA): arriving passengers head to nearby suburbs in a similar direction.", style_bullet))
    story.append(Paragraph("• <b>Events and functions</b>: a college festival, concert, or wedding ends, and hundreds of guests leave at once.", style_bullet))
    story.append(Paragraph("• <b>Busy commercial areas</b> (for example BKC): office crowds travel to similar residential corridors in the evening.", style_bullet))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Informal coordination through messaging groups is manual and unreliable. Even when two travellers find each "
        "other, they cannot easily judge whether sharing is practical: how far apart the pickups are, whether their departure "
        "times line up, or whether one rider would face an intolerable backtracking detour. Straight-line closeness is misleading in "
        "Mumbai; the project design notes show that two pickups at the same station can head in opposite directions "
        "(Dadar to Colaba versus Dadar to Borivali), and that water bodies (Mahim Bay, Mithi River) make nearby points far apart by road.",
        style_body
    ))
    story.append(Paragraph(
        "<b>The consequences are unnecessary separate journeys, higher individual costs, underused vehicle capacity and added congestion near crowded venues.</b>",
        style_body
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: SECTION 3 | PROPOSED SOLUTION
    # =========================================================================
    story.extend(heading_with_accent("Section 3  |  Proposed Solution"))
    story.append(Paragraph(
        "Smart Share connects riders through ride requests. A user signs in, creates a request, and asks the system to "
        "find compatible requests from other users.",
        style_body
    ))
    story.append(Paragraph("• <b>Create a ride request:</b> Choose a pickup and a destination (the current UI offers Mumbai landmark presets such as BKC, Airport T2, Powai, Lower Parel, Dadar and Andheri West).", style_bullet))
    story.append(Paragraph("• <b>Select a departure window:</b> State earliest and latest acceptable departure time.", style_bullet))
    story.append(Paragraph("• <b>State constraints:</b> Select seats needed (1–6) and maximum acceptable extra travel time (+0m to +60m).", style_bullet))
    story.append(Paragraph("• <b>Find matches:</b> The backend discovers candidates, filters them through spatial/temporal gates, and evaluates route sequences.", style_bullet))
    story.append(Paragraph("• <b>Review ranked suggestions:</b> View composite compatibility score, each rider's estimated detour, the pickup/drop-off sequence, and route accuracy notices.", style_bullet))
    story.append(Paragraph("• <b>Fare estimation & DEC-013 consent:</b> Inspect the pre-trip fare estimate and privacy-safe economic status; affirmatively opt-in to reveal exact proportional contributions.", style_bullet))
    story.append(Spacer(1, 6))

    # Flow Diagram Box
    journey_flow_data = [
        [
            Paragraph("<b>1. Sign In</b><br/>Supabase Auth", style_table_cell),
            Paragraph("<b>2. Create Request</b><br/>Pickup & Destination", style_table_cell),
            Paragraph("<b>3. Constraints</b><br/>Window, Seats, Detour", style_table_cell),
            Paragraph("<b>4. Find Matches</b><br/>Spatial Discovery", style_table_cell),
            Paragraph("<b>5. Ranked Results</b><br/>Route Fit & Explanations", style_table_cell),
            Paragraph("<b>6. Fares & Consent</b><br/>DEC-013 Proportional", style_table_cell),
        ]
    ]
    t_journey = Table(journey_flow_data, colWidths=[USABLE_WIDTH/6.0]*6)
    t_journey.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_CYAN),
        ('INNERGRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_journey)
    story.append(Paragraph("Figure 1. End-to-end user journey in the Smart Share application.", style_caption))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>How candidates are found:</b> The engine shortlists active, unexpired requests from other users within 2 km of the "
        "pickup, with overlapping departure windows and combined seats of at most four. It then rejects pairs travelling in "
        "clearly different directions (>90° divergence), evaluates the valid pickup/drop-off orders using road-network durations, and discards "
        "any order where either rider's extra time exceeds their own stated limit. Survivors are scored and the top five are returned.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Scope note:</b> Automatic cab dispatch, driver assignment, and payment processing are explicitly out of MVP scope.",
        style_callout
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: SECTION 4 | OBJECTIVES
    # =========================================================================
    story.extend(heading_with_accent("Section 4  |  Objectives"))
    story.append(Paragraph("<b>Technical Objectives</b>", style_h2))
    story.append(Paragraph("• Discover compatible passengers with location-aware spatial queries (PostGIS geography, GiST index).", style_bullet))
    story.append(Paragraph("• Apply time-aware matching through departure-window intersection.", style_bullet))
    story.append(Paragraph("• Evaluate direction and destination compatibility, rejecting backtracking pairings.", style_bullet))
    story.append(Paragraph("• Evaluate valid pickup/drop-off orders and keep each rider's detour within their stated limit.", style_bullet))
    story.append(Paragraph("• Provide deterministic, statutory pre-trip fare estimation using the approved Mumbai taxi tariff model.", style_bullet))
    story.append(Paragraph("• Allocate shared costs proportionally to solo baselines, conserving exact paise down to ₹0.00.", style_bullet))
    story.append(Paragraph("• Enforce DEC-013 bilateral consent to protect passenger privacy and prevent unilateral financial inference.", style_bullet))
    story.append(Paragraph("• Maintain a scalable foundation: modular services, replaceable routing adapters, Alembic migrations, and automated tests.", style_bullet))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>User-Impact Objectives</b>", style_h2))
    story.append(Paragraph("• Make it easy to find fellow travellers, reducing reliance on duplicate solo cab journeys.", style_bullet))
    story.append(Paragraph("• Improve vehicle seat occupancy during high-demand congestion hours.", style_bullet))
    story.append(Paragraph("• Minimise detour delays through strict passenger-configured detour ceilings.", style_bullet))
    story.append(Paragraph("• Offer an accessible, mobile-first experience with intuitive landmark presets and clear status feedback.", style_bullet))
    story.append(Paragraph("• Help passengers clearly understand whether pooling saves money through honest, non-manipulated economic indicators.", style_bullet))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<i>The user-impact objectives represent engineering design goals. Pilot conversion and savings targets remain subject to hosted user trials.</i>",
        style_callout
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: SECTION 5 | KEY FEATURES
    # =========================================================================
    story.extend(heading_with_accent("Section 5  |  Key Features"))
    story.append(Paragraph(
        "Feature status is verified against repository code, test suites, and database migrations. "
        "<i>Tested</i> denotes automated test verification, plus live database checks where noted.",
        style_callout
    ))

    feat_data = [
        [Paragraph("Feature", style_table_header), Paragraph("Planned", style_table_header), Paragraph("Implemented", style_table_header), Paragraph("Tested", style_table_header), Paragraph("Status", style_table_header)],
        [Paragraph("Supabase Auth with backend JWT verification (ES256/JWKS)", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Auth test suite (18 tests)", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("User profiles (retrieve/update)", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("API tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("Ride request create, list, view, edit, cancel; ownership checks", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("API + model tests; UI tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("Landmark presets, departure window, seats, detour preference", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("UI component tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("PostGIS candidate filtering (2 km radius, window overlap, LIMIT 20)", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Unit tests; live PostGIS run (rollback)", style_table_cell), Paragraph("Implemented and tested; browser E2E pending", style_table_cell_bold)],
        [Paragraph("Direction and seat-capacity checks", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Unit tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("Pairwise stop-order evaluation & per-rider detour limits", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Unit tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("Weighted scoring, ranking (top 5), and match explanations", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Unit, API and UI tests", style_table_cell), Paragraph("Implemented; hosted 2-user E2E pending", style_table_cell_bold)],
        [Paragraph("OSRM road-network durations and approximate fallback", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Adapter and fallback tests", style_table_cell), Paragraph("Implemented and tested (best-effort)", style_table_cell_bold)],
        [Paragraph("Statutory Mumbai taxi fare estimation (Phase 5B)", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Tariff, pulse, night-window tests", style_table_cell), Paragraph("Implemented and tested", style_table_cell_bold)],
        [Paragraph("Solo-proportional fare allocation & DEC-013 consent (Phase 5C)", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("12 invariant tests; paise conservation", style_table_cell), Paragraph("Implemented (local verified; hosted pending)", style_table_cell_bold)],
        [Paragraph("Match acceptance / decline, ride groups, proposal expiry", style_table_cell), Paragraph("Yes", style_table_cell), Paragraph("No", style_table_cell), Paragraph("-", style_table_cell), Paragraph("Planned (Phase 7)", style_table_cell)],
        [Paragraph("Cab booking, payments, live dispatch, vehicle tracking", style_table_cell), Paragraph("Future", style_table_cell), Paragraph("No", style_table_cell), Paragraph("-", style_table_cell), Paragraph("Out of MVP scope", style_table_cell)],
    ]
    t_feat = Table(feat_data, colWidths=[150, 42, 58, 120, 111.9])
    t_feat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG]),
    ]))
    story.append(t_feat)
    story.append(Paragraph("Table 1. Feature-status matrix (reflecting verified Phase 5B/5C implementation).", style_caption))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>Scoring model (as implemented):</b>", style_h2))
    story.append(Paragraph(
        "Composite score = 30% pickup proximity + 30% destination similarity & direction + 20% departure-time compatibility + "
        "20% individual detour headroom. Seat capacity is a hard eligibility gate, not a scoring factor. "
        "Ties are broken by lower total detour, then smaller pickup separation.",
        style_body
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: SECTION 6 | TECHNOLOGY / TECH STACK
    # =========================================================================
    story.extend(heading_with_accent("Section 6  |  Technology / Tech Stack"))
    
    # Tech stack summary box
    tech_box_data = [
        [Paragraph("<b>Frontend:</b> React 18 · TypeScript · Vite · Vitest · Tailwind CSS", style_table_cell)],
        [Paragraph("<b>Backend:</b> Python 3.14 · FastAPI · SQLAlchemy 2 (async) · Pydantic v2", style_table_cell)],
        [Paragraph("<b>Database:</b> PostgreSQL 17.11 · PostGIS 3.3.7 · Supabase (hosted) · Alembic migrations", style_table_cell)],
        [Paragraph("<b>Identity & Auth:</b> Supabase Auth · ES256 asymmetric JWT verification via JWKS", style_table_cell)],
        [Paragraph("<b>Routing:</b> OSRM Table API adapter · Calibrated tortuosity fallback (geodesic × 1.40, 22 km/h)", style_table_cell)],
        [Paragraph("<b>Quality & CI:</b> Pytest (backend) · Vitest (frontend) · Ruff · Oxlint · TypeScript compiler", style_table_cell)],
    ]
    t_techbox = Table(tech_box_data, colWidths=[USABLE_WIDTH])
    t_techbox.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_CYAN),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_techbox)
    story.append(Paragraph("Figure 2. Technology stack, limited to components documented as implemented.", style_caption))
    story.append(Spacer(1, 4))

    tech_table_data = [
        [Paragraph("Technology", style_table_header), Paragraph("Purpose in Smart Share", style_table_header), Paragraph("Why it fits", style_table_header)],
        [Paragraph("React, TypeScript, Vite", style_table_cell_bold), Paragraph("Mobile-first UI, forms, and match results", style_table_cell), Paragraph("Fast dev builds, typed props, rich ecosystem", style_table_cell)],
        [Paragraph("Python, FastAPI", style_table_cell_bold), Paragraph("REST API under /api/v1 and matching engine", style_table_cell), Paragraph("High async throughput, clean dependency injection", style_table_cell)],
        [Paragraph("Pydantic v2", style_table_cell_bold), Paragraph("Request/response schema validation & DEC-013 redaction", style_table_cell), Paragraph("Guarantees private fields are omitted from wire payloads", style_table_cell)],
        [Paragraph("PostgreSQL + PostGIS", style_table_cell_bold), Paragraph("Geography(Point, 4326) storage and spatial queries", style_table_cell), Paragraph("ST_DWithin with GiST index accelerates pickup filtering", style_table_cell)],
        [Paragraph("Supabase (hosted)", style_table_cell_bold), Paragraph("Managed PostgreSQL, PostGIS, and user authentication", style_table_cell), Paragraph("Reliable hosted cloud DB without DevOps overhead", style_table_cell)],
        [Paragraph("Alembic", style_table_cell_bold), Paragraph("Versioned database schema migrations (c5d013c0a501)", style_table_cell), Paragraph("Deterministic, additive, reviewable schema evolution", style_table_cell)],
        [Paragraph("Supabase Auth / JWKS", style_table_cell_bold), Paragraph("User sign-in; backend verifies ES256 bearer tokens", style_table_cell), Paragraph("Cryptographically derived identity, zero passwords stored", style_table_cell)],
        [Paragraph("OSRM (+ Fallback)", style_table_cell_bold), Paragraph("Road-network travel durations for detour calculations", style_table_cell), Paragraph("Zero-credential routing with graceful offline degradation", style_table_cell)],
        [Paragraph("Pytest, Ruff, Oxlint, tsc", style_table_cell_bold), Paragraph("Automated unit/API tests, static linting, and type checking", style_table_cell), Paragraph("Prevents regressions and enforces strict code cleanliness", style_table_cell)],
    ]
    t_tech = Table(tech_table_data, colWidths=[120, 180, 181.9])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG]),
    ]))
    story.append(t_tech)
    story.append(Paragraph("Table 2. Technologies and architecture rationale.", style_caption))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: SECTION 7 | SYSTEM ARCHITECTURE
    # =========================================================================
    story.extend(heading_with_accent("Section 7  |  System Architecture"))
    
    # Architecture flow box
    arch_box_data = [
        [Paragraph("<b>Primary Data Flow:</b>", style_table_cell_bold)],
        [Paragraph("User (Mobile Browser) → React Client → Supabase Auth (Sign-in / JWT) → FastAPI Backend (/api/v1) → JWT Verification (JWKS ES256) → Matching Engine → PostGIS (Spatial Discovery) → OSRM Adapter (Road Network Detours) → Fare Estimator (Phase 5B) → Proportional Allocation (Phase 5C) → DEC-013 Consent Filter → Scoped Proposal JSON → React UI.", style_table_cell)],
    ]
    t_arch = Table(arch_box_data, colWidths=[USABLE_WIDTH])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_CYAN),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_arch)
    story.append(Paragraph("Figure 3. System architecture and primary end-to-end data flow.", style_caption))
    story.append(Spacer(1, 4))
    
    story.append(Paragraph(
        "<b>Backend Authoritativeness & Decoupled Routing:</b> The frontend never determines match feasibility or "
        "cost allocation; the backend is authoritative. The routing adapter sits behind a provider interface, allowing "
        "OSRM, OpenRouteService, or the calibrated fallback to be swapped transparently without modifying matching heuristics. "
        "Match proposals are computed dynamically on demand; cancelling or expiring a request automatically excludes it from future queries.",
        style_body
    ))
    story.append(Spacer(1, 4))

    # 8-step matching pipeline table
    steps_data = [
        [Paragraph("1. Spatial Discovery", style_table_cell_bold), Paragraph("PostGIS ST_DWithin <= 2,000m on pickup points with GiST index.", style_table_cell)],
        [Paragraph("2. Temporal Overlap", style_table_cell_bold), Paragraph("Closed-interval departure window intersection [start, end].", style_table_cell)],
        [Paragraph("3. Direction Gate", style_table_cell_bold), Paragraph("Heading bearing difference <= 45° (or <= 90° if destinations within 3km).", style_table_cell)],
        [Paragraph("4. Capacity Gate", style_table_cell_bold), Paragraph("Combined seats requested <= 4 (hard vehicle capacity gate).", style_table_cell)],
        [Paragraph("5. Sequence Evaluation", style_table_cell_bold), Paragraph("Evaluates 4 genuinely shared stop orders out of 6 precedence permutations.", style_table_cell)],
        [Paragraph("6. Detour Verification", style_table_cell_bold), Paragraph("Verifies individual rider extra time stays within stated max_extra_minutes.", style_table_cell)],
        [Paragraph("7. Fare Estimation (5B)", style_table_cell_bold), Paragraph("Computes statutory Mumbai pre-trip fare estimates for shared and solo journeys.", style_table_cell)],
        [Paragraph("8. Allocation & DEC-013 (5C)", style_table_cell_bold), Paragraph("Allocates proportional shares; gates exact contribution behind bilateral consent.", style_table_cell)],
    ]
    t_steps = Table(steps_data, colWidths=[130, 351.9])
    t_steps.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), C_LIGHT_BG),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    story.append(t_steps)
    story.append(Paragraph("Figure 4. Matching engine execution pipeline (Phases 4B, 5B, and 5C).", style_caption))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: SECTION 8 | IMPLEMENTATION
    # =========================================================================
    story.extend(heading_with_accent("Section 8  |  Implementation"))

    # Phase timeline summary box
    phases_summary = [
        [Paragraph("<b>Phase 0:</b> Planning (completed)", style_table_cell), Paragraph("<b>Phase 1:</b> Foundation (completed)", style_table_cell), Paragraph("<b>Phase 2:</b> Database & Auth (completed)", style_table_cell)],
        [Paragraph("<b>Phase 3:</b> Ride Requests (completed)", style_table_cell), Paragraph("<b>Phase 4:</b> Matching Engine (completed)", style_table_cell), Paragraph("<b>Phase 5:</b> Fares & Allocation (5B/5C implemented)", style_table_cell)],
        [Paragraph("<b>Phase 6A:</b> Consent UX (started)", style_table_cell), Paragraph("<b>Phase 7:</b> Group Lifecycle (planned)", style_table_cell), Paragraph("<b>Phases 8-9:</b> Production Deploy (planned)", style_table_cell)],
    ]
    t_phases = Table(phases_summary, colWidths=[USABLE_WIDTH/3.0]*3)
    t_phases.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_CYAN),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    story.append(t_phases)
    story.append(Paragraph("Figure 5. Implementation milestone roadmap (Phase 5 completed locally).", style_caption))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Milestone Summaries:</b>", style_h2))
    story.append(Paragraph("• <b>Phase 0–3:</b> Completed foundational architecture, PostgreSQL/PostGIS schemas, Alembic migrations, Supabase Auth ES256 verification, and authenticated CRUD ride request management.", style_bullet))
    story.append(Paragraph("• <b>Phase 4 (Matching Engine):</b> Implemented spatial shortlisting, 90° direction gating, pairwise stop-order enumeration, detour scoring, and ranked match explanation payloads.", style_bullet))
    story.append(Paragraph("• <b>Phase 5B (Fare Estimation):</b> Implemented statutory Mumbai taxi tariff (₹33 base fare for 1.5 km, ₹21.90/km), Asia/Kolkata night surcharge window (00:00–05:00 IST), and conservative route accuracy tiers (ROAD_ROUTE, MATRIX_SCREENING, CALIBRATED_FALLBACK).", style_bullet))
    story.append(Paragraph("• <b>Phase 5C (Fare Allocation & Privacy):</b> Implemented solo-proportional allocation (DEC-008), deterministic Half-Up integer-paise conservation, economic classification (POSITIVE, BREAK_EVEN, NEGATIVE, CONDITIONAL), and DEC-013 bilateral affirmative consent persistence in <code>match_disclosure_consent_events</code>.", style_bullet))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>Key Technical Challenges & Resolutions:</b>", style_h2))
    chal_data = [
        [Paragraph("Challenge", style_table_header), Paragraph("Resolution", style_table_header)],
        [Paragraph("Straight-line distance misleads in Mumbai (water bodies, opposite headings from Dadar/CSMT)", style_table_cell_bold), Paragraph("Direction gate (hard reject >90°) and OSRM road-network travel durations for detours.", style_table_cell)],
        [Paragraph("Precedence permutations where riders never share cab", style_table_cell_bold), Paragraph("Engine enumerates 6 orders and discards the 2 non-sharing sequences (P1-D1-P2-D2, P2-D2-P1-D1).", style_table_cell)],
        [Paragraph("Public routing service rate limits and downtime", style_table_cell_bold), Paragraph("1.05s request spacing, bounded candidate batching, and calibrated geodesic fallback.", style_table_cell)],
        [Paragraph("PostGIS returned raw hex EWKB for geography columns", style_table_cell_bold), Paragraph("Queries select ST_AsText; parser also decodes raw WKB/EWKB as fallback.", style_table_cell)],
        [Paragraph("Unilateral financial inference risk (DEC-013)", style_table_cell_bold), Paragraph("Bilateral affirmative consent required before exact contribution disclosure; solo baselines remain redacted.", style_table_cell)],
    ]
    t_chal = Table(chal_data, colWidths=[180, 301.9])
    t_chal.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG]),
    ]))
    story.append(t_chal)
    story.append(Paragraph("Table 3. Key engineering challenges and technical resolutions.", style_caption))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 11: SECTION 9 | RESULTS / SCREENSHOTS (PART 1: AUTH & CREATION)
    # =========================================================================
    story.extend(heading_with_accent("Section 9  |  Results / Screenshots"))
    story.append(Paragraph(
        "This section presents visual verification evidence from the running Smart Share application. "
        "Screenshots captured from the running application are distinguished from pending hosted items. "
        "In accordance with academic verification standards, screenshot placeholders remain for unsupplied views.",
        style_callout
    ))
    story.append(Spacer(1, 4))

    # Grid 1: Auth & Profile
    img_auth_path = "report_images/fig_auth.png"
    img_prof_path = "report_images/fig_profile.jpg"
    
    t_img_row1 = Table([
        [
            Image(img_auth_path, width=170, height=210) if os.path.exists(img_auth_path) else Paragraph("[Auth Screen]", style_placeholder),
            Image(img_prof_path, width=195, height=210) if os.path.exists(img_prof_path) else Paragraph("[Profile Screen]", style_placeholder),
        ],
        [
            Paragraph("Figure 9. User authentication interface showing Supabase Auth integration and backend health status.", style_caption),
            Paragraph("Figure 13. Authenticated user profile and onboarding setup interface with development UUID.", style_caption),
        ]
    ], colWidths=[240, 241.9])
    t_img_row1.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_img_row1)
    story.append(Spacer(1, 6))

    # Grid 2: Request Creation & Edit Modal
    img_create_path = "report_images/fig_create.jpg"
    img_edit_path = "report_images/fig_edit.jpg"

    t_img_row2 = Table([
        [
            Image(img_create_path, width=170, height=300) if os.path.exists(img_create_path) else Paragraph("[Create Request]", style_placeholder),
            Image(img_edit_path, width=170, height=300) if os.path.exists(img_edit_path) else Paragraph("[Edit Request]", style_placeholder),
        ],
        [
            Paragraph("Figure 10. Ride request creation interface with landmark presets, departure window, and detour slider.", style_caption),
            Paragraph("Figure 12. Ride request details and edit interface for modifying active departure constraints.", style_caption),
        ]
    ], colWidths=[240, 241.9])
    t_img_row2.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_img_row2)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 12: SECTION 9 (PART 2: LISTING & PENDING RESULTS)
    # =========================================================================
    story.extend(heading_with_accent("Section 9  |  Results / Screenshots (Cont.)"))

    # Active Request Listing & Matching Placeholder
    img_list_path = "report_images/fig_list.jpg"

    # Placeholder box for Figure 14 & 15
    placeholder_html = (
        "<b>[ SCREENSHOT PENDING — HOSTED ACCEPTANCE RUN ]</b><br/><br/>"
        "<i>Figure 14 & 15. Match discovery proposals & DEC-013 bilateral fare disclosure.</i><br/><br/>"
        "To be captured during the upcoming live hosted two-user acceptance test between Passenger A "
        "and Passenger B on the deployed Supabase / Render / Vercel infrastructure."
    )
    t_placeholder_box = Table([[Paragraph(placeholder_html, style_placeholder)]], colWidths=[220], rowHeights=[280])
    t_placeholder_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BOX_BG),
        ('BOX', (0,0), (-1,-1), 1, C_SLATE),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))

    t_img_row3 = Table([
        [
            Image(img_list_path, width=170, height=300) if os.path.exists(img_list_path) else Paragraph("[Request Listing]", style_placeholder),
            t_placeholder_box,
        ],
        [
            Paragraph("Figure 11. Active ride request listing with status badges and on-demand 'Find matches' action.", style_caption),
            Paragraph("Figure 14. Ranked match proposals with statutory fare estimates and DEC-013 consent (Pending).", style_caption),
        ]
    ], colWidths=[240, 241.9])
    t_img_row3.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_img_row3)
    story.append(Spacer(1, 8))

    # Placeholder 1 notice
    story.append(Paragraph(
        "<b>Note on Unsupplied Screenshots:</b> Genuine application captures have been inserted for Authentication (Fig. 9), "
        "Request Creation (Fig. 10), Request Listing (Fig. 11), Request Edit (Fig. 12), and User Profile (Fig. 13). "
        "Screenshots for the unauthenticated landing homepage (Placeholder 1) and live two-user consented match results (Fig. 14) "
        "are pending live hosted acceptance verification and are truthfully designated as pending.",
        style_callout
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 13: DOCUMENTED TESTING RESULTS & VERIFICATION STATUS
    # =========================================================================
    story.extend(heading_with_accent("Documented Testing Results & Acceptance"))
    
    test_data = [
        [Paragraph("Evidence Layer", style_table_header), Paragraph("Verified Result", style_table_header), Paragraph("Verification Source", style_table_header)],
        [Paragraph("Full Backend Pytest Suite", style_table_cell_bold), Paragraph("175 passed, 1 skipped (hosted PostGIS sandbox restriction) in 12.70s", style_table_cell), Paragraph("Clean baseline 536c92a (app/tests)", style_table_cell)],
        [Paragraph("Fare & Matching Tests", style_table_cell_bold), Paragraph("51 passed in 0.66s (covering 12 mathematical invariants, tariff & allocation)", style_table_cell), Paragraph("test_fares.py & test_matching_algorithms.py", style_table_cell)],
        [Paragraph("Live PostGIS Query Test", style_table_cell_bold), Paragraph("1 passed in 0.49s against Supabase PostgreSQL inside rolled-back transaction", style_table_cell), Paragraph("test_matching_postgis.py", style_table_cell)],
        [Paragraph("Frontend Vitest Suite", style_table_cell_bold), Paragraph("32 passed across 7 test files in 3.48s", style_table_cell), Paragraph("frontend/src/features/ride-requests", style_table_cell)],
        [Paragraph("Static Quality & Linters", style_table_cell_bold), Paragraph("Ruff (0 errors, 74 files clean), Oxlint (0 errors), tsc --noEmit (0 errors)", style_table_cell), Paragraph("CI quality check suite", style_table_cell)],
        [Paragraph("Production Client Build", style_table_cell_bold), Paragraph("Vite production bundle built successfully in 0.39s (125 kB gzip)", style_table_cell), Paragraph("npm run build", style_table_cell)],
        [Paragraph("Database Migration", style_table_cell_bold), Paragraph("Migration c5d013c0a501 verified on Supabase development DB (ifdmbwjaysspvysoxfpl)", style_table_cell), Paragraph("Alembic current revision", style_table_cell)],
    ]
    t_test = Table(test_data, colWidths=[130, 220, 131.9])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG]),
    ]))
    story.append(t_test)
    story.append(Paragraph("Table 4. Comprehensive test execution evidence across backend, frontend, and database.", style_caption))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>Verification status, stated transparently:</b>", style_h2))
    story.append(Paragraph(
        "<b>Phase 5C Verdict: CONDITIONAL PASS.</b> All mathematical allocation algorithms, non-negative bounds, "
        "proportional solo weights, deterministic integer-paise conservation ($C_A + C_B \\equiv S$), and DEC-013 server-side "
        "redaction filters have passed automated unit and component testing. "
        "However, a live two-user acceptance test between two separate authenticated commuters on deployed infrastructure "
        "(Render/Vercel/Supabase) has not yet been executed. Therefore, complete hosted acceptance remains conditional.",
        style_body
    ))
    story.append(Paragraph(
        "<b>Source Tree State Notice:</b> The Git repository HEAD commit (<code>eef01c7</code>) contains unresolved merge "
        "conflict markers across 6 source files that must be reconciled before deployment to staging/production.",
        style_callout
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 14: SECTION 10 | INNOVATION & SECTION 11 | IMPACT
    # =========================================================================
    story.extend(heading_with_accent("Section 10  |  Innovation"))
    story.append(Paragraph(
        "Smart Share's contribution is not simply splitting a cab fare. It is deciding which strangers can practically "
        "share a journey, and showing why. It combines several checks that simple proximity matching lacks:",
        style_body
    ))
    story.append(Paragraph("• <b>Location-aware spatial discovery:</b> PostGIS geography indexing with 2 km radius shortlisting.", style_bullet))
    story.append(Paragraph("• <b>Time compatibility:</b> Closed-interval overlap of departure windows prevents impossible meetups.", style_bullet))
    story.append(Paragraph("• <b>Direction gating:</b> Rigid bearing checks ensure riders heading in opposite directions are never paired.", style_bullet))
    story.append(Paragraph("• <b>Detour-aware sequence optimization:</b> Evaluates 4 shared stop orders against individual detour tolerances.", style_bullet))
    story.append(Paragraph("• <b>Statutory Mumbai taxi tariff:</b> Accurate pre-trip estimation using official government rate models.", style_bullet))
    story.append(Paragraph("• <b>Solo-proportional fair allocation:</b> Weighting cost contributions by individual solo baselines with zero-paise residual drift.", style_bullet))
    story.append(Paragraph("• <b>DEC-013 Bilateral Consent Privacy:</b> Cryptographic snapshot binding prevents unilateral economic profiling.", style_bullet))
    story.append(Spacer(1, 4))

    # Traditional vs Smart Share Box
    comp_data = [
        [Paragraph("<b>Traditional Approach:</b> Separate bookings → Duplicate cab journeys → Higher individual costs → Empty seats → Street congestion.", style_table_cell)],
        [Paragraph("<b>Smart Share Approach:</b> Intelligent spatial/temporal matching → Feasible pooled routes → Statutory fare estimation → Fair proportional allocation → Bilateral privacy protection.", style_table_cell)],
    ]
    t_comp = Table(comp_data, colWidths=[USABLE_WIDTH])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, C_CYAN),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_comp)
    story.append(Paragraph("Figure 6. Traditional cab booking versus Smart Share intelligent pooling.", style_caption))
    story.append(Spacer(1, 8))

    story.extend(heading_with_accent("Section 11  |  Impact"))
    story.append(Paragraph("<b>EXPECTED impact only. No user adoption, savings or emissions figures have been measured.</b>", style_callout))
    
    impact_data = [
        [Paragraph("Economic", style_table_header), Paragraph("Environmental", style_table_header), Paragraph("Social", style_table_header), Paragraph("Operational", style_table_header)],
        [
            Paragraph("Potential lower travel outlays; improved cost efficiency per passenger.", style_table_cell),
            Paragraph("Fewer duplicate trips, reduced fuel consumption and vehicle tailpipe emissions.", style_table_cell),
            Paragraph("Easier coordination among commuters leaving crowded venues.", style_table_cell),
            Paragraph("Higher vehicle occupancy and reduced bottleneck congestion at hubs.", style_table_cell),
        ]
    ]
    t_impact = Table(impact_data, colWidths=[USABLE_WIDTH/4.0]*4)
    t_impact.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white]),
    ]))
    story.append(t_impact)
    story.append(Paragraph("Figure 7. Expected project impact dimensions (subject to future live deployment trials).", style_caption))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 15: SECTION 12 | FUTURE SCOPE & SECTION 13 | REFERENCES
    # =========================================================================
    story.extend(heading_with_accent("Section 12  |  Future Scope"))
    story.append(Paragraph("All items below represent future development roadmap milestones:", style_callout))
    
    scope_data = [
        [Paragraph("Priority", style_table_header), Paragraph("Milestone Description", style_table_header), Paragraph("Roadmap Link", style_table_header)],
        [Paragraph("Near term", style_table_cell_bold), Paragraph("Reconcile Git merge conflicts and complete authenticated hosted two-user acceptance testing.", style_table_cell), Paragraph("Phase 5C Acceptance", style_table_cell)],
        [Paragraph("Next", style_table_cell_bold), Paragraph("Match acceptance / decline, ride group confirmation, proposal expiry, and safe seat allocation.", style_table_cell), Paragraph("Phase 7", style_table_cell)],
        [Paragraph("Next", style_table_cell_bold), Paragraph("Interactive Leaflet map route visualization and web push status notifications.", style_table_cell), Paragraph("Phases 6–7", style_table_cell)],
        [Paragraph("Later", style_table_cell_bold), Paragraph("Multi-passenger matching optimization (pooling groups of 3 or 4 riders).", style_table_cell), Paragraph("Matching Extension", style_table_cell)],
        [Paragraph("Later", style_table_cell_bold), Paragraph("Production deployment, traffic-aware routing adapter, and realistic load testing.", style_table_cell), Paragraph("Phases 8–9", style_table_cell)],
        [Paragraph("Out of MVP", style_table_cell_bold), Paragraph("Commercial cab-provider API integration, payment gateway processing, and real-time taxi dispatch.", style_table_cell), Paragraph("Future Commercial", style_table_cell)],
    ]
    t_scope = Table(scope_data, colWidths=[70, 311.9, 100])
    t_scope.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_NAVY),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, C_LIGHT_BG]),
    ]))
    story.append(t_scope)
    story.append(Paragraph("Table 5. Future development scope and roadmap priorities.", style_caption))
    story.append(Spacer(1, 8))

    story.extend(heading_with_accent("Section 13  |  References"))
    refs = [
        "React documentation: https://react.dev",
        "Vite build tool: https://vite.dev",
        "TypeScript documentation: https://www.typescriptlang.org/docs/",
        "FastAPI framework: https://fastapi.tiangolo.com",
        "Pydantic v2 documentation: https://docs.pydantic.dev",
        "SQLAlchemy 2.0: https://docs.sqlalchemy.org",
        "Alembic database migrations: https://alembic.sqlalchemy.org",
        "PostgreSQL 17: https://www.postgresql.org/docs/",
        "PostGIS spatial extension: https://postgis.net/documentation/",
        "Supabase documentation: https://supabase.com/docs",
        "OSRM Table service API: https://project-osrm.org/docs/v5.24.0/api/#table-service",
        "pytest testing framework: https://docs.pytest.org",
        "Vitest frontend testing: https://vitest.dev",
        "Ruff Python linter: https://docs.astral.sh/ruff/",
        "Internal Project Documentation: Project Charter; SRS/PRD; System Architecture; Database & API Contracts; Roadmap; Phase 4B Matching Reports; Phase 5B Fare Estimation Design; Phase 5C Proportional Allocation & Privacy Reports.",
    ]
    for r in refs:
        story.append(Paragraph(f"• {r}", style_bullet))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF built successfully: {filename}")


if __name__ == "__main__":
    build_pdf()