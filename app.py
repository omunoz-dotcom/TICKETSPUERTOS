import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

st.set_page_config(page_title="Carga de Tickets de Peso", page_icon="🚛", layout="centered")

st.title("🚛 Registro de Tickets de Peso")
st.write("Sube la foto del ticket de peso para enviarlo al sistema.")

with st.form("ticket_form", clear_on_submit=True):
    nombre_conductor = st.text_input("Nombre del Conductor / Placa del Vehículo")
    numero_ticket = st.text_input("Número de Ticket (Opcional)")
    
    archivo = st.file_uploader(
        "Toma una foto o selecciona el ticket", 
        type=["jpg", "jpeg", "png", "pdf"]
    )
    
    submit_button = st.form_submit_button("📤 Enviar Ticket", use_container_width=True)

def send_email(filename, conductor, num_ticket, file_bytes):
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_password = st.secrets["SENDER_PASSWORD"]
    mailing_list = [e.strip() for e in st.secrets["MAILING_LIST"].split(",") if e.strip()]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(mailing_list)
    msg['Subject'] = f"🚛 Ticket de Peso: {conductor if conductor else 'Sin Nombre'} - {num_ticket if num_ticket else ''}"

    body = f"""
    Se ha registrado un nuevo ticket de peso desde el puerto:

    - Conductor / Placa: {conductor if conductor else 'No especificado'}
    - Nº de Ticket: {num_ticket if num_ticket else 'N/A'}
    - Nombre de archivo: {filename}

    El archivo adjunto contiene la imagen/PDF del ticket de peso.
    """
    msg.attach(MIMEText(body, 'plain'))

    # Adjuntar archivo
    part = MIMEBase("application", "octet-stream")
    part.set_payload(file_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename= {filename}")
    msg.attach(part)

    # Conexión SMTP a Gmail
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, mailing_list, msg.as_string())
    server.close()

if submit_button:
    if not archivo:
        st.error("Por favor adjunta la foto del ticket antes de enviar.")
    else:
        with st.spinner("Enviando ticket..."):
            try:
                bytes_data = archivo.read()
                tag_conductor = nombre_conductor.replace(" ", "_") if nombre_conductor else "Ticket"
                clean_filename = f"{tag_conductor}_{archivo.name}"
                
                # Enviar correo con el adjunto
                send_email(clean_filename, nombre_conductor, numero_ticket, bytes_data)
                
                st.success("✅ ¡Ticket registrado y enviado con éxito a la lista de correo!")
            except Exception as e:
                st.error(f"Ocurrió un error al enviar: {e}")
