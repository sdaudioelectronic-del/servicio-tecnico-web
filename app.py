from flask import Flask, render_template, request, send_file, redirect
from reportlab.lib.utils import ImageReader
from datetime import datetime
from zoneinfo import ZoneInfo
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.enums import TA_RIGHT
import sqlite3
import base64
import os
import secrets


from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)


NOMBRE_BASE_DATOS = "servicio.db"

fecha_actual = datetime.now()

fecha = fecha_actual.strftime("%d/%m/%Y")
hora = fecha_actual.strftime("%I:%M %p")

fecha_actual = datetime.now(
    ZoneInfo("America/Bogota")
)

fecha = fecha_actual.strftime("%d/%m/%Y")
hora = fecha_actual.strftime("%I:%M %p")


def crear_base_datos():
    print(">>> CREANDO BASE DE DATOS:", NOMBRE_BASE_DATOS)
    conexion = sqlite3.connect(NOMBRE_BASE_DATOS)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefono TEXT NOT NULL,
            direccion TEXT NOT NULL,
            equipo TEXT NOT NULL,
            marca TEXT,
            modelo TEXT,
            falla TEXT,
            observacion TEXT,
            accesorios TEXT,
            firma TEXT,
            estado TEXT DEFAULT 'Pendiente de firma',
            codigo TEXT
            mano_obra REAL DEFAULT 0,
            repuestos REAL DEFAULT 0
        )
    """)

    conexion.commit()
    conexion.close()
crear_base_datos()

@app.route("/")
def formulario():

    return render_template("formulario.html")


@app.route("/guardar", methods=["POST"])
def guardar():

    cliente = request.form["cliente"]
    telefono = request.form["telefono"]
    direccion = request.form["direccion"]
    equipo = request.form["equipo"]
    marca = request.form["marca"]
    modelo = request.form["modelo"]
    falla = request.form["falla"]
    observacion = request.form["observacion"]
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
            direccion,
            equipo,
            marca,
            modelo,
            falla,
            observacion,
            accesorios,
            codigo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        cliente,
        telefono,
        direccion,
        equipo,
        marca,
        modelo,
        falla,
        observacion,
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
        direccion=direccion,
        telefono=telefono,
        equipo=equipo,
        marca=marca,
        modelo=modelo,
        falla=falla,
        observacion=observacion,
        accesorios=accesorios,
        codigo=codigo
    )


@app.route("/firmar/<int:numero_orden>", methods=["POST"])
def firmar(numero_orden):

    firma = request.form["firma"]

    if not firma:

        return "No se recibió la firma."

    mano_obra = float(request.form.get("mano_obra", 0) or 0)
    repuestos = float(request.form.get("repuestos", 0) or 0)

    total = mano_obra + repuestos


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
            estado = ?,
            mano_obra = ?,
            repuestos = ?
        WHERE id = ?
    """,  (
        nombre_firma,
        "Firmada",
        mano_obra,
        repuestos,
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

    mano_obra = orden["mano_obra"] or 0
    repuestos = orden["repuestos"] or 0

    total = mano_obra + repuestos
    # Crear PDF

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


# Fecha y hora

    fecha_actual = datetime.now(
        ZoneInfo("America/Bogota")
    )

    fecha = fecha_actual.strftime("%d/%m/%Y")
    hora = fecha_actual.strftime("%I:%M %p")


# Fecha en el PDF

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(
        450,
        alto - 110,
        f"Fecha: {fecha}"
    )

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(
        450,
        alto - 125,
        f"Hora: {hora}"
    )


# Logo

    ruta_logo = os.path.join(
        "static",
        "logo.png"
    )

    pdf.drawImage(
        ImageReader(ruta_logo),
        20,
        alto - 80,
        width=120,
        height=50,
        preserveAspectRatio=True,
        mask="auto"
    )


# =========================================================
# ENCABEZADO
# =========================================================

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(
        ancho / 2,
        alto - 55,
        "ORDEN DE SERVICIO TÉCNICO"
    )

    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        ancho / 2,
        alto - 72,
        "Comprobante de recepción del equipo"
    )

# Línea separadora

    pdf.line(
        40,
        alto - 90,
        ancho - 40,
        alto - 90
    )

# =========================================================
# INFORMACIÓN DE LA ORDEN
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        alto - 120,
        f"ORDEN #{numero_orden}"
    )

    pdf.setFont("Helvetica", 10)


# =========================================================
# DATOS DEL CLIENTE
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        alto - 155,
        "DATOS DEL CLIENTE"
    )

    pdf.roundRect(
        45,
        alto - 220,
        ancho - 90,
        45,
        6
    )

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(
        60,
        alto - 190,
        "Cliente:"
    )

    pdf.drawString(
        60,
        alto - 210,
        "Dirección:"
    )


    pdf.drawString(
        320,
        alto - 190,
        "Teléfono:"
    )

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        105,
        alto - 190,
        orden["cliente"] or ""
    )

    pdf.drawString(
        375,
        alto - 190,
        orden["telefono"] or ""
    )

    pdf.drawString(
        115,
        alto - 210,
        orden["direccion"] or ""
    )

# =========================================================
# DATOS DEL EQUIPO
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        alto - 245,
        "EQUIPO RECIBIDO"
    )

    pdf.roundRect(
        45,
        alto - 330,
        ancho - 90,
        60,
        6
    )

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(
        60,
        alto - 290,
        "Equipo:"
    )

    pdf.drawString(
        320,
        alto - 290,
        "Marca:"
    )

    pdf.drawString(
        60,
        alto - 315,
        "Modelo:"
    )

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        110,
        alto - 290,
        orden["equipo"] or ""
    )

    pdf.drawString(
        365,
        alto - 290,
        orden["marca"] or ""
    )

    pdf.drawString(
        110,
        alto - 315,
        orden["modelo"] or ""
    )

    # =========================================================
# FALLA REPORTADA
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        alto - 355,
        "FALLA REPORTADA"
    )

    pdf.roundRect(
        45,
        alto - 430,
        ancho - 350,
        60,
        6
    )

    falla = orden["falla"] or "No especificada"


# Estilo del texto

    estilo_falla = ParagraphStyle(
        "Falla",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT
    )


# Crear párrafo

    parrafo_falla = Paragraph(
        falla,
        estilo_falla
    )


# Calcular tamaño del texto

    ancho_falla = ancho - 370
    alto_falla = 50

    parrafo_falla.wrap(
        ancho_falla,
        alto_falla
    )


# Dibujar dentro del recuadro

    parrafo_falla.drawOn(
        pdf,
        60,
        alto - 420
    )
    
    # =========================================================
    # =========================================================

    # =========================================================
# OBSERVACIONES 
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        345,
        alto - 355,
        "OBSERVACIONES"
    )

    pdf.roundRect(
        320,
        alto - 430,
        ancho - 350,
        60,
        6
    )

    observacion = orden["observacion"] or "Sin observaciones"


# Estilo del texto

    estilo_observacion = ParagraphStyle(
        "observacion",
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_LEFT
    )


# Crear párrafo

    parrafo_observacion = Paragraph(
        observacion,
        estilo_observacion
    )


# Calcular tamaño del texto

    ancho_observacion = ancho - 370
    alto_observacion = 50

    parrafo_observacion.wrap(
        ancho_observacion,
        alto_observacion
    )


# Dibujar dentro del recuadro

    parrafo_observacion.drawOn(
        pdf,
        325,
        alto - 420
    )


    
# =========================================================
# ACCESORIOS
# =========================================================

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(
        50,
        alto - 455,
        "ACCESORIOS ENTREGADOS"
    )

    pdf.roundRect(
        45,
        alto - 520,
        ancho - 90,
        50,
        6
    )#Espacio de Campo

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        60,
        alto - 500,
        orden["accesorios"] or "Ninguno"
    )


    # ==============================
    # DESGLOSE DE COSTOS
    # ==============================

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        50,
        alto - 580,
        "DESGLOSE DE COSTOS"
    )

    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        70,
        alto - 620,
        f"Mano de obra:    $ {mano_obra:,.0f}"
    )

    pdf.drawString(
        75,
        alto - 640,
        f"Repuestos:       $ {repuestos:,.0f}"
    )

    # Línea separadora

    pdf.line(
        50,
        alto - 590,
        300,
        alto - 590
    )

    # Total

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        70,
        alto - 668,
        f"TOTAL:           $ {total:,.0f}"
    )
    


# =========================================================
# FIRMA
# =========================================================

    

    pdf.drawImage(
     ImageReader(ruta_firma),
        5,
        alto - 785,
        width=220,
        height=90,
        preserveAspectRatio=True,
        mask="auto"
    )


    # Firma del técnico
    pdf.drawImage(
        ImageReader("static/firma_tecnico.png"),
        320,
        alto - 795,
        width=180,
        height=80,
        preserveAspectRatio=True,
        mask="auto"
    )       

    pdf.setFont("Helvetica", 10)

    pdf.drawString(
        90,
        alto - 790,
        "Firma del cliente"
    )   

    pdf.drawString(
        370,
        alto - 790,
        "Firma del técnico"
    )


# =========================================================
# PIE DE PÁGINA
# =========================================================

    pdf.line(
        40,
        45,
        ancho - 40,
        45
    )

    pdf.setFont("Helvetica", 8)

    pdf.drawCentredString(
        ancho / 2,
        30,
        "Conserve este documento como comprobante de recepción del equipo."
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
            direccion,
            equipo,
            marca,
            modelo,
            falla,
            observacion,
            accesorios,
            firma,
            estado,
            codigo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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