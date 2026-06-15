import json
from datetime import date
from mcp.server.fastmcp import FastMCP
from database import init_db, SessionLocal, Course, Faculty, Batch, Student, Enrollment

# Initialise DB tables on startup
init_db()

# ── MCP Server ────────────────────────────────────────────────────────────────
mcp = FastMCP("Deccansoft Institute MCP") #, port=8000)


# ═════════════════════════════════════════════════════════════════════════════
# TOOLS  — actions that DO something (create, enroll, search)
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def add_student(name: str, email: str, phone: str) -> str:
    """Register a new student in the institute."""
    db = SessionLocal()
    try:
        student = Student(name=name, email=email, phone=phone,
                          enrolled_date=str(date.today()))
        db.add(student)
        db.commit()
        db.refresh(student)
        return f"Student '{name}' registered successfully with ID {student.id}."
    except Exception as e:
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


@mcp.tool()
def enroll_student(student_id: int, batch_id: int) -> str:
    """Enroll an existing student into a batch."""
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == student_id).first()
        batch   = db.query(Batch).filter(Batch.id == batch_id).first()

        if not student:
            return f"Student ID {student_id} not found."
        if not batch:
            return f"Batch ID {batch_id} not found."

        already = db.query(Enrollment).filter(
            Enrollment.student_id == student_id,
            Enrollment.batch_id   == batch_id
        ).first()
        if already:
            return f"{student.name} is already enrolled in this batch."

        db.add(Enrollment(student_id=student_id, batch_id=batch_id,
                          enrollment_date=str(date.today()), status="active"))
        db.commit()
        return f"{student.name} enrolled in Batch {batch_id} ({batch.course.title}) successfully."
    except Exception as e:
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


@mcp.tool()
def add_batch(course_id: int, faculty_id: int,
              start_date: str, end_date: str,
              schedule: str, max_students: int = 20) -> str:
    """Create a new batch for a course assigned to a faculty member."""
    db = SessionLocal()
    try:
        course  = db.query(Course).filter(Course.id == course_id).first()
        faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()

        if not course:
            return f"Course ID {course_id} not found."
        if not faculty:
            return f"Faculty ID {faculty_id} not found."

        batch = Batch(course_id=course_id, faculty_id=faculty_id,
                      start_date=start_date, end_date=end_date,
                      schedule=schedule, max_students=max_students)
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return (f"New batch for '{course.title}' created with ID {batch.id}, "
                f"taught by {faculty.name}, starting {start_date}.")
    except Exception as e:
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()


@mcp.tool()
def get_students_by_course(course_name: str) -> str:
    """Get all students enrolled in any batch of a given course (match by course name)."""
    db = SessionLocal()
    try:
        courses = db.query(Course).filter(Course.title.ilike(f"%{course_name}%")).all()
        if not courses:
            return f"No course found matching '{course_name}'."

        result = []
        for course in courses:
            for batch in course.batches:
                for e in batch.enrollments:
                    result.append({
                        "student_id":   e.student.id,
                        "student_name": e.student.name,
                        "email":        e.student.email,
                        "batch_id":     batch.id,
                        "schedule":     batch.schedule,
                        "status":       e.status,
                    })

        if not result:
            return f"No students enrolled in any batch of '{course_name}'."

        return json.dumps({"course": courses[0].title, "students": result}, indent=2)
    finally:
        db.close()


@mcp.tool()
def search_students(query: str) -> str:
    """Search students by name or email (partial match)."""
    db = SessionLocal()
    try:
        results = db.query(Student).filter(
            (Student.name.ilike(f"%{query}%")) |
            (Student.email.ilike(f"%{query}%"))
        ).all()
        if not results:
            return f"No students found matching '{query}'."
        return json.dumps(
            [{"id": s.id, "name": s.name, "email": s.email, "phone": s.phone}
             for s in results],
            indent=2
        )
    finally:
        db.close()


@mcp.tool()
def get_batch_students(batch_id: int) -> str:
    """List all students enrolled in a specific batch."""
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return f"Batch ID {batch_id} not found."
        return json.dumps({
            "batch_id": batch.id,
            "course":   batch.course.title,
            "faculty":  batch.faculty.name,
            "schedule": batch.schedule,
            "students": [
                {"id": e.student.id, "name": e.student.name,
                 "email": e.student.email, "status": e.status}
                for e in batch.enrollments
            ]
        }, indent=2)
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# RESOURCES  — static/addressable data (no parameters in URI)
# ═════════════════════════════════════════════════════════════════════════════

@mcp.resource("institute://courses")
def list_courses() -> str:
    """All courses offered by the institute."""
    db = SessionLocal()
    try:
        return json.dumps(
            [{"id": c.id, "title": c.title, "description": c.description,
              "duration_weeks": c.duration_weeks, "fees": c.fees}
             for c in db.query(Course).all()],
            indent=2
        )
    finally:
        db.close()


@mcp.resource("institute://faculty")
def list_faculty() -> str:
    """All faculty members at the institute."""
    db = SessionLocal()
    try:
        return json.dumps(
            [{"id": f.id, "name": f.name, "email": f.email, "expertise": f.expertise}
             for f in db.query(Faculty).all()],
            indent=2
        )
    finally:
        db.close()


@mcp.resource("institute://students")
def list_students() -> str:
    """All registered students."""
    db = SessionLocal()
    try:
        return json.dumps(
            [{"id": s.id, "name": s.name, "email": s.email,
              "phone": s.phone, "enrolled_date": s.enrolled_date}
             for s in db.query(Student).all()],
            indent=2
        )
    finally:
        db.close()


@mcp.resource("institute://batches/active")
def list_active_batches() -> str:
    """All active batches across all courses."""
    db = SessionLocal()
    try:
        return json.dumps(
            [{"id": b.id, "course": b.course.title, "faculty": b.faculty.name,
              "start_date": b.start_date, "end_date": b.end_date,
              "schedule": b.schedule, "max_students": b.max_students,
              "enrolled": len(b.enrollments)}
             for b in db.query(Batch).all()],
            indent=2
        )
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# RESOURCE TEMPLATES  — parameterised URIs  institute://entity/{id}
# ═════════════════════════════════════════════════════════════════════════════

@mcp.resource("institute://courses/{course_id}")
def get_course(course_id: str) -> str:
    """Details of a specific course including all its batches."""
    db = SessionLocal()
    try:
        course = db.query(Course).filter(Course.id == int(course_id)).first()
        if not course:
            return json.dumps({"error": f"Course {course_id} not found"})
        return json.dumps({
            "id": course.id, "title": course.title,
            "description": course.description,
            "duration_weeks": course.duration_weeks, "fees": course.fees,
            "batches": [
                {"batch_id": b.id, "faculty": b.faculty.name,
                 "start_date": b.start_date, "end_date": b.end_date,
                 "schedule": b.schedule, "max_students": b.max_students,
                 "enrolled": len(b.enrollments)}
                for b in course.batches
            ]
        }, indent=2)
    finally:
        db.close()


@mcp.resource("institute://students/{student_id}")
def get_student(student_id: str) -> str:
    """Profile and enrollment history of a specific student."""
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == int(student_id)).first()
        if not student:
            return json.dumps({"error": f"Student {student_id} not found"})
        return json.dumps({
            "id": student.id, "name": student.name,
            "email": student.email, "phone": student.phone,
            "enrolled_date": student.enrolled_date,
            "enrollments": [
                {"batch_id": e.batch_id, "course": e.batch.course.title,
                 "faculty": e.batch.faculty.name,
                 "schedule": e.batch.schedule, "status": e.status}
                for e in student.enrollments
            ]
        }, indent=2)
    finally:
        db.close()


@mcp.resource("institute://faculty/{faculty_id}")
def get_faculty_detail(faculty_id: str) -> str:
    """Profile and batch assignments of a specific faculty member."""
    db = SessionLocal()
    try:
        faculty = db.query(Faculty).filter(Faculty.id == int(faculty_id)).first()
        if not faculty:
            return json.dumps({"error": f"Faculty {faculty_id} not found"})
        return json.dumps({
            "id": faculty.id, "name": faculty.name,
            "email": faculty.email, "expertise": faculty.expertise,
            "batches": [
                {"batch_id": b.id, "course": b.course.title,
                 "start_date": b.start_date, "end_date": b.end_date,
                 "schedule": b.schedule, "students_enrolled": len(b.enrollments)}
                for b in faculty.batches
            ]
        }, indent=2)
    finally:
        db.close()


@mcp.resource("institute://batches/{batch_id}")
def get_batch_detail(batch_id: str) -> str:
    """Full details of a specific batch including its student roster."""
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == int(batch_id)).first()
        if not batch:
            return json.dumps({"error": f"Batch {batch_id} not found"})
        return json.dumps({
            "batch_id": batch.id,
            "course":   batch.course.title,
            "faculty":  batch.faculty.name,
            "start_date": batch.start_date, "end_date": batch.end_date,
            "schedule": batch.schedule, "max_students": batch.max_students,
            "enrolled_count": len(batch.enrollments),
            "students": [
                {"id": e.student.id, "name": e.student.name,
                 "email": e.student.email, "status": e.status}
                for e in batch.enrollments
            ]
        }, indent=2)
    finally:
        db.close()


# ═════════════════════════════════════════════════════════════════════════════
# PROMPTS  — reusable instruction templates with dynamic arguments
# ═════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def student_progress_report(student_name: str, course_title: str,
                             batch_schedule: str, progress_notes: str) -> str:
    """Generate a formal student progress report."""
    return f"""
You are an academic coordinator at Deccansoft Software Training Institute.
Write a formal progress report for the following student:

Student Name : {student_name}
Course       : {course_title}
Schedule     : {batch_schedule}
Progress     : {progress_notes}

The report must include:
1. Brief introduction of the student and the course
2. Current progress summary based on the notes provided
3. Strengths observed
4. Areas that need improvement
5. Recommendations for the student going forward

Tone: Professional and encouraging. Length: 300-400 words.
"""


@mcp.prompt()
def batch_announcement(course_title: str, start_date: str,
                        faculty_name: str, schedule: str, fees: str) -> str:
    """Generate a new batch announcement for WhatsApp / Email broadcast."""
    return f"""
You are a marketing coordinator at Deccansoft Software Training Institute.
Write a compelling batch announcement using the details below:

Course     : {course_title}
Start Date : {start_date}
Faculty    : {faculty_name}
Schedule   : {schedule}
Fees       : {fees}

The announcement must include:
1. An engaging opening line
2. Key highlights of the course
3. Batch details — start date, schedule, faculty name
4. A strong call-to-action encouraging enrollment
5. A placeholder for contact details: [Contact: phone / email]

Tone: Enthusiastic yet professional.
Format: Suitable for WhatsApp and Email broadcast.
"""


@mcp.prompt()
def course_recommendation(background: str, interest_area: str,
                           available_days: str) -> str:
    """Recommend the best-fit course for a prospective student."""
    return f"""
You are a career counselor at Deccansoft Software Training Institute.
A prospective student has shared the following details:

Background     : {background}
Interest Area  : {interest_area}
Available Days : {available_days}

Based on these details, recommend the most suitable course(s) from the options below:

  - Python Full Stack      (16 weeks | ₹25,000)
  - Data Science w/ Python (12 weeks | ₹20,000)
  - Java Full Stack        (16 weeks | ₹25,000)
  - DevOps & Cloud         (10 weeks | ₹18,000)

Your response must include:
1. Top recommended course with clear justification
2. Alternative course if applicable
3. Expected career outcomes after completing the course
4. Suggested batch schedule based on available days

Tone: Friendly, honest, and advisory.
"""


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# stdio (default) : python main.py           → used by stdio_client.py & MCP Inspector
# HTTP            : python main.py http      → used by http_client.py
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
<<<<<<< HEAD:MCPClientWithLLM/main.py
    mcp.run(transport="stdio")

    # if len(sys.argv) > 1 and sys.argv[1] == "http":
    #     print("Starting MCP server on http://127.0.0.1:8000/mcp ...")
    # else:
    #     mcp.run(transport="stdio")
=======
    if len(sys.argv) > 1 and sys.argv[1] == "http":
        print("Starting MCP server on http://127.0.0.1:8000/mcp ...")
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    else:
        mcp.run(transport="stdio")
>>>>>>> a9b508fc8c9b6829a46cddcc8fc5e8a64eabe965:5.1-institute-mcp/main.py
