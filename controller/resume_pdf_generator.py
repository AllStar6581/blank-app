from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
import os
import qrcode
from io import BytesIO
from reportlab.platypus.flowables import Flowable, Preformatted
from reportlab.graphics.shapes import Drawing, Line, Circle, Rect
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor

# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont

from controller.resume_controller import ResumePage, Experience, SkillCategorized


class HHRuPDFGenerator:
    """Generates PDF resume in HH.ru style - compact and information-dense"""

    MAX_TECH_SKILLS = None
    MAX_RESPONSIBILITIES = None
    MAX_CONTACTS_IN_COLUMN = 3
    MAX_FIRST_EXPERIENCE_WITH_DESCRIPTION = 4
    MAX_FIRST_EXPERIENCE_WITH_ACTION_POINTS = 6
    MAX_FIRST_EXPERIENCE_WITH_SKILLS = None

    BASE_FONT_SIZE = 9
    # COLORS
    TITLE_TEXT_COLOR = "#1a3d6d"
    POSITION_TEXT_COLOR = "#666666"
    # TEXTS
    TXT_TECH_STACK = "Стэк:"
    TXT_WORK_EXPERIENCE = "ОПЫТ РАБОТЫ"
    TXT_EDUCATION = "ОБРАЗОВАНИЕ"
    TXT_SKILLS = "КЛЮЧЕВЫЕ НАВЫКИ"
    TXT_LANGUAGES = "ЗНАНИЕ ЯЗЫКОВ"
    TXT_ABOUT = "ОБО МНЕ"
    TXT_LOCATION = "ЛОКАЦИЯ"
    TXT_YEARS_OF_EXPERIENCE = "лет опыта"
    TXT_PRESENT_TIME = "настоящее время"
    TXT_YEARS = "г."
    TXT_MONTHS = "мес."
    TXT_SEE_DETAILED_CV = "Посмотреть резюме подробнее"

    photo_path = "static/me.jpg"

    # SIZES
    SIZE_QR_CODE_IMAGE = 2.2 * cm

    SIZE_CONTACTS_PICTURE_COLUMN = 6.1 * cm
    SIZE_CONTACTS_TEXT_COLUMN = 6.1 * cm
    SIZE_CONTACTS_QR_COLUMN = 6.1 * cm

    SIZE_PAGE_FORMAT = A4
    SIZE_PAGE_TOP_MARGIN = 0.5 * cm
    SIZE_PAGE_BOTTOM_MARGIN = 0.5 * cm
    SIZE_PAGE_LEFT_MARGIN = 1.5 * cm
    SIZE_PAGE_RIGHT_MARGIN = 1.5 * cm

    SPACER_DEFAULT = Spacer(width=1, height=0.2 * cm)

    SIZE_CONTACTS_PICTURE_IMAGE_HEIGHT = 4.1 * cm
    SIZE_CONTACTS_PICTURE_IMAGE_WIDTH = 4.1 * cm
    SIZE_CONTACTS_PICTURE_COL_WIDTH = 4.5 * cm

    # TABLESTYLES
    TABWIDTH_CONTACTS = []
    TABSTYLE_CONTACTS = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, 0), "LEFT"),  # Photo centered
            ("ALIGN", (1, 0), (1, 0), "CENTER"),  # TEXT
            ("ALIGN", (2, 0), (2, 0), "LEFT"),  # QR codes centered
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            #             ('BOX', (0, 0), (0, -1), 2, colors.red),      # Photo column - Red
            # ('BOX', (1, 0), (1, -1), 2, colors.green),    # Contacts column - Green
            # ('BOX', (2, 0), (2, -1), 2, colors.blue),     # QR column - Blue
            # # CELL BACKGROUND COLORS (light)
            # ('BACKGROUND', (0, 0), (0, -1), colors.Color(1, 0.9, 0.9)),    # Light red
            # ('BACKGROUND', (1, 0), (1, -1), colors.Color(0.9, 1, 0.9)),    # Light green
            # ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.9, 0.9, 1)),    # Light blue
            # # GRID LINES (visible grid between all cells)
            # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]
    )

    TABWIDTH_QR = [SIZE_CONTACTS_QR_COLUMN]
    TABSTYLE_QR = TableStyle(
        [
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]
    )

    TABWIDTH_CONTACTS_TEXT = [SIZE_CONTACTS_TEXT_COLUMN]
    TABSTYLE_CONTACTS_TEXT = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (0, 0), 1),
        ]
    )

    TABWIDTH_CONTACTS_PICTURE = [SIZE_CONTACTS_PICTURE_COL_WIDTH]
    TABSTYLE_CONTACTS_PICTURE = TableStyle(
        [
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (0, 0), 0),
        ]
    )

    TABWIDTH_CONTACTS_NO = [1.5 * cm, 4 * cm, 1.5 * cm, 4 * cm]
    TABSTYLE_CONTACTS_NO = TableStyle(
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("BOX", (0, 0), (0, -1), 2, colors.red),  # Photo column - Red
            ("BOX", (1, 0), (1, -1), 2, colors.green),  # Contacts column - Green
            ("BOX", (2, 0), (2, -1), 2, colors.blue),  # QR column - Blue
            # CELL BACKGROUND COLORS (light)
            ("BACKGROUND", (0, 0), (0, -1), colors.Color(1, 0.9, 0.9)),  # Light red
            ("BACKGROUND", (1, 0), (1, -1), colors.Color(0.9, 1, 0.9)),  # Light green
            ("BACKGROUND", (2, 0), (2, -1), colors.Color(0.9, 0.9, 1)),  # Light blue
            # GRID LINES (visible grid between all cells)
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ]
    )

    def __init__(self, resume):
        self.resume = resume
        self.styles = getSampleStyleSheet()
        self._register_fonts()
        self._setup_styles()
        self.elements = []

    def _register_fonts(self):
        """Register Cyrillic-compatible TrueType fonts with ReportLab"""
        try:
            # Register the regular font
            font_path_regular = "DejaVuSans.ttf"
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path_regular))

            # Register the bold variant (using the same file for simplicity)
            # For better typography, use a separate bold font file if available
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", font_path_regular))

            # Set as the default font family
            pdfmetrics.registerFontFamily(
                "DejaVuSans",
                normal="DejaVuSans",
                bold="DejaVuSans-Bold",
            )
        except Exception as e:
            print(
                f"Warning: Could not register custom fonts. Using default. Error: {e}"
            )
            # Fallback to standard fonts (may not support Cyrillic)

    def _setup_styles(self):
        """Setup HH.ru specific styles"""
        # set up font
        # pdfmetrics.registerFont(TTFont('Warownia', 'path/to/font.ttf'))

        # Title style (for name)
        self.styles.add(
            ParagraphStyle(
                name="HH-Title",
                parent=self.styles["Heading1"],
                fontSize=self.BASE_FONT_SIZE+7,
                textColor=colors.HexColor(self.TITLE_TEXT_COLOR),
                spaceAfter=6,
                alignment=TA_LEFT,
                fontName="DejaVuSans-Bold",
            )
        )

        # Position style
        self.styles.add(
            ParagraphStyle(
                name="HH-Position",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE+3,
                textColor=colors.HexColor(self.POSITION_TEXT_COLOR),
                spaceAfter=12,
                alignment=TA_LEFT,
                # fontName="Arial",
                fontName="DejaVuSans-Bold",
            )
        )

        # Section header style
        self.styles.add(
            ParagraphStyle(
                name="HH-SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=self.BASE_FONT_SIZE+3,
                textColor=colors.HexColor("#1a3d6d"),
                spaceAfter=6,
                spaceBefore=12,
                leftIndent=0,
                borderLeft=1,
                borderLeftColor=colors.HexColor("#1a3d6d"),
                borderLeftWidth=3,
                paddingLeft=6,
                # fontName="Arial",
                fontName="DejaVuSans-Bold",
            )
        )

        # Company style
        self.styles.add(
            ParagraphStyle(
                name="HH-Company",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE+2,
                textColor=colors.HexColor("#333333"),
                spaceAfter=2,
                leftIndent=0,
                # fontName="Arial",
                fontName="DejaVuSans-Bold",
            )
        )

        # Position duration style
        self.styles.add(
            ParagraphStyle(
                name="HH-Duration",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE,
                textColor=colors.HexColor("#666666"),
                spaceAfter=6,
                leftIndent=0,
                # fontName="Arial",
                fontName="DejaVuSans",
            )
        )

        # Responsibility style
        self.styles.add(
            ParagraphStyle(
                name="HH-Responsibility",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE,
                textColor=colors.HexColor("#444444"),
                spaceAfter=3,
                leftIndent=12,
                bulletIndent=12,
                # fontName="Arial",
                fontName="DejaVuSans",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="HH-JobDescription",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE,
                textColor=colors.HexColor("#444444"),
                spaceAfter=3,
                leftIndent=12,
                bulletIndent=12,
                # fontName="Arial",
                fontName="DejaVuSans",
            )
        )

        # Contact style
        self.styles.add(
            ParagraphStyle(
                name="HH-Contact",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE,
                textColor=colors.HexColor("#333333"),
                spaceAfter=2,
                # fontName="Arial",
                fontName="DejaVuSans",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="HH-About",
                parent=self.styles["Normal"],
                fontSize=self.BASE_FONT_SIZE,
                textColor=colors.HexColor("#444444"),
                spaceAfter=3,
                leftIndent=12,
                bulletIndent=12,
                # fontName="Arial",
                fontName="DejaVuSans",
            )
        )

    def generate(self, output_path: str):
        """Generate and save the PDF document"""
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
        """Build all PDF content"""
        self._add_header()
        # self._add_contacts()

        self._add_contacts_with_photo_and_qr()

        self._add_experience()
        self._add_education()
        # self._add_skills()
        self._add_skills_combined_visualization()
        self._add_languages()
        self._add_about()

    def _add_header(self):
        """Add name and position in HH.ru style"""
        # Name
        self.elements.append(
            Paragraph(
                f"<b>{self.resume.full_name.upper()}</b>", self.styles["HH-Title"]
            )
        )

        # Position with total experience
        total_exp = self.resume.total_experience_months_wide / 12
        exp_text = (
            f", {total_exp:.1f} {self.TXT_YEARS_OF_EXPERIENCE}" if total_exp > 0 else ""
        )
        position_text = f"{self.resume.position}{exp_text}"

        self.elements.append(Paragraph(position_text, self.styles["HH-Position"]))

        self.elements.append(Spacer(1, 0.2 * cm))
        # self.elements.append(self.SPACER_DEFAULT)

    def _add_contacts_with_photo_and_qr(self):
        """Add contacts with photo on left and QR codes on right"""
        if not hasattr(self, "resume"):
            return

        # Create a 3-column table: Photo | Contacts | QR Codes
        table_data = []

        # Left column: Photo
        photo_cell = self._create_photo_cell()

        # Middle column: Contacts list
        contacts_cell = self._create_contacts_cell()

        # Right column: QR Codes
        qr_cell = self._create_qr_codes_cell()

        # Create table row
        table_data.append([photo_cell, contacts_cell, qr_cell])

        # Create and style the table
        col_widths = [
            self.SIZE_CONTACTS_PICTURE_COLUMN,
            self.SIZE_CONTACTS_TEXT_COLUMN,
            self.SIZE_CONTACTS_QR_COLUMN,
        ]  # Adjust as needed
        table = Table(table_data, colWidths=col_widths)

        # Style the table
        table.setStyle(self.TABSTYLE_CONTACTS)

        self.elements.append(table)
        self.elements.append(Spacer(1, 0.3 * cm))
        # self.elements.append(self.SPACER_DEFAULT)

    def _create_photo_cell(self):
        """Create cell with profile photo"""
        from reportlab.platypus import Image

        # Check if photo exists
        if not self.photo_path or not os.path.exists(self.photo_path):
            # Return empty cell or placeholder
            return Paragraph("", self.styles["Normal"])

        try:
            # Load and resize photo
            img = Image(
                self.photo_path,
                width=self.SIZE_CONTACTS_PICTURE_IMAGE_WIDTH,
                height=self.SIZE_CONTACTS_PICTURE_IMAGE_HEIGHT,
            )

            # Optional: Make it circular (adds complexity but looks professional)
            # You would need to pre-process the image or use a mask

            # Create a small table to hold the photo with some padding
            photo_table = Table([[img]], colWidths=self.TABWIDTH_CONTACTS_PICTURE)
            photo_table.setStyle(self.TABSTYLE_CONTACTS_PICTURE)

            return photo_table

        except Exception as e:
            print(f"Warning: Could not load photo: {e}")
            return Paragraph("", self.styles["Normal"])

    def _create_contacts_cell(self):
        """Create cell with contact information"""
        contact_items = []

        # Build contact paragraphs
        # for contact in self.resume.contacts:
        #     if contact.type.value == 'email':
        #         display = f"✉️ {contact.display_text}"
        #     elif contact.type.value == 'phone':
        #         display = f"📱 {contact.display_text}"
        #     elif contact.type.value == 'linkedin':
        #         display = f"💼 LinkedIn"
        #     elif contact.type.value == 'github':
        #         display = f"👨‍💻 GitHub"
        #     elif contact.type.value == 'location':
        #         display = f"📍 {contact.display_text}"
        #     else:
        #         display = f"• {contact.display_text}"

        #     contact_para = Paragraph(
        #         f"{display}",
        #         self.styles['HH-Contact']
        #     )
        #     contact_items.append(contact_para)

        for contact in self.resume.contacts:
            contact_items.append(
                [
                    # Paragraph(f"<b>{contact.type.value.title()}:</b>", self.styles['HH-Contact']),
                    Paragraph(contact.link, self.styles["HH-Contact"])
                ]
            )

        contact_items.insert(0, Paragraph(self.resume.tel, self.styles["HH-Contact"]))
        contact_items.insert(0, Paragraph(self.resume.email, self.styles["HH-Contact"]))

        # Create a table to hold all contact items
        contact_table_data = [[item] for item in contact_items]
        contact_table = Table(contact_table_data, colWidths=self.TABWIDTH_CONTACTS_TEXT)

        contact_table.setStyle(self.TABSTYLE_CONTACTS_TEXT)

        return contact_table

    def _make_clickable_text(self, url, text, font_size=BASE_FONT_SIZE):
        """Create text that looks and acts like a clickable link in PDF"""
        # Style for clickable links
        link_style = ParagraphStyle(
            name="QR-Link",
            parent=self.styles["Normal"],
            fontName="DejaVuSans",
            fontSize=font_size,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0066CC"),  # Blue color for links
            leading=font_size + 1,
            spaceAfter=0,
        )

        # The magic: <link> tag makes it clickable, <u> underlines it
        link_html = f"<link href='{url}'><u>{text}</u></link>"

        return Paragraph(link_html, link_style)

    def _create_qr_codes_cell(self):
        """Create cell with QR codes and descriptions"""
        qr_items = []

        # Define which contacts get QR codes
        qr_data_list = [
            # {
            #     'data': self.resume.email,
            #     'title': 'Email',
            #     'description': 'Send me an email'
            # } if self.resume.email else None,
            # {
            #     'data': self._get_contact_by_type('linkedin'),
            #     'title': 'LinkedIn',
            #     'description': 'View profile'
            # },
            # {
            #     'data': self._get_contact_by_type('github'),
            #     'title': 'GitHub',
            #     'description': 'See my code'
            # },
            {
                "data": self.resume.website,
                "title": self.resume.website,
                "description": self.TXT_SEE_DETAILED_CV,
            }
        ]

        # Filter out None values and limit to 3 QR codes
        qr_data_list = [item for item in qr_data_list if item and item["data"]][:3]

        for qr_data in qr_data_list:
            # Generate QR code image
            qr_image = self._generate_qr_code(
                qr_data["data"], size=self.SIZE_QR_CODE_IMAGE
            )

            if qr_image:
                # Create a small table for each QR code with description
                qr_table = Table(
                    [
                        [qr_image],
                        [
                            Paragraph(
                                f"<b>{qr_data['title']}</b>",
                                ParagraphStyle(
                                    name="QR-Title",
                                    parent=self.styles["Normal"],
                                    fontName="DejaVuSans-Bold",
                                    fontSize=self.BASE_FONT_SIZE-2,
                                    alignment=TA_CENTER,
                                    textColor=colors.HexColor("#333333"),
                                ),
                            )
                        ],
                        [
                            Paragraph(
                                f"{qr_data['description']}",
                                ParagraphStyle(
                                    name="QR-Desc",
                                    parent=self.styles["Normal"],
                                    fontName="DejaVuSans",
                                    fontSize=self.BASE_FONT_SIZE-3,
                                    alignment=TA_CENTER,
                                    textColor=colors.HexColor("#666666"),
                                ),
                            )
                        ],
                    ],
                    colWidths=self.TABWIDTH_QR,
                )

                qr_table.setStyle(self.TABSTYLE_QR)

                qr_items.append(qr_table)

        # Arrange QR codes horizontally if we have 2 or fewer
        if len(qr_items) <= 2:
            # qr_row = Table([qr_items], colWidths=[4*cm/len(qr_items)]*len(qr_items))
            qr_row = Table([qr_items], colWidths=[1 * cm])
            return qr_row
        else:
            # Stack vertically if we have 3
            qr_stack = Table([[item] for item in qr_items], colWidths=[4 * cm])
            return qr_stack

    def _get_contact_by_type(self, contact_type: str) -> str:
        """Get contact value by type"""
        for contact in self.resume.contacts:
            if contact.type.value == contact_type:
                return contact.value
        return None

    def _generate_qr_code(self, data: str, size=1.5 * cm):
        """Generate a QR code image from data"""
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=9,
                border=1,
            )
            qr.add_data(data)
            qr.make(fit=True)

            # Create image
            qr_img = qr.make_image(fill_color="black", back_color="white")

            # Convert to bytes
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            # Create ReportLab Image
            from reportlab.platypus import Image

            return Image(img_buffer, width=size, height=size)

        except Exception as e:
            print(f"Warning: Could not generate QR code for {data[:20]}...: {e}")
            return None

    def _add_contacts(self):
        """Add contacts in a compact format"""
        if not self.resume.contacts:
            return

        # Create contact table
        contact_data = []
        for contact in self.resume.contacts:
            contact_data.append(
                [
                    # Paragraph(f"<b>{contact.type.value.title()}:</b>", self.styles['HH-Contact']),
                    Paragraph(contact.text, self.styles["HH-Contact"])
                ]
            )

        # Split into two columns if enough contacts
        if len(contact_data) > self.MAX_CONTACTS_IN_COLUMN:
            mid = len(contact_data) // 2
            contact_table_data = []
            for i in range(max(len(contact_data) - mid, mid)):
                row = []
                if i < len(contact_data) - mid:
                    row.extend(contact_data[i])
                else:
                    row.extend(["", ""])

                if i < mid:
                    row.extend(contact_data[i + mid])
                else:
                    row.extend(["", ""])

                contact_table_data.append(row)
        else:
            contact_table_data = contact_data

        contact_table = Table(contact_table_data, colWidths=self.TABWIDTH_CONTACTS_NO)
        contact_table.setStyle(self.TABSTYLE_CONTACTS_NO)

        self.elements.append(contact_table)
        self.elements.append(Spacer(1, 0.3 * cm))
        # self.elements.append(self.SPACER_DEFAULT)

    def _add_experience(self):
        """Add work experience in HH.ru compact format"""
        if not self.resume.exp:
            return

        self.elements.append(
            Paragraph(
                # "WORK EXPERIENCE",
                self.TXT_WORK_EXPERIENCE,
                self.styles["HH-SectionHeader"],
            )
        )

        is_add_description = True
        is_add_action_points = True
        is_add_skills = True
        for index, exp in enumerate(self.resume.ordered_experience):
            is_add_description = self.MAX_FIRST_EXPERIENCE_WITH_DESCRIPTION is None or (
                index + 1 < self.MAX_FIRST_EXPERIENCE_WITH_DESCRIPTION
            )
            is_add_action_points = (
                self.MAX_FIRST_EXPERIENCE_WITH_ACTION_POINTS is None
                or (index + 1 < self.MAX_FIRST_EXPERIENCE_WITH_ACTION_POINTS)
            )
            is_add_skills = self.MAX_FIRST_EXPERIENCE_WITH_SKILLS is None or (
                index + 1 < self.MAX_FIRST_EXPERIENCE_WITH_SKILLS
            )

            # Company and location
            company_text = f"<b>{exp.company_name}</b>"
            if exp.location:
                company_text += f" ({exp.location})"

            self.elements.append(Paragraph(company_text, self.styles["HH-Company"]))

            # Position and duration
            duration = self._format_duration_hh(exp)
            position_text = f"{exp.position_name} | {duration}"

            self.elements.append(Paragraph(position_text, self.styles["HH-Duration"]))

            if is_add_description and exp.description:
                self.elements.append(
                    Paragraph(exp.description, self.styles["HH-JobDescription"])
                )

            # Responsibilities (compact)
            if is_add_action_points:
                for responsibility in exp.responsibilities[
                    : self.MAX_RESPONSIBILITIES
                ]:  # Limit to 4 most important
                    self.elements.append(
                        Paragraph(
                            f"• {responsibility}", self.styles["HH-Responsibility"]
                        )
                    )

            # Skills used
            if is_add_skills and exp.skills:
                skills_text = ", ".join(
                    exp.skills[: self.MAX_TECH_SKILLS]
                )  # Limit skills display
                skills_para = Paragraph(
                    f"<i>{self.TXT_TECH_STACK} {skills_text}</i>",
                    self.styles["HH-Duration"],
                )
                self.elements.append(skills_para)

            self.elements.append(Spacer(1, 0.2 * cm))
            # self.elements.append(self.SPACER_DEFAULT)

    def _add_education(self):
        """Add education section"""
        if not self.resume.edu:
            return

        self.elements.append(
            Paragraph(self.TXT_EDUCATION, self.styles["HH-SectionHeader"])
        )

        for edu in self.resume.edu:
            # University and degree
            edu_text = f"<b>{edu.university}</b>"
            if edu.programme:
                edu_text += f", {edu.programme}"

            self.elements.append(Paragraph(edu_text, self.styles["HH-Company"]))

            # Degree and years
            degree_text = f"{edu.degree} | {edu.year_start}-{edu.year_end}"
            self.elements.append(Paragraph(degree_text, self.styles["HH-Duration"]))

            if edu.website:
                self.elements.append(
                    Paragraph(str(edu.website), self.styles["HH-Responsibility"])
                )

            self.elements.append(Spacer(1, 0.1 * cm))
            # self.elements.append(self.SPACER_DEFAULT)

    def _add_skills_combined_visualization(self):
        """Add skills with combined size, color, and boldness indicating frequency"""
        skill_counter = self.resume.counter_of_main_skills

        if not skill_counter:
            return

        self.elements.append(
            Paragraph(self.TXT_SKILLS, self.styles["HH-SectionHeader"])
        )

        most_common_skills = skill_counter.most_common()  # Optimal number for one line

        if not most_common_skills:
            return

        min_count, max_count = most_common_skills[-1][1], most_common_skills[0][1]

        skill_html_parts = []
        for skill, count in most_common_skills:
            # Calculate visual properties
            ratio = (
                (count - min_count) / (max_count - min_count)
                if max_count != min_count
                else 0.5
            )

            # Font size: 9-13pt
            font_size = 8 + (ratio * 5)

            # Color: lighter to darker (gray scale)
            color_intensity = int(80 + (ratio * 120))  # 80-200
            # color_intensity = int(200 - (ratio * 120))  # 80-200

            color_hex = (
                f"#{color_intensity:02x}{color_intensity:02x}{color_intensity:02x}"
            )

            # Only bold for top skills
            bold_tag = "<b>" if ratio > 0.7 else ""
            bold_close = "</b>" if ratio > 0.7 else ""

            skill_html_parts.append(
                f"{bold_tag}<font size='{int(font_size)}' color='{color_hex}'>{skill.capitalize()}</font>{bold_close}"
            )

        skills_para = Paragraph(
            # " ' ".join(skill_html_parts),
            " . ".join(skill_html_parts),
            ParagraphStyle(
                name="SkillCombined",
                parent=self.styles["Normal"],
                fontName="DejaVuSans",
                fontSize=self.BASE_FONT_SIZE,
                leading=13,
                alignment=TA_LEFT,
            ),
        )

        self.elements.append(skills_para)
        self.elements.append(Spacer(1, 0.2 * cm))

    def _add_skills(self):
        """Add skills in compact format"""
        if not self.resume.all_skills_set:
            return

        self.elements.append(
            Paragraph(
                # "SKILLS",
                self.TXT_SKILLS,
                self.styles["HH-SectionHeader"],
            )
        )

        # Group by category
        skills_by_category = self.resume.all_skills_set
        # skills_by_category = {}
        # for skill in self.resume.all_skills_set:  # Only show primary skills
        #     if skill.category not in skills_by_category:
        #         skills_by_category[skill.category] = []
        #     skills_by_category[skill.category].append(skill)

        # Create skills text
        skills_text_parts = [f"<b>{skill}</b> " for skill in skills_by_category]
        # skills_text_parts = []
        # for category, skills in skills_by_category.items():
        #     skill_names = [skill.name for skill in skills]
        #     skills_text_parts.append(f"<b>{category.title()}</b>: {', '.join(skill_names)}")

        skills_para = Paragraph(
            "; ".join(skills_text_parts), self.styles["HH-Responsibility"]
        )
        self.elements.append(skills_para)
        self.elements.append(Spacer(1, 0.2 * cm))
        # self.elements.append(self.SPACER_DEFAULT)

    def _add_languages(self):
        """Add languages section"""
        if not self.resume.spoken_languages:
            return

        self.elements.append(
            Paragraph(
                # "LANGUAGES",
                self.TXT_LANGUAGES,
                self.styles["HH-SectionHeader"],
            )
        )

        languages_text = "; ".join(
            f"{lang.name} - {lang.level}" for lang in self.resume.spoken_languages
        )

        languages_para = Paragraph(languages_text, self.styles["HH-Responsibility"])
        self.elements.append(languages_para)

    def _format_duration_hh(self, experience: Experience) -> str:
        """Format duration in HH.ru style"""
        start_text = experience.work_start_date

        if experience.current:
            end_text = self.TXT_PRESENT_TIME
        else:
            end_text = experience.work_end_date

        duration_months = experience.duration_months
        years = duration_months // 12
        months = duration_months % 12

        duration_text = ""
        if years > 0:
            # duration_text += f"{years} year{'s' if years > 1 else ''}"
            duration_text += f"{years} {self.TXT_YEARS}"
        if months > 0:
            if duration_text:
                duration_text += " "
            duration_text += f"{months} {self.TXT_MONTHS}"

        return f"{start_text} - {end_text} ({duration_text})"

    def _add_about(self):
        if not self.resume.about:
            return

        self.elements.append(
            Paragraph(
                self.TXT_ABOUT,
                self.styles["HH-SectionHeader"],
            )
        )

        about_text = self.resume.about

        about_para = Paragraph(about_text, self.styles["HH-About"])
        self.elements.append(about_para)
