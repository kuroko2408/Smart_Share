"""
Generate Smart_Share_Final_Project_Report_Updated.docx
Editable Microsoft Word document matching the updated NOVEX 2026 report.
Includes formatted tables, bullet points, genuine screenshots, and figure captions.
"""

import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    """Sets background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets cell padding in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def build_docx(filename="Smart_Share_Final_Project_Report_Updated.docx"):
    doc = docx.Document()

    # Page setup - A4
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Styles
    COLOR_NAVY = RGBColor(11, 31, 58)
    COLOR_CYAN = RGBColor(0, 168, 204)
    COLOR_SLATE = RGBColor(91, 107, 127)
    COLOR_BODY = RGBColor(31, 41, 55)

    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Helvetica'
    style_normal.font.size = Pt(10)
    style_normal.font.color.rgb = COLOR_BODY

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(15)
        run.font.color.rgb = COLOR_NAVY
        # Add a colored accent line below
        p_line = doc.add_paragraph()
        p_line.paragraph_format.space_before = Pt(0)
        p_line.paragraph_format.space_after = Pt(8)
        run_line = p_line.add_run("―" * 28)
        run_line.bold = True
        run_line.font.size = Pt(8)
        run_line.font.color.rgb = COLOR_CYAN
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = COLOR_NAVY
        return p

    def add_bullet(bold_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            run_b = p.add_run(bold_prefix + " ")
            run_b.bold = True
            run_b.font.color.rgb = COLOR_NAVY
        run_t = p.add_run(text)
        run_t.font.color.rgb = COLOR_BODY
        return p

    def add_caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(10)
        run = p.add_run(text)
        run.italic = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = COLOR_SLATE
        return p

    # --- TITLE & COVER ---
    p_cat = doc.add_paragraph()
    p_cat.paragraph_format.space_before = Pt(30)
    p_cat.paragraph_format.space_after = Pt(10)
    run_cat = p_cat.add_run("NOVEX 2026 | FINAL PROJECT REPORT")
    run_cat.bold = True
    run_cat.font.size = Pt(12)
    run_cat.font.color.rgb = COLOR_CYAN

    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_after = Pt(6)
    run_title = p_title.add_run("SMART SHARE")
    run_title.bold = True
    run_title.font.size = Pt(32)
    run_title.font.color.rgb = COLOR_NAVY

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(15)
    run_sub = p_sub.add_run("Intelligent, location-based cab pooling for Mumbai")
    run_sub.font.size = Pt(14)
    run_sub.font.color.rgb = COLOR_CYAN

    p_tag = doc.add_paragraph()
    p_tag.paragraph_format.space_after = Pt(30)
    run_tag = p_tag.add_run("Same Direction. Similar Timing. One Shared Ride.")
    run_tag.italic = True
    run_tag.font.size = Pt(12)
    run_tag.font.color.rgb = COLOR_SLATE

    # Meta table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.LEFT
    meta_rows = [
        ("Team name:", "Terminal 1"),
        ("Category:", "Smart Automation"),
        ("Submission date:", "November 2026"),
        ("Target Geography:", "Mumbai, Maharashtra, India"),
    ]
    for i, (k, v) in enumerate(meta_rows):
        c0 = meta_table.cell(i, 0)
        c1 = meta_table.cell(i, 1)
        c0.paragraphs[0].add_run(k).bold = True
        c1.paragraphs[0].add_run(v)
        c0.width = Inches(1.8)
        c1.width = Inches(4.5)

    p_status = doc.add_paragraph()
    p_status.paragraph_format.space_before = Pt(40)
    run_st = p_status.add_run(
        "Status statement: Ride-matching suggestions, statutory fare estimation (Phase 5B), and "
        "solo-proportional fare allocation with DEC-013 consent (Phase 5C) are implemented locally; "
        "ride acceptance, cab booking, payments and hosted two-user acceptance testing are pending."
    )
    run_st.italic = True
    run_st.font.size = Pt(8.5)
    run_st.font.color.rgb = COLOR_SLATE

    doc.add_page_break()

    # --- CONTENTS ---
    add_h1("Contents")
    toc_items = [
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
    for item, pg in toc_items:
        p_t = doc.add_paragraph()
        p_t.paragraph_format.space_after = Pt(3)
        r_item = p_t.add_run(item)
        r_item.bold = True
        p_t.add_run(f"  ....................................................................................................  {pg}")

    p_guide = doc.add_paragraph()
    p_guide.paragraph_format.space_before = Pt(20)
    r_g1 = p_guide.add_run("Reading guide. ")
    r_g1.bold = True
    p_guide.add_run(
        "This report separates intended design from what has been built and verified. "
        "Every feature carries one of three labels: Implemented and tested, "
        "Implemented, awaiting complete end-to-end verification, or Planned. "
        "Test figures come from the project's own verification reports; nothing here is an unverified user outcome."
    )
    doc.add_page_break()

    # --- SECTION 1 | ABSTRACT ---
    add_h1("Section 1 | Abstract")
    doc.add_paragraph(
        "Smart Share is a mobile-first platform that helps people discover others whose journeys are compatible with "
        "theirs, so that they can share a cab instead of booking separate ones. People leaving the same station, airport, "
        "event or business district at about the same time, heading in a similar direction, rarely know about each other. "
        "Smart Share lets a user post a ride request (pickup, destination, departure window, seats, and the maximum extra "
        "minutes they accept) and returns a ranked list of compatible requests with an explanation of why each was suggested."
    )
    doc.add_paragraph(
        "The matching engine is location-aware and time-aware. It uses PostGIS to shortlist nearby pickups, then checks "
        "departure-window overlap, travel direction and seat capacity. It evaluates the valid pickup and drop-off orders for "
        "a pair, using OSRM road-network durations (with a clearly labelled approximate fallback), and keeps only pairings "
        "that stay inside each rider's detour limit. Pre-trip fare estimation (Phase 5B) implements the official Mumbai "
        "black-and-yellow taxi tariff with continuous linear calculation and Asia/Kolkata night surcharge windows. Pairwise "
        "cost allocation (Phase 5C) computes proportional shares based on solo baselines, conserving exact integer paise "
        "down to ₹0.00 while strictly gating exact contribution disclosures behind DEC-013 bilateral affirmative consent."
    )
    doc.add_paragraph(
        "The stack is React, TypeScript and Vite on the front end; Python, FastAPI and SQLAlchemy 2 on the back end; "
        "PostgreSQL 17 with PostGIS 3.3 hosted on Supabase; and Supabase Auth with backend ES256 JWT verification via JWKS."
    )
    doc.add_paragraph(
        "Expected benefits are lower individual fares, better seat utilisation and fewer separate trips. These are expected "
        "benefits and have not been measured. Smart Share currently produces ranked suggestions and fare estimates; it does "
        "not book cabs, assign drivers or process payments."
    )
    doc.add_page_break()

    # --- SECTION 2 | PROBLEM STATEMENT ---
    add_h1("Section 2 | Problem Statement")
    doc.add_paragraph(
        "In dense cities such as Mumbai, many people start journeys from the same place, at nearly the same time, "
        "towards the same or neighbouring destinations. Yet each person typically books a separate cab, because there is "
        "no easy way to find out who else is going their way."
    )
    add_h2("Typical Mumbai Scenarios:")
    add_bullet("Railway stations (e.g. Dadar or CSMT):", "Hundreds of commuters leave the same station exits within minutes of each other.")
    add_bullet("Airports (e.g. Mumbai T2 CSMIA):", "Arriving passengers head to neighbouring suburban corridors in similar travel directions.")
    add_bullet("Events and functions:", "Concerts, college festivals, or weddings end, and crowds leave simultaneously.")
    add_bullet("Busy commercial districts (e.g. BKC):", "Office workers commute toward similar residential corridors during evening peak hours.")
    doc.add_paragraph(
        "Informal coordination through messaging groups is manual and unreliable. Even when two travellers find each "
        "other, they cannot easily judge whether sharing is practical: how far apart the pickups are, whether their departure "
        "times line up, or whether one rider would face an intolerable backtracking detour. Straight-line closeness is misleading in "
        "Mumbai; the project design notes show that two pickups at the same station can head in opposite directions "
        "(Dadar to Colaba versus Dadar to Borivali), and that water bodies (Mahim Bay, Mithi River) make nearby points far apart by road."
    )
    doc.add_paragraph(
        "The consequences are unnecessary separate journeys, higher individual costs, underused vehicle capacity and added congestion near crowded venues."
    )
    doc.add_page_break()

    # --- SECTION 3 | PROPOSED SOLUTION ---
    add_h1("Section 3 | Proposed Solution")
    doc.add_paragraph(
        "Smart Share connects riders through ride requests. A user signs in, creates a request, and asks the system to "
        "find compatible requests from other users."
    )
    add_bullet("Create a ride request:", "Choose a pickup and destination using Mumbai landmark presets (BKC, Airport T2, Powai, Lower Parel, Dadar, Andheri).")
    add_bullet("Select a departure window:", "Specify earliest and latest acceptable departure times.")
    add_bullet("State journey constraints:", "Specify seats requested (1–6) and maximum acceptable extra travel time (+0m to +60m).")
    add_bullet("Find matches:", "The backend discovers candidates, filters them through spatial/temporal gates, and evaluates route sequences.")
    add_bullet("Review ranked suggestions:", "Inspect composite compatibility scores, detour breakdowns, stop sequences, and route accuracy notices.")
    add_bullet("Fare estimation & DEC-013 consent:", "Inspect pre-trip estimates and privacy-safe economic status; opt in to reveal exact proportional contributions.")
    doc.add_caption("Figure 1. End-to-end user journey in the Smart Share application.")
    doc.add_paragraph(
        "How candidates are found: The engine shortlists active, unexpired requests from other users within 2 km of the "
        "pickup, with overlapping departure windows and combined seats of at most four. It then rejects pairs travelling in "
        "clearly different directions (>90° divergence), evaluates valid pickup/drop-off orders using road-network durations, and discards "
        "any order where either rider's extra time exceeds their own stated limit. Survivors are scored and the top five are returned."
    )
    doc.add_paragraph(
        "Scope note: Automatic cab dispatch, driver assignment, and payment processing are explicitly out of MVP scope."
    )
    doc.add_page_break()

    # --- SECTION 4 | OBJECTIVES ---
    add_h1("Section 4 | Objectives")
    add_h2("Technical Objectives")
    add_bullet("Spatial discovery:", "Discover compatible passengers with location-aware spatial queries (PostGIS geography, GiST index).")
    add_bullet("Temporal compatibility:", "Apply time-aware matching through departure-window intersection.")
    add_bullet("Directional gating:", "Evaluate direction and destination compatibility, rejecting backtracking pairings.")
    add_bullet("Detour constraints:", "Evaluate valid pickup/drop-off orders and keep each rider's detour within their stated limit.")
    add_bullet("Statutory fare estimation:", "Provide deterministic, statutory pre-trip fare estimation using the approved Mumbai taxi tariff model.")
    add_bullet("Proportional cost allocation:", "Allocate shared costs proportionally to solo baselines, conserving exact paise down to ₹0.00.")
    add_bullet("Bilateral privacy consent:", "Enforce DEC-013 bilateral consent to protect passenger privacy and prevent unilateral financial inference.")
    add_bullet("Scalable architecture:", "Maintain modular services, replaceable routing adapters, Alembic migrations, and automated regression suites.")
    add_h2("User-Impact Objectives")
    add_bullet("Cost efficiency:", "Make it easy to find fellow travellers, reducing reliance on duplicate solo cab journeys.")
    add_bullet("Seat occupancy:", "Improve vehicle seat occupancy during high-demand congestion hours.")
    add_bullet("Detour protection:", "Minimise detour delays through strict passenger-configured detour ceilings.")
    add_bullet("Accessible mobile UX:", "Offer an accessible, mobile-first experience with intuitive landmark presets and clear status feedback.")
    add_bullet("Economic truthfulness:", "Help passengers clearly understand whether pooling saves money through honest, non-manipulated economic indicators.")
    doc.add_paragraph(
        "The user-impact objectives represent engineering design goals. Pilot conversion and savings targets remain subject to hosted user trials."
    )
    doc.add_page_break()

    # --- SECTION 5 | KEY FEATURES ---
    add_h1("Section 5 | Key Features")
    doc.add_paragraph(
        "Feature status is verified against repository code, test suites, and database migrations. "
        "Tested denotes automated test verification, plus live database checks where noted."
    )
    feat_tbl = doc.add_table(rows=1, cols=5)
    feat_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = feat_tbl.rows[0].cells
    hdr_titles = ["Feature", "Planned", "Implemented", "Tested", "Status"]
    for idx, t in enumerate(hdr_titles):
        hdr[idx].paragraphs[0].add_run(t).bold = True
        hdr[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(hdr[idx], "0B1F3A")
        set_cell_margins(hdr[idx], 80, 80, 100, 100)

    feat_rows = [
        ("Supabase Auth with backend JWT verification (ES256/JWKS)", "Yes", "Yes", "Auth test suite (18 tests)", "Implemented and tested"),
        ("User profiles (retrieve/update)", "Yes", "Yes", "API tests", "Implemented and tested"),
        ("Ride request create, list, view, edit, cancel; ownership checks", "Yes", "Yes", "API + model tests; UI tests", "Implemented and tested"),
        ("Landmark presets, departure window, seats, detour preference", "Yes", "Yes", "UI component tests", "Implemented and tested"),
        ("PostGIS candidate filtering (2 km radius, window overlap, LIMIT 20)", "Yes", "Yes", "Unit tests; live PostGIS run (rollback)", "Implemented and tested; browser E2E pending"),
        ("Direction and seat-capacity checks", "Yes", "Yes", "Unit tests", "Implemented and tested"),
        ("Pairwise stop-order evaluation & per-rider detour limits", "Yes", "Yes", "Unit tests", "Implemented and tested"),
        ("Weighted scoring, ranking (top 5), and match explanations", "Yes", "Yes", "Unit, API and UI tests", "Implemented; hosted 2-user E2E pending"),
        ("OSRM road-network durations and approximate fallback", "Yes", "Yes", "Adapter and fallback tests", "Implemented and tested (best-effort)"),
        ("Statutory Mumbai taxi fare estimation (Phase 5B)", "Yes", "Yes", "Tariff, pulse, night-window tests", "Implemented and tested"),
        ("Solo-proportional fare allocation & DEC-013 consent (Phase 5C)", "Yes", "Yes", "12 invariant tests; paise conservation", "Implemented (local verified; hosted pending)"),
        ("Match acceptance / decline, ride groups, proposal expiry", "Yes", "No", "-", "Planned (Phase 7)"),
        ("Cab booking, payments, live dispatch, vehicle tracking", "Future", "No", "-", "Out of MVP scope"),
    ]
    for r in feat_rows:
        row_cells = feat_tbl.add_row().cells
        for idx, val in enumerate(r):
            p_c = row_cells[idx].paragraphs[0]
            run_c = p_c.add_run(val)
            if idx == 4:
                run_c.bold = True
            p_c.runs[0].font.size = Pt(8.5)
            set_cell_margins(row_cells[idx], 60, 60, 80, 80)
    add_caption("Table 1. Feature-status matrix (reflecting verified Phase 5B/5C implementation).")

    add_h2("Scoring model (as implemented):")
    doc.add_paragraph(
        "Composite score = 30% pickup proximity + 30% destination similarity & direction + 20% departure-time compatibility + "
        "20% individual detour headroom. Seat capacity is a hard eligibility gate, not a scoring factor. "
        "Ties are broken by lower total detour, then smaller pickup separation."
    )
    doc.add_page_break()

    # --- SECTION 6 | TECHNOLOGY / TECH STACK ---
    add_h1("Section 6 | Technology / Tech Stack")
    add_h2("Core Technology Choices & Implementation Rationale")
    tech_tbl = doc.add_table(rows=1, cols=3)
    tech_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_hdr = tech_tbl.rows[0].cells
    for idx, title in enumerate(["Technology", "Purpose in Smart Share", "Why it fits"]):
        t_hdr[idx].paragraphs[0].add_run(title).bold = True
        t_hdr[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(t_hdr[idx], "0B1F3A")
        set_cell_margins(t_hdr[idx], 80, 80, 100, 100)

    tech_rows = [
        ("React, TypeScript, Vite", "Mobile-first UI, forms, and match results", "Fast dev builds, typed props, rich ecosystem"),
        ("Python, FastAPI", "REST API under /api/v1 and matching engine", "High async throughput, clean dependency injection"),
        ("Pydantic v2", "Request/response schema validation & DEC-013 redaction", "Guarantees private fields are omitted from wire payloads"),
        ("PostgreSQL + PostGIS", "Geography(Point, 4326) storage and spatial queries", "ST_DWithin with GiST index accelerates pickup filtering"),
        ("Supabase (hosted)", "Managed PostgreSQL, PostGIS, and user authentication", "Reliable hosted cloud DB without DevOps overhead"),
        ("Alembic", "Versioned database schema migrations (c5d013c0a501)", "Deterministic, additive, reviewable schema evolution"),
        ("Supabase Auth / JWKS", "User sign-in; backend verifies ES256 bearer tokens", "Cryptographically derived identity, zero passwords stored"),
        ("OSRM (+ Fallback)", "Road-network travel durations for detour calculations", "Zero-credential routing with graceful offline degradation"),
        ("Pytest, Ruff, Oxlint, tsc", "Automated unit/API tests, static linting, and type checking", "Prevents regressions and enforces strict code cleanliness"),
    ]
    for r in tech_rows:
        rc = tech_tbl.add_row().cells
        for idx, val in enumerate(r):
            rc[idx].paragraphs[0].add_run(val)
            if idx == 0:
                rc[idx].paragraphs[0].runs[0].bold = True
            rc[idx].paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(rc[idx], 60, 60, 80, 80)
    add_caption("Table 2. Technologies and architecture rationale.")
    doc.add_page_break()

    # --- SECTION 7 | SYSTEM ARCHITECTURE ---
    add_h1("Section 7 | System Architecture")
    doc.add_paragraph(
        "Primary Data Flow: User (Mobile Browser) → React Client → Supabase Auth (Sign-in / JWT) → FastAPI Backend (/api/v1) "
        "→ JWT Verification (JWKS ES256) → Matching Engine → PostGIS (Spatial Discovery) → OSRM Adapter (Road Network Detours) "
        "→ Fare Estimator (Phase 5B) → Proportional Allocation (Phase 5C) → DEC-013 Consent Filter → Scoped Proposal JSON → React UI."
    )
    doc.add_paragraph(
        "Backend Authoritativeness & Decoupled Routing: The frontend never determines match feasibility or "
        "cost allocation; the backend is authoritative. The routing adapter sits behind a provider interface, allowing "
        "OSRM, OpenRouteService, or the calibrated fallback to be swapped transparently without modifying matching heuristics. "
        "Match proposals are computed dynamically on demand; cancelling or expiring a request automatically excludes it from future queries."
    )
    doc.add_page_break()

    # --- SECTION 8 | IMPLEMENTATION ---
    add_h1("Section 8 | Implementation")
    doc.add_paragraph(
        "Smart Share was developed through disciplined, documented engineering phases. "
        "Phase 5 (Fare Estimation & Proportional Allocation) has been completed and locally verified."
    )
    add_h2("Milestone Execution Summaries:")
    add_bullet("Phase 0–3:", "Completed foundational architecture, PostgreSQL/PostGIS schemas, Alembic migrations, Supabase Auth ES256 verification, and authenticated CRUD ride request management.")
    add_bullet("Phase 4 (Matching Engine):", "Implemented spatial shortlisting, 90° direction gating, pairwise stop-order enumeration, detour scoring, and ranked match explanation payloads.")
    add_bullet("Phase 5B (Fare Estimation):", "Implemented statutory Mumbai taxi tariff (₹33 base fare for 1.5 km, ₹21.90/km), Asia/Kolkata night surcharge window (00:00–05:00 IST), and conservative route accuracy tiers (ROAD_ROUTE, MATRIX_SCREENING, CALIBRATED_FALLBACK).")
    add_bullet("Phase 5C (Fare Allocation & Privacy):", "Implemented solo-proportional allocation (DEC-008), deterministic Half-Up integer-paise conservation, economic classification (POSITIVE, BREAK_EVEN, NEGATIVE, CONDITIONAL), and DEC-013 bilateral affirmative consent persistence in match_disclosure_consent_events.")

    add_h2("Key Technical Challenges & Resolutions:")
    chal_tbl = doc.add_table(rows=1, cols=2)
    chal_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_hdr = chal_tbl.rows[0].cells
    c_hdr[0].paragraphs[0].add_run("Challenge").bold = True
    c_hdr[1].paragraphs[0].add_run("Resolution").bold = True
    c_hdr[0].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    c_hdr[1].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    set_cell_background(c_hdr[0], "0B1F3A")
    set_cell_background(c_hdr[1], "0B1F3A")

    chal_rows = [
        ("Straight-line distance misleads in Mumbai (water bodies, opposite headings from Dadar/CSMT)", "Direction gate (hard reject >90°) and OSRM road-network travel durations for detours."),
        ("Precedence permutations where riders never share cab", "Engine enumerates 6 orders and discards the 2 non-sharing sequences (P1-D1-P2-D2, P2-D2-P1-D1)."),
        ("Public routing service rate limits and downtime", "1.05s request spacing, bounded candidate batching, and calibrated geodesic fallback."),
        ("PostGIS returned raw hex EWKB for geography columns", "Queries select ST_AsText; parser also decodes raw WKB/EWKB as fallback."),
        ("Unilateral financial inference risk (DEC-013)", "Bilateral affirmative consent required before exact contribution disclosure; solo baselines remain redacted."),
    ]
    for r in chal_rows:
        rc = chal_tbl.add_row().cells
        rc[0].paragraphs[0].add_run(r[0]).bold = True
        rc[1].paragraphs[0].add_run(r[1])
        rc[0].paragraphs[0].runs[0].font.size = Pt(8.5)
        rc[1].paragraphs[0].runs[0].font.size = Pt(8.5)
        set_cell_margins(rc[0], 60, 60, 80, 80)
        set_cell_margins(rc[1], 60, 60, 80, 80)
    add_caption("Table 3. Key engineering challenges and technical resolutions.")
    doc.add_page_break()

    # --- SECTION 9 | RESULTS / SCREENSHOTS ---
    add_h1("Section 9 | Results / Screenshots & Test Evidence")
    doc.add_paragraph(
        "This section presents visual verification evidence from the running Smart Share application. "
        "Screenshots captured from the running application are distinguished from pending hosted items. "
        "In accordance with academic verification standards, screenshot placeholders remain for unsupplied views."
    )

    # Insert images
    img_auth = "report_images/fig_auth.png"
    img_prof = "report_images/fig_profile.jpg"
    img_create = "report_images/fig_create.jpg"
    img_edit = "report_images/fig_edit.jpg"
    img_list = "report_images/fig_list.jpg"

    if os.path.exists(img_auth):
        doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].add_run().add_picture(img_auth, width=Inches(3.2))
        add_caption("Figure 9. User authentication interface showing Supabase Auth integration and backend health status.")

    if os.path.exists(img_prof):
        doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].add_run().add_picture(img_prof, width=Inches(3.5))
        add_caption("Figure 13. Authenticated user profile and onboarding setup interface with development UUID.")

    doc.add_page_break()

    if os.path.exists(img_create):
        doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].add_run().add_picture(img_create, width=Inches(3.2))
        add_caption("Figure 10. Ride request creation interface with landmark presets, departure window, and detour slider.")

    if os.path.exists(img_edit):
        doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].add_run().add_picture(img_edit, width=Inches(3.2))
        add_caption("Figure 12. Ride request details and edit interface for modifying active departure constraints.")

    doc.add_page_break()

    if os.path.exists(img_list):
        doc.add_paragraph().alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.paragraphs[-1].add_run().add_picture(img_list, width=Inches(3.2))
        add_caption("Figure 11. Active ride request listing with status badges and on-demand 'Find matches' action.")

    p_ph = doc.add_paragraph()
    p_ph.paragraph_format.space_before = Pt(15)
    r_ph = p_ph.add_run(
        "[ SCREENSHOT PENDING — HOSTED ACCEPTANCE RUN ]\n"
        "Figure 14 & 15. Match discovery proposals & DEC-013 bilateral fare disclosure.\n"
        "To be captured during the upcoming live hosted two-user acceptance test between Passenger A "
        "and Passenger B on the deployed Supabase / Render / Vercel infrastructure."
    )
    r_ph.italic = True
    r_ph.font.color.rgb = COLOR_SLATE
    p_ph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption("Figure 14. Ranked match proposals with statutory fare estimates and DEC-013 consent (Pending).")

    doc.add_paragraph(
        "Note on Unsupplied Screenshots: Genuine application captures have been inserted for Authentication (Fig. 9), "
        "Request Creation (Fig. 10), Request Listing (Fig. 11), Request Edit (Fig. 12), and User Profile (Fig. 13). "
        "Screenshots for the unauthenticated landing homepage (Placeholder 1) and live two-user consented match results (Fig. 14) "
        "are pending live hosted acceptance verification and are truthfully designated as pending."
    )

    add_h2("Documented Testing Results & Acceptance")
    test_tbl = doc.add_table(rows=1, cols=3)
    test_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    th = test_tbl.rows[0].cells
    for idx, t in enumerate(["Evidence Layer", "Verified Result", "Verification Source"]):
        th[idx].paragraphs[0].add_run(t).bold = True
        th[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(th[idx], "0B1F3A")

    test_rows = [
        ("Full Backend Pytest Suite", "175 passed, 1 skipped (hosted PostGIS sandbox restriction) in 12.70s", "Clean baseline 536c92a (app/tests)"),
        ("Fare & Matching Tests", "51 passed in 0.66s (covering 12 mathematical invariants, tariff & allocation)", "test_fares.py & test_matching_algorithms.py"),
        ("Live PostGIS Query Test", "1 passed in 0.49s against Supabase PostgreSQL inside rolled-back transaction", "test_matching_postgis.py"),
        ("Frontend Vitest Suite", "32 passed across 7 test files in 3.48s", "frontend/src/features/ride-requests"),
        ("Static Quality & Linters", "Ruff (0 errors, 74 files clean), Oxlint (0 errors), tsc --noEmit (0 errors)", "CI quality check suite"),
        ("Production Client Build", "Vite production bundle built successfully in 0.39s (125 kB gzip)", "npm run build"),
        ("Database Migration", "Migration c5d013c0a501 verified on Supabase development DB (ifdmbwjaysspvysoxfpl)", "Alembic current revision"),
    ]
    for r in test_rows:
        rc = test_tbl.add_row().cells
        rc[0].paragraphs[0].add_run(r[0]).bold = True
        rc[1].paragraphs[0].add_run(r[1])
        rc[2].paragraphs[0].add_run(r[2])
        for c in rc:
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, 60, 60, 80, 80)
    add_caption("Table 4. Comprehensive test execution evidence across backend, frontend, and database.")

    doc.add_paragraph(
        "Verification status, stated transparently: Phase 5C Verdict: CONDITIONAL PASS. "
        "All mathematical allocation algorithms, non-negative bounds, proportional solo weights, deterministic integer-paise conservation "
        "(Contribution A + Contribution B = Gross Fare), and DEC-013 server-side redaction filters have passed automated unit and component testing. "
        "However, a live two-user acceptance test between two separate authenticated commuters on deployed infrastructure "
        "(Render/Vercel/Supabase) has not yet been executed. Therefore, complete hosted acceptance remains conditional."
    )
    doc.add_page_break()

    # --- SECTION 10 & 11 ---
    add_h1("Section 10 | Innovation")
    doc.add_paragraph(
        "Smart Share's contribution is not simply splitting a cab fare. It is deciding which strangers can practically "
        "share a journey, and showing why. It combines several checks that simple proximity matching lacks:"
    )
    add_bullet("Location-aware spatial discovery:", "PostGIS geography indexing with 2 km radius shortlisting.")
    add_bullet("Time compatibility:", "Closed-interval overlap of departure windows prevents impossible meetups.")
    add_bullet("Direction gating:", "Rigid bearing checks ensure riders heading in opposite directions are never paired.")
    add_bullet("Detour-aware sequence optimization:", "Evaluates 4 shared stop orders against individual detour tolerances.")
    add_bullet("Statutory Mumbai taxi tariff:", "Accurate pre-trip estimation using official government rate models.")
    add_bullet("Solo-proportional fair allocation:", "Weighting cost contributions by individual solo baselines with zero-paise residual drift.")
    add_bullet("DEC-013 Bilateral Consent Privacy:", "Cryptographic snapshot binding prevents unilateral economic profiling.")

    add_h1("Section 11 | Impact")
    doc.add_paragraph("EXPECTED impact only. No user adoption, savings or emissions figures have been measured.")
    add_bullet("Economic:", "Potential lower travel outlays; improved cost efficiency per passenger.")
    add_bullet("Environmental:", "Fewer duplicate trips, reduced fuel consumption and vehicle tailpipe emissions.")
    add_bullet("Social:", "Easier coordination among commuters leaving crowded venues.")
    add_bullet("Operational:", "Higher vehicle occupancy and reduced bottleneck congestion at hubs.")
    doc.add_page_break()

    # --- SECTION 12 & 13 ---
    add_h1("Section 12 | Future Scope")
    scope_tbl = doc.add_table(rows=1, cols=3)
    scope_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    sh = scope_tbl.rows[0].cells
    for idx, t in enumerate(["Priority", "Milestone Description", "Roadmap Link"]):
        sh[idx].paragraphs[0].add_run(t).bold = True
        sh[idx].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(sh[idx], "0B1F3A")

    scope_rows = [
        ("Near term", "Reconcile Git merge conflicts and complete authenticated hosted two-user acceptance testing.", "Phase 5C Acceptance"),
        ("Next", "Match acceptance / decline, ride group confirmation, proposal expiry, and safe seat allocation.", "Phase 7"),
        ("Next", "Interactive Leaflet map route visualization and web push status notifications.", "Phases 6–7"),
        ("Later", "Multi-passenger matching optimization (pooling groups of 3 or 4 riders).", "Matching Extension"),
        ("Later", "Production deployment, traffic-aware routing adapter, and realistic load testing.", "Phases 8–9"),
        ("Out of MVP", "Commercial cab-provider API integration, payment gateway processing, and real-time taxi dispatch.", "Future Commercial"),
    ]
    for r in scope_rows:
        rc = scope_tbl.add_row().cells
        rc[0].paragraphs[0].add_run(r[0]).bold = True
        rc[1].paragraphs[0].add_run(r[1])
        rc[2].paragraphs[0].add_run(r[2])
        for c in rc:
            c.paragraphs[0].runs[0].font.size = Pt(8.5)
            set_cell_margins(c, 60, 60, 80, 80)
    add_caption("Table 5. Future development scope and roadmap priorities.")

    add_h1("Section 13 | References")
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
        add_bullet("", r)

    doc.save(filename)
    print(f"DOCX built successfully: {filename}")

if __name__ == "__main__":
    build_docx()
EOF
./backend/.venv/bin/python build_docx.py