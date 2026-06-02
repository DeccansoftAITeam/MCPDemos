from database import init_db, SessionLocal, Course, Faculty, Batch, Student, Enrollment


def seed():
    init_db()
    db = SessionLocal()

    # ── Courses ──────────────────────────────────────────────────────────────
    courses = [
        Course(title="Python Full Stack",        description="Web development with Django & React",    duration_weeks=16, fees=25000),
        Course(title="Data Science with Python",  description="ML, Data Analysis, Visualisation",      duration_weeks=12, fees=20000),
        Course(title="Java Full Stack",           description="Java, Spring Boot, Angular",             duration_weeks=16, fees=25000),
        Course(title="DevOps & Cloud",            description="Docker, Kubernetes, AWS, CI/CD",         duration_weeks=10, fees=18000),
    ]
    db.add_all(courses)
    db.flush()

    # ── Faculty ───────────────────────────────────────────────────────────────
    faculty_list = [
        Faculty(name="Rajesh Kumar", email="rajesh@deccansoft.net", expertise="Python, Django, FastAPI"),
        Faculty(name="Priya Sharma", email="priya@deccansoft.net",  expertise="Data Science, ML, TensorFlow"),
        Faculty(name="Anil Reddy",   email="anil@deccansoft.net",   expertise="Java, Spring Boot, Microservices"),
        Faculty(name="Meena Iyer",   email="meena@deccansoft.net",  expertise="DevOps, AWS, Kubernetes"),
    ]
    db.add_all(faculty_list)
    db.flush()

    # ── Batches ───────────────────────────────────────────────────────────────
    batches = [
        Batch(course_id=1, faculty_id=1, start_date="2026-06-10", end_date="2026-09-26", schedule="Mon/Wed/Fri 10am-1pm",  max_students=20),
        Batch(course_id=1, faculty_id=1, start_date="2026-07-01", end_date="2026-10-17", schedule="Sat/Sun 9am-1pm",       max_students=25),
        Batch(course_id=2, faculty_id=2, start_date="2026-06-15", end_date="2026-09-07", schedule="Tue/Thu 2pm-5pm",       max_students=20),
        Batch(course_id=3, faculty_id=3, start_date="2026-06-10", end_date="2026-09-26", schedule="Mon/Wed/Fri 2pm-5pm",   max_students=20),
        Batch(course_id=4, faculty_id=4, start_date="2026-07-01", end_date="2026-09-09", schedule="Sat/Sun 2pm-6pm",       max_students=15),
    ]
    db.add_all(batches)
    db.flush()

    # ── Students ──────────────────────────────────────────────────────────────
    students = [
        Student(name="Arjun Mehta",  email="arjun@gmail.com",  phone="9876543210", enrolled_date="2026-06-01"),
        Student(name="Sneha Patel",  email="sneha@gmail.com",  phone="9876543211", enrolled_date="2026-06-01"),
        Student(name="Rahul Singh",  email="rahul@gmail.com",  phone="9876543212", enrolled_date="2026-06-02"),
        Student(name="Divya Nair",   email="divya@gmail.com",  phone="9876543213", enrolled_date="2026-06-02"),
        Student(name="Kiran Rao",    email="kiran@gmail.com",  phone="9876543214", enrolled_date="2026-06-03"),
    ]
    db.add_all(students)
    db.flush()

    # ── Enrollments ───────────────────────────────────────────────────────────
    enrollments = [
        Enrollment(student_id=1, batch_id=1, enrollment_date="2026-06-01", status="active"),  # Arjun → Python Batch 1
        Enrollment(student_id=2, batch_id=1, enrollment_date="2026-06-01", status="active"),  # Sneha → Python Batch 1
        Enrollment(student_id=3, batch_id=3, enrollment_date="2026-06-02", status="active"),  # Rahul → Data Science
        Enrollment(student_id=4, batch_id=4, enrollment_date="2026-06-02", status="active"),  # Divya → Java
        Enrollment(student_id=5, batch_id=5, enrollment_date="2026-06-03", status="active"),  # Kiran → DevOps
        Enrollment(student_id=1, batch_id=3, enrollment_date="2026-06-01", status="active"),  # Arjun also in Data Science
    ]
    db.add_all(enrollments)
    db.commit()
    print("Database seeded successfully!")
    db.close()


if __name__ == "__main__":
    seed()
