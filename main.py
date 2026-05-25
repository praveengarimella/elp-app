import io
import json
import os
import re
import secrets
from datetime import datetime


def natural_key(project):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', project.elp_project_id)]


def cell_to_html(value) -> str:
    """Convert an openpyxl cell value to HTML, preserving bold, italic, and colour."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    # CellRichText (openpyxl rich_text=True)
    try:
        parts = []
        for run in value:
            if isinstance(run, str):
                parts.append(run)
                continue
            text = run.text or ""
            font = getattr(run, "font", None)
            if font:
                color = getattr(font, "color", None)
                if color and getattr(color, "type", None) == "rgb":
                    rgb = color.rgb or ""
                    # rgb is 8-char ARGB; skip pure black and transparent
                    if len(rgb) == 8 and rgb.upper() not in ("FF000000", "00000000"):
                        text = f'<span style="color:#{rgb[2:]}">{text}</span>'
                if getattr(font, "italic", False):
                    text = f"<em>{text}</em>"
                if getattr(font, "bold", False):
                    text = f"<strong>{text}</strong>"
            parts.append(text)
        return "".join(parts)
    except Exception:
        return str(value)

import openpyxl
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Group, Preference, Project

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "elpadmin2027")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    valid = secrets.compare_digest(credentials.username, ADMIN_USERNAME) and \
            secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not valid:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})


# ---------------------------------------------------------------------------
# Student routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def browse_projects(request: Request, db: Session = Depends(get_db)):
    projects = sorted(db.query(Project).all(), key=natural_key)
    industries = sorted({p.industry_sector for p in projects if p.industry_sector})
    problem_types = sorted({p.problem_type for p in projects if p.problem_type})
    projects_json = json.dumps({
        p.elp_project_id: {
            "title": p.title,
            "problem_type": p.problem_type,
            "industry_sector": p.industry_sector,
            "problem_description": p.problem_description,
            "expected_outcomes": p.expected_outcomes,
        }
        for p in projects
    })
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects,
        "industries": industries,
        "problem_types": problem_types,
        "projects_json": projects_json,
    })


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_group(
    request: Request,
    db: Session = Depends(get_db),
    group_id_suffix: str = Form(...),
    s1_name: str = Form(...), s1_roll: str = Form(...),
    s2_name: str = Form(...), s2_roll: str = Form(...),
    s3_name: str = Form(...), s3_roll: str = Form(...),
    s4_name: str = Form(...), s4_roll: str = Form(...),
    s5_name: str = Form(...), s5_roll: str = Form(...),
):
    group_id = "ELP" + group_id_suffix.strip().upper()
    rolls = [r.strip() for r in [s1_roll, s2_roll, s3_roll, s4_roll, s5_roll]]

    def render_register(error=None, already_exists=False, existing_group_id=None):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": error,
            "already_exists": already_exists,
            "existing_group_id": existing_group_id,
        }, status_code=400)

    # Same group ID already registered
    existing = db.query(Group).filter(Group.group_id == group_id).first()
    if existing:
        if existing.is_submitted:
            # Already submitted — tell them clearly and give a link
            return render_register(
                error=f"Group {group_id} has already submitted preferences. "
                      f"You can view your submission at the link below."
            , already_exists=True, existing_group_id=group_id)
        else:
            # Registered but not submitted — send them to continue
            return RedirectResponse(url=f"/submit/{group_id}", status_code=303)

    # Check if any roll number already appears in a submitted group
    submitted_groups = db.query(Group).filter(Group.is_submitted == True).all()
    for g in submitted_groups:
        existing_rolls = {g.student_1_roll, g.student_2_roll, g.student_3_roll,
                          g.student_4_roll, g.student_5_roll}
        overlap = set(rolls) & existing_rolls
        if overlap:
            roll_list = ", ".join(overlap)
            return render_register(
                error=f"Roll number(s) {roll_list} have already submitted preferences "
                      f"as part of group {g.group_id}. Each student can only be in one group."
            )

    group = Group(
        group_id=group_id,
        student_1_name=s1_name.strip(), student_1_roll=rolls[0],
        student_2_name=s2_name.strip(), student_2_roll=rolls[1],
        student_3_name=s3_name.strip(), student_3_roll=rolls[2],
        student_4_name=s4_name.strip(), student_4_roll=rolls[3],
        student_5_name=s5_name.strip(), student_5_roll=rolls[4],
        is_submitted=False,
    )
    db.add(group)
    db.commit()
    return RedirectResponse(url=f"/submit/{group_id}", status_code=303)


@app.get("/submit/{group_id}", response_class=HTMLResponse)
def submit_page(group_id: str, request: Request, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        return templates.TemplateResponse("not_found.html", {"request": request}, status_code=404)

    if group.is_submitted:
        prefs = sorted(group.preferences, key=lambda x: x.rank)
        return templates.TemplateResponse("submitted.html", {
            "request": request,
            "group": group,
            "prefs": prefs,
        })

    projects = sorted(db.query(Project).all(), key=natural_key)
    industries = sorted({p.industry_sector for p in projects if p.industry_sector})
    problem_types = sorted({p.problem_type for p in projects if p.problem_type})
    projects_json = json.dumps({
        p.elp_project_id: {
            "title": p.title,
            "problem_type": p.problem_type,
            "industry_sector": p.industry_sector,
            "problem_description": p.problem_description,
            "expected_outcomes": p.expected_outcomes,
        }
        for p in projects
    })

    return templates.TemplateResponse("submit.html", {
        "request": request,
        "group": group,
        "projects": projects,
        "industries": industries,
        "problem_types": problem_types,
        "projects_json": projects_json,
    })


@app.post("/submit/{group_id}")
async def submit_preferences(
    group_id: str,
    request: Request,
    db: Session = Depends(get_db),
    pref_1: str = Form(...), pref_2: str = Form(...),
    pref_3: str = Form(...), pref_4: str = Form(...),
    pref_5: str = Form(...), pref_6: str = Form(...),
    pref_7: str = Form(...), pref_8: str = Form(...),
    pref_9: str = Form(...), pref_10: str = Form(...),
):
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        return templates.TemplateResponse("not_found.html", {"request": request}, status_code=404)
    if group.is_submitted:
        return RedirectResponse(url=f"/submit/{group_id}", status_code=303)

    prefs = [pref_1, pref_2, pref_3, pref_4, pref_5,
             pref_6, pref_7, pref_8, pref_9, pref_10]

    if len(set(prefs)) != 10:
        projects = db.query(Project).order_by(Project.elp_project_id).all()
        return templates.TemplateResponse("submit.html", {
            "request": request,
            "group": group,
            "projects": projects,
            "industries": sorted({p.industry_sector for p in projects}),
            "problem_types": sorted({p.problem_type for p in projects}),
            "projects_json": json.dumps({p.elp_project_id: {"title": p.title, "problem_type": p.problem_type, "industry_sector": p.industry_sector, "problem_description": p.problem_description, "expected_outcomes": p.expected_outcomes} for p in projects}),
            "error": "Duplicate projects detected. Please ensure all 10 preferences are different.",
        }, status_code=400)

    for rank, pid in enumerate(prefs, start=1):
        db.add(Preference(group_id=group_id, elp_project_id=pid, rank=rank))

    group.is_submitted = True
    group.submitted_at = datetime.utcnow()
    db.commit()
    return RedirectResponse(url=f"/submit/{group_id}", status_code=303)


@app.get("/submit/{group_id}/download")
def download_preferences(group_id: str, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group or not group.is_submitted:
        raise HTTPException(status_code=404)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "My Preferences"

    # Group info header rows
    ws.append(["Group ID", group.group_id])
    ws.append(["Submitted At", group.submitted_at.strftime("%d %b %Y, %H:%M")])
    ws.append([])
    ws.append(["#", "Student Name", "Roll Number"])
    for i, (name, roll) in enumerate([
        (group.student_1_name, group.student_1_roll),
        (group.student_2_name, group.student_2_roll),
        (group.student_3_name, group.student_3_roll),
        (group.student_4_name, group.student_4_roll),
        (group.student_5_name, group.student_5_roll),
    ], start=1):
        ws.append([i, name, roll])

    ws.append([])
    ws.append(["Rank", "Project ID", "Title", "Problem Type", "Industry Sector"])
    for pref in sorted(group.preferences, key=lambda x: x.rank):
        ws.append([
            pref.rank,
            pref.elp_project_id,
            pref.project.title,
            pref.project.problem_type,
            pref.project.industry_sector,
        ])

    # Column widths
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"ELP_preferences_{group_id}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "project_count": db.query(Project).count(),
        "group_count": db.query(Group).count(),
        "submitted_count": db.query(Group).filter(Group.is_submitted == True).count(),
        "recent_groups": db.query(Group).order_by(Group.submitted_at.desc()).limit(10).all(),
    })


@app.post("/admin/upload", response_class=HTMLResponse)
async def upload_projects(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    def dashboard(error=None, success=None):
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "project_count": db.query(Project).count(),
            "group_count": db.query(Group).count(),
            "submitted_count": db.query(Group).filter(Group.is_submitted == True).count(),
            "recent_groups": db.query(Group).order_by(Group.submitted_at.desc()).limit(10).all(),
            "error": error,
            "success": success,
        })

    contents = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contents), rich_text=True)
    except Exception:
        return dashboard(error="Could not read the file. Please upload a valid .xlsx file.")

    ws = wb.active
    raw_headers = [str(c.value).strip() if c.value else "" for c in ws[1]]
    headers = [h.lower().replace(" ", "_") for h in raw_headers]

    col = {}
    for i, h in enumerate(headers):
        if "project_id" in h or (h.startswith("elp") and "id" in h):
            col["elp_project_id"] = i
        elif h == "title" or "project_title" in h:
            col["title"] = i
        elif "industry" in h:
            col["industry_sector"] = i
        elif "problem_type" in h or h == "type":
            col["problem_type"] = i
        elif "description" in h:
            col["problem_description"] = i
        elif "outcome" in h:
            col["expected_outcomes"] = i

    missing = [k for k in ("elp_project_id", "title", "industry_sector", "problem_type",
                            "problem_description", "expected_outcomes") if k not in col]
    if missing:
        readable = [m.replace("_", " ").title() for m in missing]
        return dashboard(error=f"Could not find these columns: {', '.join(readable)}. "
                               f"Found: {', '.join(raw_headers)}")

    uploaded = updated = 0
    for row in ws.iter_rows(min_row=2, values_only=False):
        pid = str(row[col["elp_project_id"]].value or "").strip()
        if not pid:
            continue
        data = dict(
            title=cell_to_html(row[col["title"]].value).strip(),
            industry_sector=str(row[col["industry_sector"]].value or "").strip(),
            problem_type=str(row[col["problem_type"]].value or "").strip(),
            problem_description=cell_to_html(row[col["problem_description"]].value),
            expected_outcomes=cell_to_html(row[col["expected_outcomes"]].value),
        )
        existing = db.query(Project).filter(Project.elp_project_id == pid).first()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(Project(elp_project_id=pid, **data))
            uploaded += 1

    db.commit()
    return dashboard(success=f"Done — {uploaded} new projects added, {updated} updated.")


@app.get("/admin/export")
def export_preferences(db: Session = Depends(get_db), _=Depends(require_admin)):
    wb = openpyxl.Workbook()

    # Sheet 1 — full detail
    ws1 = wb.active
    ws1.title = "Preferences"
    ws1.append([
        "Group ID",
        "S1 Name", "S1 Roll", "S2 Name", "S2 Roll",
        "S3 Name", "S3 Roll", "S4 Name", "S4 Roll",
        "S5 Name", "S5 Roll",
        "Pref 1", "Pref 2", "Pref 3", "Pref 4", "Pref 5",
        "Pref 6", "Pref 7", "Pref 8", "Pref 9", "Pref 10",
        "Submitted At",
    ])

    groups = db.query(Group).filter(Group.is_submitted == True).order_by(Group.submitted_at).all()
    for group in groups:
        pref_ids = [p.elp_project_id for p in sorted(group.preferences, key=lambda x: x.rank)]
        while len(pref_ids) < 10:
            pref_ids.append("")
        ws1.append([
            group.group_id,
            group.student_1_name, group.student_1_roll,
            group.student_2_name, group.student_2_roll,
            group.student_3_name, group.student_3_roll,
            group.student_4_name, group.student_4_roll,
            group.student_5_name, group.student_5_roll,
            *pref_ids,
            group.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])

    # Sheet 2 — group / project pairs for matching algorithm
    ws2 = wb.create_sheet(title="Group-Project Pairs")
    ws2.append(["Group ID", "Preferred Project ID"])
    for group in groups:
        for pref in sorted(group.preferences, key=lambda x: x.rank):
            ws2.append([group.group_id, pref.elp_project_id])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=elp_preferences.xlsx"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
