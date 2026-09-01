from flask import Flask, render_template, request, send_file, redirect
import sqlite3
import base64
import os
import secrets

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)

NOMBRE_BASE_DATOS = "servicio.db"


def crear_base_datos():

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefono TEXT NOT NULL,
            equipo TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            falla TEXT,
            accesorios TEXT,
            firma TEXT,
            estado TEXT DEFAULT 'Pendiente de firma',
            codigo TEXT
        )
    """)

    conexion.commit()
    conexion.close()


@app.route("/")
def formulario():

    return render_template("formulario.html")


@app.route("/guardar", methods=["POST"])
def guardar():

    cliente = request.form["cliente"]
    telefono = request.form["telefono"]
    equipo = request.form["equipo"]
    marca = request.form["marca"]
    modelo = request.form["modelo"]
    falla = request.form["falla"]
    accesorios = request.form["accesorios"]

    # Crear código único para la orden
    codigo = secrets.token_urlsafe(6)

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO ordenes
        (
            cliente,
            telefono,
            equipo,
            marca,
            modelo,
            falla,
            accesorios,
            codigo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cliente,
        telefono,
        equipo,
        marca,
        modelo,
        falla,
        accesorios,
        codigo
    ))

    conexion.commit()

    numero_orden = cursor.lastrowid

    conexion.close()

    return render_template(
        "revision.html",
        numero_orden=numero_orden,
        cliente=cliente,
        telefono=telefono,
        equipo=equipo,
        marca=marca,
        modelo=modelo,
        falla=falla,
        accesorios=accesorios,
        codigo=codigo
    )


@app.route("/firmar/<int:numero_orden>", methods=["POST"])
def firmar(numero_orden):

    firma = request.form["firma"]

    if not firma:

        return "No se recibió la firma."

    firma = firma.split(",")[1]

    carpeta_firmas = "firmas"
    carpeta_pdfs = "pdf"

    os.makedirs(carpeta_firmas, exist_ok=True)
    os.makedirs(carpeta_pdfs, exist_ok=True)

    # Guardar firma

    nombre_firma = f"firma_{numero_orden}.png"

    ruta_firma = os.path.join(
        carpeta_firmas,
        nombre_firma
    )

    with open(ruta_firma, "wb") as archivo:

        archivo.write(
            base64.b64decode(firma)
        )

    # Actualizar orden

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    conexion.execute("""
        UPDATE ordenes
        SET firma = ?,
            estado = ?
        WHERE id = ?
    """, (
        nombre_firma,
        "Firmada",
        numero_orden
    ))

    conexion.commit()

    conexion.close()

    # Obtener orden

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    conexion.row_factory = sqlite3.Row

    orden = conexion.execute(
        "SELECT * FROM ordenes WHERE id = ?",
        (numero_orden,)
    ).fetchone()

    conexion.close()

    if not orden:

        return "Orden no encontrada."

    # Crear PDF

    nombre_pdf = f"orden_{numero_orden}.pdf"

    ruta_pdf = os.path.join(
        carpeta_pdfs,
        nombre_pdf
    )

    pdf = canvas.Canvas(
        ruta_pdf,
        pagesize=A4
    )

    ancho, alto = A4

    # Título

    pdf.setFont(
        "Helvetica-Bold",
        20
    )

    pdf.drawString(
        50,
        alto - 60,
        "ORDEN DE SERVICIO TECNICO"
    )

    # Número de orden

    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        alto - 95,
        f"Orden #{numero_orden}"
    )

    # Cliente

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 140,
        "DATOS DEL CLIENTE"
    )

    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        50,
        alto - 165,
        f"Cliente: {orden['cliente']}"
    )

    pdf.drawString(
        50,
        alto - 185,
        f"Telefono: {orden['telefono']}"
    )

    # Equipo

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 225,
        "DATOS DEL EQUIPO"
    )

    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        50,
        alto - 250,
        f"Equipo: {orden['equipo']}"
    )

    pdf.drawString(
        50,
        alto - 270,
        f"Marca: {orden['marca'] or ''}"
    )

    pdf.drawString(
        50,
        alto - 290,
        f"Modelo: {orden['modelo'] or ''}"
    )

    # Falla

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 330,
        "FALLA REPORTADA"
    )

    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        50,
        alto - 355,
        orden["falla"] or "No especificada"
    )

    # Accesorios

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 395,
        "ACCESORIOS ENTREGADOS"
    )

    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        50,
        alto - 420,
        orden["accesorios"] or "Ninguno"
    )

    # Firma

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 470,
        "FIRMA DEL CLIENTE"
    )

    pdf.drawImage(
        ImageReader(ruta_firma),
        50,
        alto - 620,
        width=250,
        height=120,
        preserveAspectRatio=True,
        mask="auto"
    )

    pdf.setFont(
        "Helvetica",
        9
    )

    pdf.drawString(
        50,
        alto - 640,
        "Firma digital del cliente"
    )

    pdf.save()

    # Pantalla final

    return f"""
    <!DOCTYPE html>

    <html lang="es">

    <head>

        <meta charset="UTF-8">

        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>Orden finalizada</title>

        <style>

            body {{
                font-family: Arial, sans-serif;
                background: #f2f4f7;
                margin: 0;
                padding: 30px;
            }}

            .contenedor {{
                max-width: 500px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            }}

            .correcto {{
                font-size: 50px;
            }}

            h1 {{
                margin-bottom: 10px;
            }}

            .orden {{
                font-size: 20px;
                font-weight: bold;
                margin: 20px;
            }}

            .boton {{
                display: block;
                text-decoration: none;
                background: #2563eb;
                color: white;
                padding: 14px;
                border-radius: 8px;
                margin-top: 15px;
            }}

        </style>

    </head>

    <body>

        <div class="contenedor">

            <div class="correcto">
                ✓
            </div>

            <h1>Orden registrada</h1>

            <p>
                La orden fue registrada y firmada correctamente.
            </p>

            <div class="orden">
                Orden #{numero_orden}
            </div>

            <a class="boton"
               href="/pdf/{numero_orden}"
               target="_blank">

                Ver comprobante PDF

            </a>

        </div>

    </body>

    </html>
    """


@app.route("/pdf/<int:numero_orden>")
def ver_pdf(numero_orden):

    ruta_pdf = os.path.join(
        "pdf",
        f"orden_{numero_orden}.pdf"
    )

    if not os.path.exists(ruta_pdf):

        return "PDF no encontrado."

    return send_file(ruta_pdf)

@app.route("/registro/<codigo>")
def registro(codigo):

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)
    conexion.row_factory = sqlite3.Row

    orden = conexion.execute(
        "SELECT * FROM ordenes WHERE codigo = ?",
        (codigo,)
    ).fetchone()

    conexion.close()

    if not orden:
        return "Enlace no válido o expirado."

    return render_template(
        "formulario.html",
        codigo=codigo
    )

@app.route("/admin")
def admin():

    return render_template(
        "admin.html"
    )

@app.route("/generar-enlace", methods=["POST"])
def generar_enlace():

    telefono = request.form["telefono"]

    codigo = secrets.token_urlsafe(6)

    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    conexion.execute("""
        INSERT INTO ordenes
        (
            cliente,
            telefono,
            equipo,
            marca,
            modelo,
            falla,
            accesorios,
            firma,
            estado,
            codigo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Pendiente",
        telefono,
        "Pendiente",
        "",
        "",
        "",
        "",
        "",
        "Pendiente de registro",
        codigo
    ))

    conexion.commit()

    conexion.close()

    enlace = f"https://{request.host}/registro/{codigo}"

    return render_template(
        "admin.html",
        enlace=enlace
    )


if __name__ == "__main__":

    crear_base_datos()

    app.run(
    host="0.0.0.0",
    port=5000,
    debug=True
    )