import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class Project(Base):
    __tablename__ = "projects"

    elp_project_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    industry_type_1 = Column(String, nullable=False)
    industry_type_2 = Column(String, nullable=True)
    problem_category_1 = Column(String, nullable=False)
    problem_category_2 = Column(String, nullable=True)
    problem_category_3 = Column(String, nullable=True)
    problem_description = Column(Text, nullable=False)
    expected_outcomes = Column(Text, nullable=False)


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String, unique=True, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4()))
    student_1_name = Column(String, nullable=False)
    student_1_roll = Column(String, nullable=False)
    student_1_email = Column(String, nullable=True)
    student_2_name = Column(String, nullable=False)
    student_2_roll = Column(String, nullable=False)
    student_2_email = Column(String, nullable=True)
    student_3_name = Column(String, nullable=False)
    student_3_roll = Column(String, nullable=False)
    student_3_email = Column(String, nullable=True)
    student_4_name = Column(String, nullable=False)
    student_4_roll = Column(String, nullable=False)
    student_4_email = Column(String, nullable=True)
    student_5_name = Column(String, nullable=False)
    student_5_roll = Column(String, nullable=False)
    student_5_email = Column(String, nullable=True)
    is_submitted = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    preferences = relationship("Preference", back_populates="group", order_by="Preference.rank")



class Preference(Base):
    __tablename__ = "preferences"
    __table_args__ = (UniqueConstraint("group_id", "rank"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String, ForeignKey("groups.group_id"), nullable=False)
    elp_project_id = Column(String, ForeignKey("projects.elp_project_id"), nullable=False)
    rank = Column(Integer, nullable=False)

    group = relationship("Group", back_populates="preferences")
    project = relationship("Project")
