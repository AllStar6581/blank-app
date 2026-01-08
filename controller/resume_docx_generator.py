from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os
from dateutil import rrule
from collections import defaultdict
from string import Template
# from string import templatelib

from controller.resume_controller import ResumePage, Experience, SkillCategorized


class InternationalDocxGenerator:
    """Generates a clean, professional DOCX resume for international use"""

    MAX_EXPERIENCE_ITEMS:int|None = 6
    MAX_ACTION_POINTS:int|None = None
    MAX_RESPONSIBILITIES:int|None = None
    MAX_SKILLS_PER_EXPERIENCE:int|None = None

    SHOW_ACTION_POINTS_LATEST_EXPERIENCE_ITEMS:int|None = None
    SHOW_RESPONSIBILITIES_LATEST_EXPERIENCE_ITEMS:int|None = None
    SHOW_SKILLS_LATEST_EXPERIENCE_ITEMS:int|None = None 
    SHOW_DESCRIPTION_LATEST_EXPERIENCE_ITEMS:int|None = None

    TMPL_LEAD_TO_WEBSITE = Template(
        "There are more items covering $str_years_month_exp of work experience." \
        " For details see my site: ",
    )

    def __init__(self, resume: ResumePage):
        self.resume = resume
        self.doc = Document()
        self._setup_document()

    def _setup_document(self):
        """Setup document styles and margins"""
        # Set narrower margins for better space utilization
        sections = self.doc.sections
        for section in sections:
            # Standard margins (ATS can handle these)
            section.top_margin = Cm(1.5)  # 0.6 inches
            section.bottom_margin = Cm(1.5)
            section.left_margin = Cm(1.5)  # 0.6 inches
            section.right_margin = Cm(1.5)

        # Set default font to something ATS-friendly
        style = self.doc.styles["Normal"]
        style.font.name = "Calibri"  # ATS-safe font
        style.font.size = Pt(10)  # Standard readable size
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.0

    def generate(self, output_path: str):
        """Generate and save the DOCX document"""
        self._add_ats_header()
        self._add_concise_summary()
        # self._add_experience()
        self._add_ats_experience()
        # self._add_education()
        self._add_ats_education()
        # self._add_skills()
        self._add_ats_skills()
        # self._add_languages()
        self._add_ats_languages()

        self.doc.save(output_path)

    def _add_header(self):
        """Add name, position, and contacts"""
        # Name
        name_para = self.doc.add_paragraph()
        name_run = name_para.add_run(self.resume.name.upper())
        name_run.font.size = Pt(16)
        name_run.font.color.rgb = RGBColor(0, 0, 0)
        name_run.bold = True
        name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Position
        position_para = self.doc.add_paragraph()
        position_run = position_para.add_run(self.resume.expected_position)
        position_run.font.size = Pt(12)
        position_run.font.color.rgb = RGBColor(100, 100, 100)
        position_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Contacts
        if self.resume.contacts:
            contacts_para = self.doc.add_paragraph()
            contacts_text = " | ".join(contact.text for contact in self.resume.contacts)
            contacts_run = contacts_para.add_run(contacts_text)
            contacts_run.font.size = Pt(9)
            contacts_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

        self.doc.add_paragraph()  # Add spacing

    def _add_ats_header(self):
        """Simple ATS-friendly header"""
        # Name
        name_para = self.doc.add_paragraph()
        name_run = name_para.add_run(self.resume.name.upper())
        name_run.font.size = Pt(14)
        name_run.bold = True

        # Position and total experience
        total_years = self.resume.total_experience_months // 12
        exp_text = f" | {total_years}+ years experience" if total_years > 0 else ""
        position_para = self.doc.add_paragraph()
        position_run = position_para.add_run(
            f"{self.resume.expected_position}{exp_text}"
        )
        position_run.font.size = Pt(11)
        position_run.font.color.rgb = RGBColor(80, 80, 80)

        # Contact info in simple format (no icons, no complex formatting)
        contact_para = self.doc.add_paragraph()
        if self.resume.tel:
            contact_para.add_run(self.resume.tel)
        if self.resume.email:
            contact_para.add_run(" | ")
            self._create_hyperlink(
                contact_para, self.resume.email, f"mailto:{self.resume.email}"
            )
        if self.resume.website:
            contact_para.add_run(" | ")
            self._create_hyperlink(
                contact_para,
                self.resume.website.replace("http://", "").replace("https://", ""),
                self.resume.website,
            )

        # Contact info with clickable hyperlinks
        if self.resume.contacts:
            contact_para.add_run(" | ")

            # Process contacts to create hyperlinks
            clickable_contacts = []
            for i, contact in enumerate(self.resume.contacts[:4]):  # Limit to 4
                if contact.link:
                    # Create clickable hyperlink
                    clickable_text = self._create_hyperlink(
                        contact_para, contact.text or contact.value, contact.link
                    )
                else:
                    # Just plain text
                    contact_para.add_run(contact.text or contact.value)

                # Add separator (except after last)
                if i < len(self.resume.contacts[:]) - 1:
                    contact_para.add_run(" | ")

            # Style the contact paragraph
            for run in contact_para.runs:
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(100, 100, 100)

        # Simple separator line
        self._add_ats_horizontal_line()

    def _add_concise_summary(self):
        """Brief professional summary"""
        if self.resume.about:
            # Truncate to ensure it's brief
            summary_text = self.resume.about
            # if len(summary_text) > 150:
            #     # Find a good breaking point
            #     cutoff = summary_text.find('.', 100, 140)
            #     if cutoff > 0:
            #         summary_text = summary_text[:cutoff + 1]
            #     else:
            #         summary_text = summary_text[:140] + "..."

            summary_para = self.doc.add_paragraph()
            summary_run = summary_para.add_run(summary_text)
            summary_run.font.size = Pt(9)
            summary_run.italic = True
            summary_para.paragraph_format.space_after = Pt(6)

    def _add_ats_experience(self):
        """ATS-friendly experience section using constants for content limits"""
        if not self.resume.exp:
            return

        self._add_ats_section_header("WORK EXPERIENCE")

        # Get limited number of experiences
        len_all_experience_items = len(self.resume.ordered_experience)
        experiences = self.resume.ordered_experience[: self.MAX_EXPERIENCE_ITEMS]

        for exp_index, exp in enumerate(experiences):
            # Header line
            header_para = self.doc.add_paragraph()
            company_run = header_para.add_run(exp.company_name)
            company_run.bold = True
            company_run.font.size = Pt(10)

            header_para.add_run(" | ")
            position_run = header_para.add_run(exp.position_name)
            position_run.font.size = Pt(10)

            # Dates
            # header_para.add_run("\t")
            header_para.add_run(" | ")
            duration = self._format_duration(exp)
            duration_run = header_para.add_run(duration)
            duration_run.font.size = Pt(9)
            duration_run.font.color.rgb = RGBColor(120, 120, 120)

            # Description (only for recent positions)
            if (
                self.SHOW_DESCRIPTION_LATEST_EXPERIENCE_ITEMS is None
                or exp_index < self.SHOW_DESCRIPTION_LATEST_EXPERIENCE_ITEMS
            ):
                if exp.description:
                    desc_para = self.doc.add_paragraph()
                    desc_para.paragraph_format.left_indent = Cm(0.5)
                    desc_run = desc_para.add_run(exp.description)
                    desc_run.font.size = Pt(9)

            # Action points (only for recent positions)
            if (
                self.SHOW_ACTION_POINTS_LATEST_EXPERIENCE_ITEMS is None
                or exp_index < self.SHOW_ACTION_POINTS_LATEST_EXPERIENCE_ITEMS
            ):
                if exp.action_points:
                    for point in exp.action_points[: self.MAX_ACTION_POINTS]:
                        bullet_para = self.doc.add_paragraph()
                        bullet_para.paragraph_format.left_indent = Cm(0.5)
                        bullet_para.style = "List Bullet"
                        bullet_para.add_run(point).font.size = Pt(9)

            # Responsibilities (only for recent positions)
            if (
                self.SHOW_RESPONSIBILITIES_LATEST_EXPERIENCE_ITEMS is None
                or exp_index < self.SHOW_RESPONSIBILITIES_LATEST_EXPERIENCE_ITEMS
            ):
                if exp.responsibilities:
                    for resp in exp.responsibilities[: self.MAX_RESPONSIBILITIES]:
                        bullet_para = self.doc.add_paragraph()
                        bullet_para.paragraph_format.left_indent = Cm(0.5)
                        bullet_para.style = "List Bullet"
                        bullet_para.add_run(resp).font.size = Pt(9)

            # Skills (only for recent positions)
            if (
                self.SHOW_SKILLS_LATEST_EXPERIENCE_ITEMS is None
                or exp_index < self.SHOW_SKILLS_LATEST_EXPERIENCE_ITEMS
            ):
                if exp.skills:
                    skills_para = self.doc.add_paragraph()
                    skills_para.paragraph_format.left_indent = Cm(0.5)
                    skills_list_uncategorized = []
                    for skill in exp.skills:
                        if isinstance(skill, str):
                            skills_list_uncategorized.append(skill)
                        elif isinstance(skill, SkillCategorized):
                            skills_list_uncategorized.append(skill.name)
                        else:
                            raise Exception("Unexpected object in skillset")
                    skills_text = "Technologies: " + ", ".join(
                        skills_list_uncategorized[: self.MAX_SKILLS_PER_EXPERIENCE]
                    )
                    skills_run = skills_para.add_run(skills_text)
                    skills_run.font.size = Pt(8)
                    skills_run.font.color.rgb = RGBColor(150, 150, 150)
                    skills_run.italic = True

            # Space between experiences (except last one)
            if exp_index < len(experiences) - 1:
                self.doc.add_paragraph().add_run().add_break()
        
        if self.MAX_EXPERIENCE_ITEMS is not None and self.MAX_EXPERIENCE_ITEMS < len_all_experience_items:
            items_left = len_all_experience_items - self.MAX_EXPERIENCE_ITEMS

            experiences_left = self.resume.ordered_experience[self.MAX_EXPERIENCE_ITEMS:]
            
            year_to_month_work_mapping = defaultdict(set)
            date_start_list = []
            date_end_list = []
            for exp_left in experiences_left:
                date_start_list.append(exp_left.work_start_date_object)
                date_end_list.append(exp_left.work_end_date_object)

            for dt in rrule.rrule(
                rrule.MONTHLY, dtstart=min(date_start_list), until=max(date_end_list)
            ):
                year_to_month_work_mapping[dt.year].add(dt.month)
            overall_months = 0
            for year, month_set in year_to_month_work_mapping.items():
                overall_months += len(month_set)

            years_left, months_left = overall_months // 12, overall_months % 12
            str_years_month_exp = f"{years_left} years"
            if months_left:
                str_years_month_exp += f" {months_left} months"
            self.doc.add_paragraph().add_run().add_break()
            header_para = self.doc.add_paragraph()
            site_lead_text = self.TMPL_LEAD_TO_WEBSITE.safe_substitute(
                int_exp_items_count=items_left,
                str_years_month_exp=str_years_month_exp,
            )
            shortage_text_run = header_para.add_run(text=site_lead_text)
            # shortage_text_run.font.size = Pt(11)
            shortage_text_run.font.color.rgb = RGBColor(80, 80, 80)
            shortage_text_run.bold = True
            self._create_hyperlink(
                header_para,
                self.resume.website.replace("http://", "").replace("https://", ""),
                self.resume.website,
            )
            self.doc.add_paragraph().add_run().add_break()

    def _add_ats_education(self):
        """ATS-friendly education section"""
        if not self.resume.edu:
            return

        self._add_ats_section_header("EDUCATION")

        # Show only highest/most recent education
        for edu in self.resume.edu[:2]:
            # University and degree on one line
            edu_para = self.doc.add_paragraph()

            # University (bold)
            uni_run = edu_para.add_run(edu.university)
            uni_run.bold = True
            uni_run.font.size = Pt(10)

            # Degree
            edu_para.add_run(" | ")
            degree_run = edu_para.add_run(edu.degree)
            degree_run.font.size = Pt(10)

            # Years on same line via tab
            edu_para.add_run("\t")
            years_text = f"{edu.year_start} - {edu.year_end}"
            years_run = edu_para.add_run(years_text)
            years_run.font.size = Pt(9)
            years_run.font.color.rgb = RGBColor(120, 120, 120)

            # Programme/faculty if available
            if edu.programme:
                programme_para = self.doc.add_paragraph()
                programme_para.paragraph_format.left_indent = Cm(0.5)
                programme_run = programme_para.add_run(edu.programme)
                programme_run.font.size = Pt(9)
                programme_run.font.color.rgb = RGBColor(100, 100, 100)

            self.doc.add_paragraph().add_run().add_break()

    def _add_ats_skills(self):
        """ATS-friendly skills section - NO TABLES, just text"""
        if not hasattr(self.resume, "all_skills_set") or not self.resume.all_skills_set:
            return

        self._add_ats_section_header("TECHNICAL SKILLS")

        # Convert set to sorted list
        skills_list = sorted(list(self.resume.all_skills_set))

        # Categorize skills for better organization
        categorized = self._categorize_skills_for_ats(skills_list)

        # Build skill text in paragraphs (NO TABLES)
        for category, skills in categorized.items():
            if skills:
                # Category as bold text
                category_para = self.doc.add_paragraph()
                category_run = category_para.add_run(f"{category}: ")
                category_run.bold = True
                category_run.font.size = Pt(9)

                # Skills as comma-separated list
                skills_text = ", ".join(skills[:8])  # Limit per category
                skills_run = category_para.add_run(skills_text)
                skills_run.font.size = Pt(9)

        self.doc.add_paragraph().add_run().add_break()

    def _categorize_skills_for_ats(self, skills_list):
        """Organize skills without using tables"""
        categories = {
            "Programming Languages": [],
            "Frameworks & Libraries": [],
            "Databases": [],
            "Tools & Platforms": [],
            "Cloud & DevOps": [],
        }

        # Simple keyword-based categorization
        for skill in skills_list:
            skill_lower = skill.lower()

            # Programming languages
            prog_keywords = [
                "python",
                "java",
                "javascript",
                "c++",
                "c#",
                "go",
                "rust",
                "ruby",
                "php",
                "swift",
                "kotlin",
                "typescript",
            ]
            if any(keyword in skill_lower for keyword in prog_keywords):
                categories["Programming Languages"].append(skill)
                continue

            # Frameworks
            framework_keywords = [
                "react",
                "react.js",
                "angular",
                "vue",
                "django",
                "spring",
                "node",
                "express",
                "laravel",
                "flask",
                "fastapi",
                ".net",
            ]
            if any(keyword in skill_lower for keyword in framework_keywords):
                categories["Frameworks & Libraries"].append(skill)
                continue

            # Databases
            db_keywords = [
                "postgresql",
                "mysql",
                "mongodb",
                "redis",
                "oracle",
                "sql",
                "dynamodb",
                "cassandra",
            ]
            if any(keyword in skill_lower for keyword in db_keywords):
                categories["Databases"].append(skill)
                continue

            # Cloud & DevOps
            cloud_keywords = [
                "docker",
                "kubernetes",
                "aws",
                "azure",
                "gcp",
                "jenkins",
                "terraform",
                "ansible",
            ]
            if any(keyword in skill_lower for keyword in cloud_keywords):
                categories["Cloud & DevOps"].append(skill)
                continue

            # Everything else goes to Tools & Platforms
            categories["Tools & Platforms"].append(skill)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def _add_ats_languages(self):
        """ATS-friendly languages section"""
        if not self.resume.spoken_languages:
            return

        self._add_ats_section_header("LANGUAGES")

        # Simple comma-separated list
        languages_text = ", ".join(
            f"{lang.name} ({lang.level})" for lang in self.resume.spoken_languages
        )

        languages_para = self.doc.add_paragraph()
        languages_para.add_run(languages_text).font.size = Pt(9)

    def _format_duration(self, experience):
        """Format experience duration"""
        if experience.is_still_working:
            end_text = "Present"
        else:
            end_text = experience.work_end_date_object.strftime("%b %Y")

        start_text = experience.work_start_date_object.strftime("%b %Y")
        return f"{start_text} - {end_text}"

    def _add_ats_section_header(self, title: str):
        """Simple ATS-friendly section header"""
        para = self.doc.add_paragraph()
        para.paragraph_format.space_before = Pt(8)
        para.paragraph_format.space_after = Pt(4)

        run = para.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(11)

        # Simple underline that ATS can handle
        p = para._element
        pPr = p.get_or_add_pPr()
        bottom_border = OxmlElement("w:bottom")
        bottom_border.set(qn("w:val"), "single")
        bottom_border.set(qn("w:sz"), "6")
        bottom_border.set(qn("w:space"), "1")
        bottom_border.set(qn("w:color"), "000000")  # Black
        pPr.append(bottom_border)

    def _add_ats_horizontal_line(self):
        """Simple line separator (ATS can handle this)"""
        para = self.doc.add_paragraph()
        p = para._element
        pPr = p.get_or_add_pPr()
        bottom_border = OxmlElement("w:bottom")
        bottom_border.set(qn("w:val"), "single")
        bottom_border.set(qn("w:sz"), "3")
        bottom_border.set(qn("w:space"), "1")
        bottom_border.set(qn("w:color"), "000000")
        pPr.append(bottom_border)
        para.paragraph_format.space_after = Pt(6)

    def _create_hyperlink(self, paragraph, text, url):
        """
        Create a clickable hyperlink in a DOCX paragraph.
        Returns the hyperlink run so you can style it.
        """
        # This is the key method that creates actual hyperlinks

        # Create hyperlink element
        hyperlink = self._add_hyperlink(paragraph, url, text)

        # Style the hyperlink (blue, underlined - standard for links)
        hyperlink.font.color.rgb = RGBColor(0, 102, 204)  # Blue
        hyperlink.font.underline = True
        hyperlink.font.size = Pt(9)

        return hyperlink

    def _add_hyperlink(self, paragraph, url, text):
        """
        Low-level method to add a hyperlink to a paragraph.
        This creates a proper Word hyperlink.
        """
        # Create the hyperlink relationship
        part = paragraph.part
        r_id = part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)

        # Create hyperlink XML element
        hyperlink = OxmlElement("w:hyperlink")
        hyperlink.set(qn("r:id"), r_id)

        # Create run for the hyperlink text
        new_run = OxmlElement("w:r")

        # Create text element
        text_elem = OxmlElement("w:t")
        text_elem.text = text
        new_run.append(text_elem)

        # Add run properties for styling
        rPr = OxmlElement("w:rPr")

        # Color
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "0066CC")  # Blue
        rPr.append(color)

        # Underline
        underline = OxmlElement("w:u")
        underline.set(qn("w:val"), "single")
        rPr.append(underline)

        new_run.insert(0, rPr)
        hyperlink.append(new_run)

        # Add to paragraph
        paragraph._p.append(hyperlink)

        # Return a run object for further styling
        from docx.text.run import Run

        return Run(hyperlink.find(qn("w:r")), paragraph)

    def _add_summary(self):
        """Add professional summary"""
        if self.resume.about:
            self._add_section_header("Professional Summary")
            summary_para = self.doc.add_paragraph()
            summary_para.add_run(self.resume.about)
            summary_para.paragraph_format.space_after = Pt(12)

    def _add_experience(self):
        """Add work experience section"""
        if not self.resume.exp:
            return

        self._add_section_header("Work Experience")

        for exp in self.resume.ordered_experience:
            # Company and position line
            exp_para = self.doc.add_paragraph()

            # Company (bold)
            company_run = exp_para.add_run(exp.company_name)
            company_run.bold = True
            company_run.font.size = Pt(11)

            # Separator
            exp_para.add_run(" | ")

            # Position
            position_run = exp_para.add_run(exp.position_name)
            position_run.font.size = Pt(11)

            # Duration (right-aligned)
            duration = self._format_duration(exp)
            duration_run = exp_para.add_run(f" | {duration}")
            duration_run.font.size = Pt(10)
            duration_run.font.color.rgb = RGBColor(100, 100, 100)

            # Location if available
            if exp.location:
                location_run = exp_para.add_run(f" | {exp.location}")
                location_run.font.size = Pt(10)
                location_run.font.color.rgb = RGBColor(100, 100, 100)

            # Responsibilities
            if exp.responsibilities:
                for responsibility in exp.responsibilities:
                    resp_para = self.doc.add_paragraph(style="List Bullet")
                    resp_para.add_run(responsibility)
                    resp_para.paragraph_format.left_indent = Inches(0.25)
                    resp_para.paragraph_format.space_after = Pt(6)

            # Skills used in this position
            if exp.skills:
                skills_para = self.doc.add_paragraph()
                skills_run = skills_para.add_run("Technologies: ")
                skills_run.font.size = Pt(9)
                skills_run.italic = True
                skills_run.font.color.rgb = RGBColor(100, 100, 100)

                skills_text = ", ".join(exp.skills)
                skills_value_run = skills_para.add_run(skills_text)
                skills_value_run.font.size = Pt(9)
                skills_value_run.font.color.rgb = RGBColor(100, 100, 100)

            self.doc.add_paragraph()  # Add spacing between experiences

    def _add_education(self):
        """Add education section"""
        if not self.resume.edu:
            return

        self._add_section_header("Education")

        for edu in self.resume.edu:
            edu_para = self.doc.add_paragraph()

            # University (bold)
            uni_run = edu_para.add_run(edu.university)
            uni_run.bold = True
            uni_run.font.size = Pt(11)

            # Degree
            edu_para.add_run(" | ")
            degree_run = edu_para.add_run(edu.degree)
            degree_run.font.size = Pt(11)

            # Years
            years_run = edu_para.add_run(f" | {edu.year_start}-{edu.year_end}")
            years_run.font.size = Pt(10)
            years_run.font.color.rgb = RGBColor(100, 100, 100)

            # Faculty if available
            if edu.programme:
                faculty_para = self.doc.add_paragraph()
                faculty_run = faculty_para.add_run(edu.programme)
                faculty_run.font.size = Pt(10)
                faculty_run.italic = True
                faculty_run.font.color.rgb = RGBColor(100, 100, 100)
                faculty_para.paragraph_format.left_indent = Inches(0.25)

    def _add_skills(self):
        """Add skills section with categorization"""
        if not self.resume.all_skills_set:
            return

        self._add_section_header("Skills")

        # Group skills by category
        # TODO
        # skills_by_category = {}
        # for skill in self.resume.all_skills_set:
        #     if skill.category not in skills_by_category:
        #         skills_by_category[skill.category] = []
        #     skills_by_category[skill.category].append(skill)

        # # Create a table for skills
        # if skills_by_category:
        #     table = self.doc.add_table(rows=1, cols=len(skills_by_category))
        #     table.alignment = WD_TABLE_ALIGNMENT.CENTER

        #     # Add each category as a column
        #     for i, (category, skills) in enumerate(skills_by_category.items()):
        #         cell = table.cell(0, i)

        #         # Category header
        #         category_para = cell.paragraphs[0]
        #         category_run = category_para.add_run(category.title())
        #         category_run.bold = True
        #         category_run.font.size = Pt(10)

        #         # Skills list
        #         for skill in skills:
        #             skill_para = cell.add_paragraph()
        #             skill_text = skill.name
        #             if skill.level:
        #                 skill_text += f" ({skill.level})"
        #             if skill.years:
        #                 skill_text += f" - {skill.years}yr"

        #             skill_run = skill_para.add_run(skill_text)
        #             skill_run.font.size = Pt(9)
        #             skill_para.paragraph_format.space_after = Pt(2)

    def _add_languages(self):
        """Add languages section"""
        if not self.resume.spoken_languages:
            return

        self._add_section_header("Languages")

        languages_para = self.doc.add_paragraph()
        languages_text = ", ".join(
            f"{lang.name} ({lang.level})" for lang in self.resume.spoken_languages
        )
        languages_para.add_run(languages_text)

    def _add_section_header(self, title: str):
        """Add a section header with formatting"""
        para = self.doc.add_paragraph()
        para.paragraph_format.space_before = Pt(12)
        para.paragraph_format.space_after = Pt(6)

        run = para.add_run(title.upper())
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0, 0, 0)

        # Add underline
        p = para._element
        pPr = p.get_or_add_pPr()
        bottom_border = OxmlElement("w:bottom")
        bottom_border.set(qn("w:val"), "single")
        bottom_border.set(qn("w:sz"), "8")
        bottom_border.set(qn("w:space"), "1")
        bottom_border.set(qn("w:color"), "auto")
        pPr.append(bottom_border)

    def _format_duration(self, experience: Experience) -> str:
        """Format experience duration"""
        if experience.is_still_working:
            end_text = "Present"
        else:
            end_text = experience.work_end_date_object.strftime("%b %Y")

        start_text = experience.work_start_date_object.strftime("%b %Y")
        return f"{start_text} - {end_text}"
