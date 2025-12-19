from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader


def generate_pdf_report(
    filename: str,
    buses: list,
    voltages: list,
    image_path: str
):
    # Criar o PDF
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # =============================
    # TÍTULO
    # =============================
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(
        width / 2,
        height - 2 * cm,
        "Relatório de Fluxo de Potência"
    )

    # =============================
    # SUBTÍTULO
    # =============================
    c.setFont("Helvetica", 11)
    c.drawString(
        2 * cm,
        height - 3.2 * cm,
        "Perfil de Tensão do Sistema"
    )

    # =============================
    # GRÁFICO
    # =============================
    img = ImageReader(image_path)
    img_width_px, img_height_px = img.getSize()

    aspect = img_height_px / float(img_width_px)

    img_width = 16 * cm                 # largura fixa no PDF
    img_height = img_width * aspect     # altura proporcional

    c.drawImage(
        image_path,
        2 * cm,
        height - 5 * cm - img_height,
        width=img_width,
        height=img_height,
        preserveAspectRatio=True,
        mask='auto'
    )

    # =============================
    # TABELA
    # =============================
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, height - 16.2 * cm, "Barra")
    c.drawString(5 * cm, height - 16.2 * cm, "Tensão (pu)")

    c.setFont("Helvetica", 10)

    y = height - 17 * cm

    for bus, v in zip(buses, voltages):
        c.drawString(2 * cm, y, str(bus))
        c.drawString(5 * cm, y, f"{v:.4f}")
        y -= 0.5 * cm

    c.save()
