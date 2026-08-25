import os

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///institute.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Course(Base):
    __tablename__ = "courses"

    id          = Column(Integer, primary_key=True)
    title       = Column(String, nullable=False)
    description = Column(Text)
    duration_weeks = Column(Integer)
    fees        = Column(Float)

    batches = relationship("Batch", back_populates="course")


class Faculty(Base):
    __tablename__ = "faculty"

    id        = Column(Integer, primary_key=True)
    name      = Column(String, nullable=False)
    email     = Column(String, unique=True)
    expertise = Column(String)

    batches = relationship("Batch", back_populates="faculty")


class Batch(Base):
    __tablename__ = "batches"

    id           = Column(Integer, primary_key=True)
    course_id    = Column(Integer, ForeignKey("courses.id"))
    faculty_id   = Column(Integer, ForeignKey("faculty.id"))
    start_date   = Column(String)
    end_date     = Column(String)
    schedule     = Column(String)   # e.g. "Mon/Wed/Fri 10am-1pm"
    max_students = Column(Integer, default=20)

    course      = relationship("Course",  back_populates="batches")
    faculty     = relationship("Faculty", back_populates="batches")
    enrollments = relationship("Enrollment", back_populates="batch")


class Student(Base):
    __tablename__ = "students"

    id            = Column(Integer, primary_key=True)
    name          = Column(String, nullable=False)
    email         = Column(String, unique=True)
    phone         = Column(String)
    enrolled_date = Column(String)

    enrollments = relationship("Enrollment", back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id              = Column(Integer, primary_key=True)
    student_id      = Column(Integer, ForeignKey("students.id"))
    batch_id        = Column(Integer, ForeignKey("batches.id"))
    enrollment_date = Column(String)
    status          = Column(String, default="active")  # active | completed | dropped

    student = relationship("Student", back_populates="enrollments")
    batch   = relationship("Batch",   back_populates="enrollments")


def init_db():
    Base.metadata.create_all(engine)
