from pydantic import BaseModel, HttpUrl, root_validator
from typing import List, Any
from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil import rrule
import dateparser
from collections import defaultdict

from collections import Counter
from functools import cached_property
from controller.data_structures import CaseInsensitiveSet


class Contact(BaseModel):
    name: str
    icon: str | None = None
    link: str | None
    text: str | None

    def to_markdown(self):
        # return f"[{self.name}]({self.link})"
        return f"[{self.text}]({self.link})"


class Education(BaseModel):
    degree: str
    university: str
    programme: str
    year_start: int
    year_end: int
    website: HttpUrl
    icon: str | None

    def to_html(self):
        return ""


class SpokenLanguage(BaseModel):
    name: str
    level: str


class SkillCategorized(BaseModel):
    name: str
    category: str | None = None


class Experience(BaseModel):
    company_name: str
    company_contacts: str
    company_contacts_link: str | None
    work_start_date: date | str
    work_end_date: date | str | None
    work_start_date_object: date | None
    work_end_date_object: date | None
    total_time_delta: Any
    is_still_working: bool = False
    position_name: str
    description: str | None
    action_points: List[str] | None
    responsibilities: List[str] | None
    skills: List[str | SkillCategorized] | None
    skill_set_upper: set | None
    video_links: List[str] | None = None
    location: str | None = None

    @property
    def is_still_working(self):
        if not self.work_end_date_object or self.work_end_date_object <= date.today():
            return True
        return False

    @property
    def current(self):
        return self.is_still_working

    @property
    def duration_months(self):
        year_to_month_work_mapping = defaultdict(set)
        for dt in rrule.rrule(
            rrule.MONTHLY,
            dtstart=self.work_start_date_object,
            until=self.work_end_date_object,
        ):
            year_to_month_work_mapping[dt.year].add(dt.month)
        overall_months = 0
        for year, month_set in year_to_month_work_mapping.items():
            overall_months += len(month_set)
        return overall_months

    @root_validator(pre=True)
    def validate_on_create(cls, values):
        is_still_working = False
        actual_date_start = dateparser.parse(
            values.get("work_start_date"),
            date_formats=["%d-%m-%Y", "%m-%Y"],
            settings={"PREFER_DAY_OF_MONTH": "first"},
        ).date()
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

        if is_still_working:
            pass
            # print(values)

        skill_set_upper = set()
        for skill in values.get("skills"):
            if isinstance(skill, str):
                skill_set_upper.add(skill.upper())
            else:
                skill_set_upper.add(SkillCategorized(**skill).name)
        # values["skill_set_upper"] = {x.upper() for x in values.get("skills")}
        values["skill_set_upper"] = skill_set_upper
        return values


class ResumePage(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str | None
    tel: str | None = None
    website: HttpUrl | str | None
    expected_position: str = ""
    expected_salary: str | None = None
    photo: str | None = None
    about: str | None = None

    contacts: List[Contact] | None = None
    exp: List[Experience] | None = None
    edu: List[Education] | None = None
    spoken_languages: List[SpokenLanguage] | None = None

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return self.name

    @property
    def position(self):
        return self.expected_position

    @property
    def counter_of_main_skills(self):
        experience_counter = Counter()
        for experience in self.exp:
            for skill in experience.skills:
                experience_counter[skill.lower()] += 1
        return experience_counter

    @property
    def ordered_experience(self):
        experience = self.exp
        experience.sort(key=lambda exp_: exp_.work_end_date_object, reverse=True)
        return experience

    @property
    def all_skills_set(self):
        experience = self.exp
        skills_set = set()
        for exp_ in experience:
            for skill in exp_.skills:
                if isinstance(skill, str):
                    skills_set.add(skill)
                elif isinstance(skill, SkillCategorized):
                    skills_set.add(skill.name)
                else:
                    raise Exception("Unexpected object in skillset")
        return skills_set

    @property
    def all_categorized_skill_set(self):
        experience = self.exp
        skills_set = CaseInsensitiveSet()
        for exp_ in experience:
            for skill in exp_.skills:
                if isinstance(skill, SkillCategorized):
                    skills_set.add(skill)
                elif isinstance(skill, str):
                    skills_set.add(SkillCategorized(name=skill, category=None))
                else:
                    raise Exception("Unexpected object in skillset")

    # @property
    @cached_property
    def total_experience_months(self):
        year_to_month_work_mapping = defaultdict(set)
        for exp in self.exp:
            date_start = exp.work_start_date_object
            date_end = exp.work_end_date_object
            for dt in rrule.rrule(rrule.MONTHLY, dtstart=date_start, until=date_end):
                year_to_month_work_mapping[dt.year].add(dt.month)

        overall_months = 0
        for year, month_set in year_to_month_work_mapping.items():
            overall_months += len(month_set)

        return overall_months

    # @property
    @cached_property
    def total_experience_months_wide(self):
        year_to_month_work_mapping = defaultdict(set)
        date_start_list = []
        date_end_list = []
        for exp in self.exp:
            date_start_list.append(exp.work_start_date_object)
            date_end_list.append(exp.work_end_date_object)

        for dt in rrule.rrule(
            rrule.MONTHLY, dtstart=min(date_start_list), until=max(date_end_list)
        ):
            year_to_month_work_mapping[dt.year].add(dt.month)
        overall_months = 0
        for year, month_set in year_to_month_work_mapping.items():
            overall_months += len(month_set)
        return overall_months

    @classmethod
    def from_json(cls, json_object):
        contacts_json = json_object.get("contacts")
        contacts = []
        for contact_json in contacts_json:
            contacts.append(Contact(**contact_json))

        experience_json = json_object.get("exp")
        exp = []
        for exp_json in experience_json:
            exp.append(Experience(**exp_json))

        education_json = json_object.get("edu")
        edu = []
        for edu_json in education_json:
            edu.append(Education(**edu_json))

        spoken_languages_json = json_object.get("spoken_languages", [])
        spoken_languages = []
        for spoken_language_json in spoken_languages_json:
            spoken_languages.append(SpokenLanguage(**spoken_language_json))

        page_dict = dict(
            contacts=contacts,
            exp=exp,
            edu=edu,
            spoken_languages=spoken_languages,
        )
        page_dict.update(json_object)

        return cls(**page_dict)

    def to_html(self):
        return ""
