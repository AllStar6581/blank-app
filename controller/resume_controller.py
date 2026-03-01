"""Pydantic models for resume data: contacts, education, experience, and the full resume page."""

from collections import Counter, defaultdict
from datetime import date
from functools import cached_property
from typing import Any, List

import dateparser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, HttpUrl, root_validator

from controller.data_structures import CaseInsensitiveSet


class Contact(BaseModel):
    """A contact link (social media, portfolio, etc.) displayed on the resume."""

    name: str
    icon: str | None = None
    link: str | None = None
    text: str | None = None
    emojii_prefix: str = ""

    def to_markdown(self) -> str:
        return f"{self.emojii_prefix} [{self.text}]({self.link})"


class Education(BaseModel):
    """An education entry with degree, university, and time period."""

    degree: str
    university: str
    programme: str
    year_start: int
    year_end: int
    website: HttpUrl
    icon: str | None = None


class SpokenLanguage(BaseModel):
    """A spoken language with proficiency level."""

    name: str
    level: str


class SkillCategorized(BaseModel):
    """A skill with an optional category for grouping."""

    name: str
    category: str | None = None


class Experience(BaseModel):
    """A single work experience entry with date parsing and duration calculation."""

    company_name: str
    company_contacts: str
    company_contacts_link: str | None = None
    work_start_date: date | str
    work_end_date: date | str | None = None
    work_start_date_object: date | None = None
    work_end_date_object: date | None = None
    total_time_delta: Any = None
    is_still_working: bool = False
    position_name: str
    description: str | None = None
    action_points: List[str] | None = None
    responsibilities: List[str] | None = None
    skills: List[str | SkillCategorized] | None = None
    skill_set_upper: set | None = None
    video_links: List[str] | None = None
    location: str | None = None

    @property
    def current(self) -> bool:
        return self.is_still_working

    @property
    def duration_months(self) -> int:
        """Calculate total months worked using month-level granularity."""
        year_to_month_mapping = defaultdict(set)
        for dt in rrule.rrule(
            rrule.MONTHLY,
            dtstart=self.work_start_date_object,
            until=self.work_end_date_object,
        ):
            year_to_month_mapping[dt.year].add(dt.month)
        return sum(len(months) for months in year_to_month_mapping.values())

    @root_validator(pre=True)
    def parse_dates_and_skills(cls, values):
        """Parse date strings into date objects and compute duration delta."""
        actual_date_start = dateparser.parse(
            values.get("work_start_date"),
            date_formats=["%d-%m-%Y", "%m-%Y"],
            settings={"PREFER_DAY_OF_MONTH": "first"},
        ).date()

        is_still_working = False
        try:
            actual_date_end = dateparser.parse(
                values.get("work_end_date"),
                date_formats=["%d-%m-%Y", "%m-%Y"],
                settings={"PREFER_DAY_OF_MONTH": "last"},
            ).date()
        except TypeError:
            actual_date_end = date.today()
            is_still_working = True

        values["work_start_date_object"] = actual_date_start
        values["work_end_date_object"] = actual_date_end
        values["is_still_working"] = is_still_working

        delta = relativedelta(actual_date_end, actual_date_start)
        if delta.days >= 0:
            delta.months += 1
        if delta.months >= 12:
            delta.months -= 12
            delta.years += 1
        values["total_time_delta"] = delta

        skill_set_upper = set()
        for skill in values.get("skills", []):
            if isinstance(skill, str):
                skill_set_upper.add(skill.upper())
            else:
                skill_set_upper.add(SkillCategorized(**skill).name)
        values["skill_set_upper"] = skill_set_upper

        return values


def _extract_skill_name(skill: str | SkillCategorized) -> str:
    """Extract the display name from a skill (string or SkillCategorized)."""
    if isinstance(skill, str):
        return skill
    if isinstance(skill, SkillCategorized):
        return skill.name
    raise TypeError(f"Unexpected skill type: {type(skill)}")


class ResumePage(BaseModel):
    """Full resume model aggregating contacts, experience, education, and skills."""

    first_name: str = ""
    last_name: str = ""
    email: str | None = None
    tel: str | None = None
    website: HttpUrl | str | None = None
    expected_position: str = ""
    expected_salary: str | None = None
    photo: str | None = None
    about: str | None = None

    contacts: List[Contact] | None = None
    exp: List[Experience] | None = None
    edu: List[Education] | None = None
    spoken_languages: List[SpokenLanguage] | None = None

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return self.name

    @property
    def position(self) -> str:
        return self.expected_position

    @property
    def counter_of_main_skills(self) -> Counter:
        """Count how many experience entries each skill appears in."""
        experience_counter = Counter()
        for experience in self.exp:
            for skill in experience.skills:
                experience_counter[_extract_skill_name(skill).lower()] += 1
        return experience_counter

    @property
    def ordered_experience(self) -> List[Experience]:
        """Return experiences sorted by end date (most recent first)."""
        experience = self.exp
        experience.sort(key=lambda exp_: exp_.work_end_date_object, reverse=True)
        return experience

    @property
    def all_skills_set(self) -> set[str]:
        """Return a set of all unique skill names across all experiences."""
        return {_extract_skill_name(skill) for exp_ in self.exp for skill in exp_.skills}

    @property
    def all_skills_categorized(self) -> dict[str, list[str]]:
        """Return skills grouped by category from data, with 'Other skills' as fallback."""
        categories: dict[str, set[str]] = {}
        for exp_ in self.exp:
            for skill in exp_.skills:
                if isinstance(skill, SkillCategorized) and skill.category:
                    cat = skill.category
                    name = skill.name
                else:
                    cat = "Other skills"
                    name = _extract_skill_name(skill)
                categories.setdefault(cat, set()).add(name)
        return {k: sorted(v) for k, v in categories.items()}

    @cached_property
    def total_experience_months(self) -> int:
        """Calculate total unique months worked (handles overlapping periods)."""
        year_to_month_mapping = defaultdict(set)
        for exp in self.exp:
            for dt in rrule.rrule(
                rrule.MONTHLY,
                dtstart=exp.work_start_date_object,
                until=exp.work_end_date_object,
            ):
                year_to_month_mapping[dt.year].add(dt.month)
        return sum(len(months) for months in year_to_month_mapping.values())

    @cached_property
    def total_experience_months_wide(self) -> int:
        """Calculate months from earliest start to latest end date."""
        date_starts = [exp.work_start_date_object for exp in self.exp]
        date_ends = [exp.work_end_date_object for exp in self.exp]

        year_to_month_mapping = defaultdict(set)
        for dt in rrule.rrule(
            rrule.MONTHLY, dtstart=min(date_starts), until=max(date_ends)
        ):
            year_to_month_mapping[dt.year].add(dt.month)
        return sum(len(months) for months in year_to_month_mapping.values())

    @classmethod
    def from_json(cls, json_object: dict) -> "ResumePage":
        """Build a ResumePage from a raw dictionary, parsing nested models."""
        contacts = [Contact(**c) for c in json_object.get("contacts", [])]
        exp = [Experience(**e) for e in json_object.get("exp", [])]
        edu = [Education(**e) for e in json_object.get("edu", [])]
        spoken_languages = [
            SpokenLanguage(**sl) for sl in json_object.get("spoken_languages", [])
        ]

        page_dict = {
            **json_object,
            "contacts": contacts,
            "exp": exp,
            "edu": edu,
            "spoken_languages": spoken_languages,
        }
        return cls(**page_dict)
