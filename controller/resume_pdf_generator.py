"""PDF resume generator in HH.ru style using ReportLab."""

import os
from io import BytesIO

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from controller.resume_controller import Experience, ResumePage, SkillCategorized, _extract_skill_name


class HHRuPDFGenerator:
    """Generates a compact, information-dense PDF resume in HH.ru style.

    Args:
        resume: Parsed resume data.
        compact: When *True* (default), shows detailed bullets for recent
            positions only and one-liners for the rest.  *False* shows
            full detail for every entry.
    """

    # -- Compact-mode knobs --------------------------------------------------
    DETAILED_EXPERIENCE_COUNT = 3
    COMPACT_MAX_BULLETS = 3
    COMPACT_MAX_SKILLS = 8

    BASE_FONT_SIZE = 9

    # Colors
    TITLE_TEXT_COLOR = "#1a3d6d"
    POSITION_TEXT_COLOR = "#666666"

    # Russian labels
    TXT_TECH_STACK = "Стэк:"
    TXT_WORK_EXPERIENCE = "ОПЫТ РАБОТЫ"
    TXT_EARLIER_CAREER = "ПРОШЛЫЙ ОПЫТ"
    TXT_EDUCATION = "ОБРАЗОВАНИЕ"
    TXT_SKILLS = "КЛЮЧЕВЫЕ НАВЫКИ"
    TXT_LANGUAGES = "ЗНАНИЕ ЯЗЫКОВ"
    TXT_ABOUT = "ОБО МНЕ"
    TXT_YEARS_OF_EXPERIENCE = "лет опыта"
    TXT_PRESENT_TIME = "настоящее время"
    TXT_YEARS = "г."
    TXT_MONTHS = "мес."
    TXT_SEE_DETAILED_CV = "Посмотреть резюме подробнее"

    photo_path = "static/me.jpg"

    # Sizes
    SIZE_QR_CODE_IMAGE = 2.2 * cm
    SIZE_CONTACTS_PICTURE_COLUMN = 6.1 * cm
    SIZE_CONTACTS_TEXT_COLUMN = 6.1 * cm
    SIZE_CONTACTS_QR_COLUMN = 6.1 * cm
    SIZE_PAGE_FORMAT = A4
    SIZE_PAGE_TOP_MARGIN = 0.5 * cm
    SIZE_PAGE_BOTTOM_MARGIN = 0.5 * cm
    SIZE_PAGE_LEFT_MARGIN = 1.5 * cm
    SIZE_PAGE_RIGHT_MARGIN = 1.5 * cm
    SIZE_CONTACTS_PICTURE_IMAGE_HEIGHT = 4.1 * cm
    SIZE_CONTACTS_PICTURE_IMAGE_WIDTH = 4.1 * cm
    SIZE_CONTACTS_PICTURE_COL_WIDTH = 4.5 * cm

    # Table styles
    TABSTYLE_CONTACTS = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ])

    TABSTYLE_QR = TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ])

    TABSTYLE_CONTACTS_TEXT = TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (0, 0), 1),
    ])

    TABSTYLE_CONTACTS_PICTURE = TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (0, 0), 0),
    ])

    def __init__(self, resume: ResumePage, *, compact: bool = True):
        self.resume = resume
        self.compact = compact
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._setup_styles()
        self.elements = []

    def _register_fonts(self):
        """Register Cyrillic-compatible TrueType fonts."""
        try:
            font_path = "DejaVuSans.ttf"
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", font_path))
            pdfmetrics.registerFontFamily(
                "DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
            )
        except Exception as e:
            print(f"Warning: Could not register custom fonts: {e}")

    def _setup_styles(self):
        """Configure HH.ru-specific paragraph styles."""
        base = self.BASE_FONT_SIZE
        self.styles.add(ParagraphStyle(
            name="HH-Title", parent=self.styles["Heading1"],
            fontSize=base + 7, textColor=colors.HexColor(self.TITLE_TEXT_COLOR),
            spaceAfter=4, alignment=TA_LEFT, fontName="DejaVuSans-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-Position", parent=self.styles["Normal"],
            fontSize=base + 3, textColor=colors.HexColor(self.POSITION_TEXT_COLOR),
            spaceAfter=8, alignment=TA_LEFT, fontName="DejaVuSans-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-SectionHeader", parent=self.styles["Heading2"],
            fontSize=base + 3, textColor=colors.HexColor("#1a3d6d"),
            spaceAfter=4, spaceBefore=8, leftIndent=0,
            borderLeft=1, borderLeftColor=colors.HexColor("#1a3d6d"),
            borderLeftWidth=3, paddingLeft=6, fontName="DejaVuSans-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-Company", parent=self.styles["Normal"],
            fontSize=base + 2, textColor=colors.HexColor("#333333"),
            spaceAfter=1, leftIndent=0, fontName="DejaVuSans-Bold",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-Duration", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#666666"),
            spaceAfter=3, leftIndent=0, fontName="DejaVuSans",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-Responsibility", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#444444"),
            spaceAfter=1, leftIndent=12, bulletIndent=12, fontName="DejaVuSans",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-JobDescription", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#444444"),
            spaceAfter=2, leftIndent=12, bulletIndent=12, fontName="DejaVuSans",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-Contact", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#333333"),
            spaceAfter=2, fontName="DejaVuSans",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-About", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#444444"),
            spaceAfter=2, leftIndent=12, bulletIndent=12, fontName="DejaVuSans",
        ))
        self.styles.add(ParagraphStyle(
            name="HH-EarlierCareer", parent=self.styles["Normal"],
            fontSize=base, textColor=colors.HexColor("#555555"),
            spaceAfter=1, leftIndent=0, fontName="DejaVuSans",
        ))

    def generate(self, output_path):
        """Generate and save the PDF document."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.SIZE_PAGE_FORMAT,
            topMargin=self.SIZE_PAGE_TOP_MARGIN,
            bottomMargin=self.SIZE_PAGE_BOTTOM_MARGIN,
            leftMargin=self.SIZE_PAGE_LEFT_MARGIN,
            rightMargin=self.SIZE_PAGE_RIGHT_MARGIN,
        )
        self._build_content()
        doc.build(self.elements)

    def _build_content(self):
        """Assemble all PDF sections."""
        self._add_header()
        self._add_contacts_with_photo_and_qr()
        self._add_experience()
        self._add_education()
        self._add_skills_combined_visualization()
        self._add_languages()
        self._add_about()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _add_header(self):
        """Add name and position header."""
        self.elements.append(
            Paragraph(f"<b>{self.resume.full_name.upper()}</b>", self.styles["HH-Title"])
        )
        total_exp = self.resume.total_experience_months_wide / 12
        exp_text = f", {total_exp:.1f} {self.TXT_YEARS_OF_EXPERIENCE}" if total_exp > 0 else ""
        self.elements.append(
            Paragraph(f"{self.resume.position}{exp_text}", self.styles["HH-Position"])
        )
        self.elements.append(Spacer(1, 0.1 * cm))

    # ------------------------------------------------------------------
    # Contacts + photo + QR
    # ------------------------------------------------------------------

    def _add_contacts_with_photo_and_qr(self):
        """Add three-column layout: photo | contacts | QR code."""
        photo_cell = self._create_photo_cell()
        contacts_cell = self._create_contacts_cell()
        qr_cell = self._create_qr_codes_cell()

        col_widths = [
            self.SIZE_CONTACTS_PICTURE_COLUMN,
            self.SIZE_CONTACTS_TEXT_COLUMN,
            self.SIZE_CONTACTS_QR_COLUMN,
        ]
        table = Table([[photo_cell, contacts_cell, qr_cell]], colWidths=col_widths)
        table.setStyle(self.TABSTYLE_CONTACTS)
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2 * cm))

    def _create_photo_cell(self):
        """Create cell with the profile photo."""
        if not self.photo_path or not os.path.exists(self.photo_path):
            return Paragraph("", self.styles["Normal"])
        try:
            img = Image(
                self.photo_path,
                width=self.SIZE_CONTACTS_PICTURE_IMAGE_WIDTH,
                height=self.SIZE_CONTACTS_PICTURE_IMAGE_HEIGHT,
            )
            photo_table = Table([[img]], colWidths=[self.SIZE_CONTACTS_PICTURE_COL_WIDTH])
            photo_table.setStyle(self.TABSTYLE_CONTACTS_PICTURE)
            return photo_table
        except Exception as e:
            print(f"Warning: Could not load photo: {e}")
            return Paragraph("", self.styles["Normal"])

    def _create_contacts_cell(self):
        """Create cell listing contact information."""
        contact_items = []
        for contact in self.resume.contacts:
            contact_items.append(
                [Paragraph(contact.link, self.styles["HH-Contact"])]
            )
        contact_items.insert(0, Paragraph(self.resume.tel, self.styles["HH-Contact"]))
        contact_items.insert(0, Paragraph(self.resume.email, self.styles["HH-Contact"]))

        contact_table_data = [[item] for item in contact_items]
        contact_table = Table(
            contact_table_data, colWidths=[self.SIZE_CONTACTS_TEXT_COLUMN]
        )
        contact_table.setStyle(self.TABSTYLE_CONTACTS_TEXT)
        return contact_table

    def _create_qr_codes_cell(self):
        """Create cell with QR code linking to the resume website."""
        qr_data_list = [
            {
                "data": self.resume.website,
                "title": self.resume.website,
                "description": self.TXT_SEE_DETAILED_CV,
            }
        ]
        qr_data_list = [item for item in qr_data_list if item and item["data"]][:3]

        qr_items = []
        for qr_data in qr_data_list:
            qr_image = self._generate_qr_code(qr_data["data"], size=self.SIZE_QR_CODE_IMAGE)
            if not qr_image:
                continue

            qr_table = Table(
                [
                    [qr_image],
                    [Paragraph(
                        f"<b>{qr_data['title']}</b>",
                        ParagraphStyle(
                            name="QR-Title", parent=self.styles["Normal"],
                            fontName="DejaVuSans-Bold", fontSize=self.BASE_FONT_SIZE - 2,
                            alignment=TA_CENTER, textColor=colors.HexColor("#333333"),
                        ),
                    )],
                    [Paragraph(
                        qr_data["description"],
                        ParagraphStyle(
                            name="QR-Desc", parent=self.styles["Normal"],
                            fontName="DejaVuSans", fontSize=self.BASE_FONT_SIZE - 3,
                            alignment=TA_CENTER, textColor=colors.HexColor("#666666"),
                        ),
                    )],
                ],
                colWidths=[self.SIZE_CONTACTS_QR_COLUMN],
            )
            qr_table.setStyle(self.TABSTYLE_QR)
            qr_items.append(qr_table)

        if not qr_items:
            return Paragraph("", self.styles["Normal"])
        return Table([qr_items], colWidths=[1 * cm])

    def _generate_qr_code(self, data: str, size=1.5 * cm):
        """Generate a QR code image from a URL or text string."""
        try:
            qr = qrcode.QRCode(
                version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=9, border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            return Image(img_buffer, width=size, height=size)
        except Exception as e:
            print(f"Warning: Could not generate QR code: {e}")
            return None

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------

    def _add_experience(self):
        """Add work experience — tiered in compact mode, full in expanded."""
        if not self.resume.exp:
            return

        self.elements.append(
            Paragraph(self.TXT_WORK_EXPERIENCE, self.styles["HH-SectionHeader"])
        )

        all_exp = self.resume.ordered_experience

        if self.compact:
            detailed = all_exp[: self.DETAILED_EXPERIENCE_COUNT]
            remaining = all_exp[self.DETAILED_EXPERIENCE_COUNT :]

            for exp in detailed:
                self._render_detailed_entry(exp, max_bullets=self.COMPACT_MAX_BULLETS)

            if remaining:
                self._render_earlier_career(remaining)
        else:
            for exp in all_exp:
                self._render_detailed_entry(exp, max_bullets=None)

    def _render_detailed_entry(self, exp: Experience, *, max_bullets: int | None):
        """Render a single experience entry with configurable bullet limit."""
        company_text = f"<b>{exp.company_name}</b>"
        if exp.location:
            company_text += f" ({exp.location})"
        self.elements.append(Paragraph(company_text, self.styles["HH-Company"]))

        duration = self._format_duration(exp)
        self.elements.append(
            Paragraph(f"{exp.position_name} | {duration}", self.styles["HH-Duration"])
        )

        # Description (full mode only)
        if not self.compact and exp.description:
            self.elements.append(
                Paragraph(exp.description, self.styles["HH-JobDescription"])
            )

        # Merge action_points + responsibilities into one bullet list
        bullets = (exp.action_points or []) + (exp.responsibilities or [])
        for resp in bullets[:max_bullets]:
            self.elements.append(
                Paragraph(f"• {resp}", self.styles["HH-Responsibility"])
            )

        # Technologies
        if exp.skills:
            skills_limit = self.COMPACT_MAX_SKILLS if self.compact else None
            skill_names = ", ".join(
                _extract_skill_name(s) for s in exp.skills[:skills_limit]
            )
            self.elements.append(
                Paragraph(
                    f"<i>{self.TXT_TECH_STACK} {skill_names}</i>",
                    self.styles["HH-Duration"],
                )
            )

        self.elements.append(Spacer(1, 0.1 * cm))

    def _render_earlier_career(self, remaining: list[Experience]):
        """Render older positions as compact one-liners."""
        self.elements.append(
            Paragraph(self.TXT_EARLIER_CAREER, self.styles["HH-SectionHeader"])
        )

        for exp in remaining:
            duration = self._format_duration(exp)
            text = f"<b>{exp.company_name}</b> | {exp.position_name} | {duration}"
            self.elements.append(Paragraph(text, self.styles["HH-EarlierCareer"]))

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------

    def _add_education(self):
        """Add education section."""
        if not self.resume.edu:
            return

        self.elements.append(
            Paragraph(self.TXT_EDUCATION, self.styles["HH-SectionHeader"])
        )
        for edu in self.resume.edu:
            edu_text = f"<b>{edu.university}</b>"
            if edu.programme:
                edu_text += f", {edu.programme}"
            self.elements.append(Paragraph(edu_text, self.styles["HH-Company"]))
            self.elements.append(
                Paragraph(
                    f"{edu.degree} | {edu.year_start}-{edu.year_end}",
                    self.styles["HH-Duration"],
                )
            )

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def _add_skills_combined_visualization(self):
        """Render skills as a tag cloud with size/color proportional to frequency."""
        skill_counter = self.resume.counter_of_main_skills
        if not skill_counter:
            return

        self.elements.append(
            Paragraph(self.TXT_SKILLS, self.styles["HH-SectionHeader"])
        )
        most_common = skill_counter.most_common()
        if not most_common:
            return

        min_count, max_count = most_common[-1][1], most_common[0][1]
        parts = []
        for skill, count in most_common:
            ratio = (
                (count - min_count) / (max_count - min_count)
                if max_count != min_count
                else 0.5
            )
            font_size = 8 + (ratio * 5)
            intensity = int(80 + (ratio * 120))
            color_hex = f"#{intensity:02x}{intensity:02x}{intensity:02x}"
            bold_open = "<b>" if ratio > 0.7 else ""
            bold_close = "</b>" if ratio > 0.7 else ""
            parts.append(
                f"{bold_open}<font size='{int(font_size)}' color='{color_hex}'>"
                f"{skill.capitalize()}</font>{bold_close}"
            )

        self.elements.append(Paragraph(
            " . ".join(parts),
            ParagraphStyle(
                name="SkillCombined", parent=self.styles["Normal"],
                fontName="DejaVuSans", fontSize=self.BASE_FONT_SIZE,
                leading=13, alignment=TA_LEFT,
            ),
        ))
        self.elements.append(Spacer(1, 0.1 * cm))

    # ------------------------------------------------------------------
    # Languages
    # ------------------------------------------------------------------

    def _add_languages(self):
        """Add spoken languages section."""
        if not self.resume.spoken_languages:
            return
        self.elements.append(
            Paragraph(self.TXT_LANGUAGES, self.styles["HH-SectionHeader"])
        )
        text = "; ".join(
            f"{lang.name} - {lang.level}" for lang in self.resume.spoken_languages
        )
        self.elements.append(Paragraph(text, self.styles["HH-Responsibility"]))

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def _add_about(self):
        """Add the 'about me' section."""
        if not self.resume.about:
            return
        self.elements.append(
            Paragraph(self.TXT_ABOUT, self.styles["HH-SectionHeader"])
        )
        self.elements.append(Paragraph(self.resume.about, self.styles["HH-About"]))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_duration(self, experience: Experience) -> str:
        """Format a work period as 'start - end (X yr Y mo)'."""
        start_text = experience.work_start_date
        end_text = self.TXT_PRESENT_TIME if experience.is_still_working else experience.work_end_date

        months = experience.duration_months
        years, remaining = divmod(months, 12)
        duration_parts = []
        if years > 0:
            duration_parts.append(f"{years} {self.TXT_YEARS}")
        if remaining > 0:
            duration_parts.append(f"{remaining} {self.TXT_MONTHS}")

        return f"{start_text} - {end_text} ({' '.join(duration_parts)})"
