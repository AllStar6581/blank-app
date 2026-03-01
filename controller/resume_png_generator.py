"""PNG resume generator using Matplotlib for visual layout and vCard QR codes."""

import os

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import qrcode
import vobject
from matplotlib import font_manager as fm
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

from controller.resume_controller import ResumePage


class PdfPage:
    """Generates a single-page PNG resume with a visual layout and embedded QR code."""

    resume_page: ResumePage

    primary_color = "#00897b"
    secondary_color = "#4a148c"
    background_color = "#ffffff"
    black_color = "#000000"
    white_color = "#ffffff"

    def __init__(
        self,
        resume_page: ResumePage,
        palette: dict | None = None,
    ) -> None:
        self.resume_page = resume_page
        if palette:
            for key in ("primary_color", "secondary_color", "background_color",
                        "black_color", "white_color"):
                if palette.get(key):
                    setattr(self, key, palette[key])

        self.qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=0,
        )

    def create_vcard_data(self) -> str:
        """Generate a vCard string from the resume data."""
        vcard = vobject.vCard()
        vcard.add("n")
        vcard.n.value = vobject.vcard.Name(
            family=self.resume_page.last_name, given=self.resume_page.first_name
        )
        vcard.add("fn")
        vcard.fn.value = self.resume_page.name
        vcard.add("email")
        vcard.email.value = self.resume_page.email
        vcard.email.type_param = "INTERNET"
        vcard.add("title")
        vcard.title.value = self.resume_page.expected_position
        vcard.add("url")
        vcard.url.value = self.resume_page.website
        vcard.url.type_param = "INTERNET"
        return vcard.serialize()

    def create_qrcode_image(self, data_string: str, img_output_file_path: str):
        """Generate and save a QR code PNG image."""
        self.qr.add_data(data_string)
        self.qr.make(fit=True)
        img = self.qr.make_image(
            fill_color=self.primary_color, back_color=self.white_color
        )
        img.save(img_output_file_path)
        return img

    def create_resume_png(self, img_output_file_path: str):
        """Render the full resume as a PNG image with matplotlib."""
        font_path = os.path.join("fonts", "Warownia.otf")
        font_prop = fm.FontProperties(fname=font_path)
        fm.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = font_prop.get_name()

        fig, ax = plt.subplots(figsize=(8.5, 11), facecolor=self.white_color)
        ax.axvline(x=0.5, ymin=0, ymax=1, color=self.secondary_color, alpha=0.0, linewidth=50)
        plt.axvline(x=0.99, ymin=0, color=self.primary_color, alpha=1, linewidth=300)
        plt.axhline(y=0.835, xmin=0, xmax=1, color=self.white_color, linewidth=3)

        exp_position = (0.02, 0.891)
        exp_length = 6

        plt.axvline(
            x=0.009,
            ymin=exp_position[1],
            ymax=exp_position[1] - exp_length * 0.1 - 0.08,
            color=self.primary_color, alpha=1, linewidth=2,
        )
        plt.axis("off")

        # Name and position
        plt.annotate(
            self.resume_page.name, (0.01, 0.99),
            weight="bold", fontsize=20, color=self.primary_color,
        )
        plt.annotate(
            self.resume_page.expected_position, (0.02, 0.96),
            weight="regular", color=self.black_color, fontsize=14,
        )

        # Languages
        plt.annotate(
            "\n".join(f"{x.name}:{x.level}" for x in self.resume_page.spoken_languages),
            (0.68, 0.849), weight="regular", fontsize=8, color=self.background_color,
        )

        # Experience header
        overall_months = self.resume_page.total_experience_months
        months_label = f" {overall_months % 12} mo" if overall_months % 12 else ""
        plt.annotate(
            f"EXPERIENCE | {overall_months // 12} yr.{months_label} total",
            (0.02, 0.920), weight="bold", fontsize=10, color=self.primary_color,
        )

        # Experience entries
        for experience in self.resume_page.ordered_experience[:exp_length]:
            plt.annotate(".", (-0.00, exp_position[1]),
                         weight="bold", fontsize=30, color=self.primary_color)
            plt.annotate(experience.company_name,
                         (exp_position[0] + 0.01, exp_position[1]),
                         weight="bold", color=self.black_color, fontsize=10)
            plt.annotate(experience.position_name,
                         (exp_position[0], exp_position[1] - 0.019),
                         weight="bold", fontsize=10, color=self.secondary_color)

            end_label = (
                "Still working" if experience.is_still_working
                else experience.work_end_date_object.strftime("%B %Y")
            )
            years_str = f"{experience.total_time_delta.years} yr" if experience.total_time_delta.years else ""
            months_str = f"{experience.total_time_delta.months} mo" if experience.total_time_delta.months else ""
            plt.annotate(
                f"{experience.work_start_date_object.strftime('%B %Y')} - {end_label}  | {years_str} {months_str}",
                (exp_position[0], exp_position[1] - 0.036),
                weight="regular", fontsize=9, color=self.black_color, alpha=0.6,
            )

            action_points = experience.action_points[:4]
            description = "\n" + "\n".join(f"- {pt}" for pt in action_points)
            plt.annotate(
                description,
                (exp_position[0], exp_position[1] - 0.021 * (len(action_points) + 0.85) - 0.032),
                weight="regular", color=self.black_color, fontsize=8,
            )
            exp_position = (
                exp_position[0],
                exp_position[1] - 0.108 - 0.019 - 0.019 * (len(experience.action_points) - 4.2) - 0.016,
            )

        # Education
        plt.annotate("EDUCATION", (0.02, 0.185),
                     weight="bold", fontsize=10, color=self.primary_color)

        edu_position = (0.02, 0.155)
        edu_padding = -0.005
        for education in self.resume_page.edu[:3]:
            plt.annotate(f"{education.university}, ", edu_position,
                         weight="bold", color=self.black_color, fontsize=10)
            plt.annotate(education.degree,
                         (edu_position[0], edu_position[1] - 0.015 + edu_padding),
                         weight="bold", fontsize=9, color=self.secondary_color)
            plt.annotate(f"{education.year_start} - {education.year_end}",
                         (edu_position[0], edu_position[1] - 0.030 + edu_padding),
                         weight="regular", color=self.black_color, fontsize=9, alpha=0.6)
            plt.annotate(education.programme,
                         (edu_position[0], edu_position[1] - 0.045 + edu_padding),
                         weight="regular", color=self.black_color, fontsize=9)
            edu_position = (edu_position[0], edu_position[1] - 0.09 + edu_padding)

        # Skills sidebar
        plt.annotate("SKILLS", (0.7, 0.80),
                     weight="bold", fontsize=10, color=self.background_color)
        skills_text = "\n".join(
            s[0].capitalize()
            for s in self.resume_page.counter_of_main_skills.most_common(16)
        )
        plt.annotate(skills_text, (0.7, 0.48),
                     weight="regular", fontsize=10, color=self.background_color)

        # Profile photo
        arr_photo = mpimg.imread("static/me.jpg")
        imagebox = OffsetImage(arr_photo, zoom=0.086)
        ab = AnnotationBbox(
            imagebox, (0.90, 0.92), pad=0.2,
            bboxprops=dict(edgecolor=self.white_color, facecolor=self.white_color, alpha=1.0),
        )
        ax.add_artist(ab)

        # QR code
        plt.annotate("ADD MY CONTACT\n& SEE MORE DETAILS:", (0.7, 0.27),
                     weight="bold", fontsize=10, color=self.background_color)
        self.create_qrcode_image(self.create_vcard_data(), "qrcode.png")
        arr_code = mpimg.imread("qrcode.png")
        qr_box = OffsetImage(arr_code, zoom=0.50)
        qr_ab = AnnotationBbox(
            qr_box, (0.83, 0.15),
            bboxprops=dict(edgecolor=self.white_color, facecolor=self.white_color, alpha=1.0),
        )
        ax.add_artist(qr_ab)

        plt.annotate(self.resume_page.website or "", (0.7, 0.017),
                     weight="bold", fontsize=10, color=self.background_color)

        return plt.savefig(img_output_file_path, dpi=300, bbox_inches="tight")
