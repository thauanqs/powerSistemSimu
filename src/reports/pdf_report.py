import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet


def header_footer(canvas, doc):
    width, height = A4
    logo_width = 8 * cm
    logo_height = 4.4 * cm

    # Verifica se o arquivo existe antes de desenhar para evitar travar o PDF
    if os.path.exists(doc.logo_path):
        canvas.drawImage(
            doc.logo_path,
            1 * cm,
            height - 3.3 * cm,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )
    else:
        # Apenas imprime um aviso no console e segue gerando o PDF sem logo
        print(f"AVISO: Logo não encontrada no caminho: {doc.logo_path}")

    # Texto do cabeçalho
    canvas.setFont("Helvetica", 10)
    canvas.drawString(2 * cm, height - 3.2 * cm, "Power Systems Simulator")

    # Rodapé
    canvas.setFont("Helvetica", 9)
    canvas.drawString(18 * cm, 1.5 * cm, f"Página {doc.page}")


# SOLUÇÃO: Adicionamos 'logo_path=None' aqui para aceitar o argumento vindo do controller
# mas dentro da função nós calculamos o caminho correto independentemente do que foi enviado.
def generate_pdf(filename, bus_data, image_paths, logo_path=None):
    HEADER_HEIGHT = 5.0 * cm

    # --- CÁLCULO AUTOMÁTICO DO CAMINHO DA IMAGEM ---
    # 1. Pega a pasta onde este arquivo (pdf_report.py) está: .../src/reports
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Sobe para 'src'
    src_dir = os.path.dirname(current_dir)

    # 3. Sobe para a raiz do projeto 'Parte gabriel'
    project_root = os.path.dirname(src_dir)

    # 4. Desce para a pasta da imagem: .../Parte gabriel/reports/assets/logo.png
    abs_logo_path = os.path.join(project_root, 'reports', 'assets', 'logo.png')
    # -----------------------------------------------

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=0.5 * cm,
        rightMargin=2.0 * cm,
        topMargin=HEADER_HEIGHT + 0.5 * cm,
        bottomMargin=2.0 * cm
    )

    # Forçamos o uso do caminho absoluto calculado aqui, ignorando o argumento incorreto
    doc.logo_path = abs_logo_path

    styles = getSampleStyleSheet()
    elements = []

    elements.append(
        Paragraph("<b>Relatório de Fluxo de Potência</b>", styles["Title"])
    )
    elements.append(Spacer(1, 12))

    # Tabela
    table_data = [[
        "Barra", "Tipo", "V (pu)", "Ângulo", "P (MW)", "Q (MVAr)"
    ]]

    for b in bus_data:
        table_data.append([
            b["id"],
            b["type"],
            f"{b['v']:.3f}",
            f"{b['angle']:.2f}",
            f"{b['p']:.2f}",
            f"{b['q']:.2f}",
        ])

    table = Table(table_data, repeatRows=1)
    elements.append(table)

    elements.append(PageBreak())

    elements.append(Paragraph("Perfil de Tensão", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    for img_path in image_paths:
        # Verifica se a imagem do gráfico existe antes de adicionar
        if os.path.exists(img_path):
            elements.append(Image(img_path, width=16 * cm, height=10 * cm))
            elements.append(PageBreak())
        else:
            elements.append(Paragraph(f"Imagem não encontrada: {img_path}", styles["Normal"]))

    doc.build(
        elements,
        onFirstPage=header_footer,
        onLaterPages=header_footer
    )