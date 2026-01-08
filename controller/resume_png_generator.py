from controller.resume_controller import ResumePage
import vobject
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from matplotlib import font_manager as fm
import qrcode
import os


class PdfPage:
    resume_page: ResumePage

    # primary_color = "#3E313E"
    # primary_color = "#004d40"
    primary_color = "#00897b"
    # secondary_color = "#007ACC"
    # secondary_color = "#d500f9"
    secondary_color = "#4a148c"
    background_color = "#ffffff"
    black_color = "#000000"
    white_color = "#ffffff"

    def __init__(
        self,
        resume_page: ResumePage,
        pallette={
            "primary_color": "#00897b",
            "secondary_color": "#4a148c",
            "background_color": "#ffffff",
            "black_color": "#000000",
            "white_color": "#ffffff",
        },
    ) -> None:
        self.resume_page = resume_page
        if pallette.get("primary_color"):
            self.primary_color = pallette.get("primary_color")
        if pallette.get("secondary_color"):
            self.secondary_color = pallette.get("secondary_color")
        if pallette.get("background_color"):
            self.background_color = pallette.get("background_color")
        if pallette.get("black_color"):
            self.black_color = pallette.get("black_color")
        if pallette.get("white_color"):
            self.white_color = pallette.get("white_color")
        self.qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=0,
        )

    def create_vcard_data(self):
        vcard_object = vobject.vCard()
        vcard_object.add("n")
        vcard_object.n.value = vobject.vcard.Name(
            family=self.resume_page.last_name, given=self.resume_page.first_name
        )
        vcard_object.add("fn")
        vcard_object.fn.value = self.resume_page.name
        vcard_object.add("email")
        vcard_object.email.value = self.resume_page.email
        vcard_object.email.type_param = "INTERNET"
        vcard_object.add("title")
        vcard_object.title.value = self.resume_page.expected_position
        # vcard_object.title.type_param = 'TEXT'

        vcard_object.add("url")
        vcard_object.url.value = self.resume_page.website
        vcard_object.url.type_param = "INTERNET"
        return vcard_object.serialize()

    def create_qrcode_image(self, data_string: str, img_output_file_path: str):
        self.qr.add_data(data_string)
        self.qr.make(fit=True)
        # img = self.qr.make_image(fill_color=self.primary_color, back_color=self.background_color)
        img = self.qr.make_image(
            fill_color=self.primary_color, back_color=self.white_color
        )
        img.save(img_output_file_path)
        return img

    def create_resume_png(self, img_output_file_path: str):
        # plt.rcParams['font.family'] = 'sans-serif'
        # font_path = "fonts/Warownia.otf"
        # font_prop = fm.FontProperties(fname=font_path)
        # plt.rcParams['font.family'] = font_prop.get_name()
        font_path = os.path.join("fonts", "Warownia.otf")
        font_prop = fm.FontProperties(fname=font_path)
        fm.fontManager.addfont(font_path)
        plt.rcParams["font.family"] = font_prop.get_name()
        # plt.rcParams['font.family'] = ["sans-serif"]
        # plt.rcParams['font.sans-serif'] = 'STIXGeneral'
        # plt.rcParams['font.sans-serif'] = 'Helvetica'
        # plt.rcParams['font.sans-serif'] = font_prop.get_name()

        # plt.rcParams['axes.facecolor'] = 'none'
        # plt.rcParams['axes.facecolor'] = 'red'
        fig, ax = plt.subplots(figsize=(8.5, 11), facecolor=self.white_color)
        # ax.set_facecolor('white')

        # ax.set_facecolor('xkcd:salmon')
        # fig, ax = plt.subplots(figsize=(11.5, 14))

        ax.axvline(
            x=0.5, ymin=0, ymax=1, color=self.secondary_color, alpha=0.0, linewidth=50
        )
        # plt.axvline(x=.99, color='#000000', alpha=0.5, linewidth=300)
        plt.axvline(x=0.99, ymin=0, color=self.primary_color, alpha=1, linewidth=300)
        plt.axhline(y=0.835, xmin=0, xmax=1, color=self.white_color, linewidth=3)

        exp_position = (0.02, 0.891)
        exp_length = 6

        plt.axvline(
            x=0.009,
            ymin=exp_position[1],
            ymax=exp_position[1] - exp_length * 0.1 - 0.08,
            color=self.primary_color,
            alpha=1,
            linewidth=2,
        )
        # plt.add_patch(plt.Circle((0.5, 0.5), 0.2, color='blue'))
        # plt.axhline(y=.88, xmin=0, xmax=1, color=background_color, linewidth=3)
        # set background color
        # ax.set_facecolor(self.white_color)

        # ax.set_facecolor('red')
        # remove axes
        plt.axis("off")
        # add text
        plt.annotate(
            self.resume_page.name,
            (0.01, 0.99),
            weight="bold",
            fontsize=20,
            color=self.primary_color,
        )
        plt.annotate(
            self.resume_page.expected_position,
            (0.02, 0.96),
            weight="regular",
            color=self.black_color,
            fontsize=14,
        )
        plt.annotate(
            "\n".join(
                [x.name + ":" + x.level for x in self.resume_page.spoken_languages]
            ),
            (0.68, 0.849),
            weight="regular",
            fontsize=8,
            color=self.background_color,
        )

        overall_months = self.resume_page.total_experience_months
        plt.annotate(
            f"EXPERIENCE | {overall_months // 12} yr.{overall_months % 12 if overall_months % 12 else ''}{' mo' if overall_months % 12 else ''} total",
            (0.02, 0.920),
            weight="bold",
            fontsize=10,
            color=self.primary_color,
        )

        for experience in self.resume_page.ordered_experience[:exp_length]:
            # plt.annotate(experience.company_name, exp_position, weight='bold', fontsize=10, color=self.secondary_color)
            # plt.annotate("", (-0.001, exp_position[1]), weight='bold', fontsize=10, color=self.primary_color)
            plt.annotate(
                ".",
                (-0.00, exp_position[1]),
                weight="bold",
                fontsize=30,
                color=self.primary_color,
            )
            plt.annotate(
                experience.company_name,
                (exp_position[0] + 0.01, exp_position[1]),
                weight="bold",
                color=self.black_color,
                fontsize=10,
            )
            plt.annotate(
                experience.position_name,
                (exp_position[0], exp_position[1] - 0.019),
                weight="bold",
                fontsize=10,
                color=self.secondary_color,
            )
            plt.annotate(
                f"{experience.work_start_date_object.strftime('%B %Y')} - {experience.work_end_date_object.strftime('%B %Y') if not experience.is_still_working else 'Still working'}  | {str(experience.total_time_delta.years) +' yr' if experience.total_time_delta.years else ''} {str(experience.total_time_delta.months) +' mo' if experience.total_time_delta.months else ''}",
                (exp_position[0], exp_position[1] - 0.019 - 0.017),
                weight="regular",
                fontsize=9,
                color=self.black_color,
                alpha=0.6,
            )
            description = "\n"
            action_points = experience.action_points[:4]
            for point in action_points:
                description += f"- {point}\n"
            plt.annotate(
                description,
                (
                    exp_position[0] + 0.0,
                    exp_position[1] - 0.021 * (len(action_points) + 0.85) - 0.032,
                ),
                weight="regular",
                color=self.black_color,
                fontsize=8,
            )
            exp_position = (exp_position[0], exp_position[1] - 0.108 - 0.019)
            exp_position = (
                exp_position[0],
                exp_position[1]
                - 0.019 * (len(experience.action_points) - 4.2)
                + -0.016,
            )

        plt.annotate(
            "EDUCATION",
            (0.02, 0.185),
            weight="bold",
            fontsize=10,
            color=self.primary_color,
        )

        edu_position = (0.02, 0.155)
        edu_padding = -0.005
        for education in self.resume_page.edu[:3]:
            plt.annotate(
                education.university + ", ",
                edu_position,
                weight="bold",
                color=self.black_color,
                fontsize=10,
            )
            plt.annotate(
                education.degree,
                (edu_position[0], edu_position[1] - 0.015 + edu_padding),
                weight="bold",
                fontsize=9,
                color=self.secondary_color,
            )
            plt.annotate(
                str(education.year_start) + " - " + str(education.year_end),
                (edu_position[0], edu_position[1] - 0.030 + edu_padding),
                weight="regular",
                color=self.black_color,
                fontsize=9,
                alpha=0.6,
            )
            plt.annotate(
                education.programme,
                (edu_position[0], edu_position[1] - 0.045 + edu_padding),
                weight="regular",
                color=self.black_color,
                fontsize=9,
            )
            edu_position = (edu_position[0], edu_position[1] - 0.09 + edu_padding)

        plt.annotate(
            "SKILLS",
            (0.7, 0.80),
            weight="bold",
            fontsize=10,
            color=self.background_color,
        )
        plt.annotate(
            "\n".join(
                [
                    f"{x[0].capitalize()}"
                    for x in self.resume_page.counter_of_main_skills.most_common(16)
                ]
            ),
            (0.7, 0.48),
            weight="regular",
            fontsize=10,
            color=self.background_color,
        )

        # arr_profile_photo = mpimg.imread('static/me_2.png')
        arr_profile_photo = mpimg.imread("static/me.jpg")
        imagebox_1 = OffsetImage(arr_profile_photo, zoom=0.086)
        ab_1 = AnnotationBbox(
            imagebox_1,
            (0.90, 0.92),
            pad=0.2,
            bboxprops=dict(
                edgecolor=self.white_color, facecolor=self.white_color, alpha=1.0
            ),
        )
        ax.add_artist(ab_1)

        plt.annotate(
            f"ADD MY CONTACT\n& SEE MORE DETAILS:",
            (0.7, 0.27),
            weight="bold",
            fontsize=10,
            color=self.background_color,
        )

        self.create_qrcode_image(self.create_vcard_data(), "qrcode.png")
        arr_code = mpimg.imread("qrcode.png")
        imagebox = OffsetImage(arr_code, zoom=0.50)
        ab = AnnotationBbox(
            imagebox,
            (0.83, 0.15),
            bboxprops=dict(
                edgecolor=self.white_color, facecolor=self.white_color, alpha=1.0
            ),
        )
        ax.add_artist(ab)
        # plt.savefig('resumeexample.png', dpi=300, bbox_inches='tight')

        plt.annotate(
            self.resume_page.website or "",
            (0.7, 0.017),
            weight="bold",
            fontsize=10,
            color=self.background_color,
        )

        return plt.savefig(img_output_file_path, dpi=300, bbox_inches="tight")
