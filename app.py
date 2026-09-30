import streamlit as st
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Configuración de la interfaz para celulares
st.set_page_config(page_title="Carga de Tickets de Peso", page_icon="🚛📤", layout="centered")

st.title("🚛 Registro de Tickets de Peso")
st.write("Sube la foto del ticket de peso para registrarlo en el sistema.")

# Formulario para el conductor
with st.form("ticket_form", clear_on_submit=True):
    nombre_conductor = st.text_input("Nombre del Conductor / Placa del Vehículo")
    numero_ticket = st.text_input("Número de Ticket (Opcional)")
    
    # Captura de foto con la cámara del celular o galería
    archivo = st.file_uploader(
        "Toma una foto o selecciona el ticket", 
        type=["jpg", "jpeg", "png", "pdf"]
    )
    
    submit_button = st.form_submit_button("📤 Enviar Ticket", use_container_width=True)

# Función para conectarse a Google Drive
def get_drive_service():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

# Función para subir archivo a Drive
def upload_to_drive(file_bytes, filename, mimetype):
    service = get_drive_service()
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=True)
    
    # Se añade supportsAllDrives=True para solucionar el error 403 de cuota
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    
    return uploaded_file.get('webViewLink')

# Función para enviar el correo corporativo
def send_email(filename, drive_url, conductor, num_ticket, file_bytes):
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_password = st.secrets["SENDER_PASSWORD"]
    mailing_list = st.secrets["MAILING_LIST"].split(",")

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(mailing_list)
    msg['Subject'] = f"Nuevo Ticket de Peso - {conductor if conductor else 'Sin Nombre'}"

    body = f"""
    Se ha registrado un nuevo ticket de peso:

    - Conductor / Placa: {conductor}
    - Nº de Ticket: {num_ticket if num_ticket else 'N/A'}
    - Nombre de archivo: {filename}
    - Google Drive: {drive_url}

    Adjunto se encuentra la copia del ticket.
    """
    msg.attach(MIMEText(body, 'plain'))

    # Adjunto
    part = MIMEBase("application", "octet-stream")
    part.set_payload(file_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename= {filename}")
    msg.attach(part)

    # Conexión SMTP Gmail Corporativo
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, mailing_list, msg.as_string())
    server.close()

# Procesamiento al presionar el botón
if submit_button:
    if not archivo:
        st.error("Por favor adjunta la foto del ticket antes de enviar.")
    else:
        with st.spinner("Subiendo ticket y notificando..."):
            try:
                bytes_data = archivo.read()
                
                # Crear nombre descriptivo para el archivo
                tag_conductor = nombre_conductor.replace(" ", "_") if nombre_conductor else "Ticket"
                clean_filename = f"{tag_conductor}_{archivo.name}"
                
                # 1. Subir a Drive
                drive_link = upload_to_drive(bytes_data, clean_filename, archivo.type)
                
                # 2. Enviar Correo
                send_email(clean_filename, drive_link, nombre_conductor, numero_ticket, bytes_data)
                
                st.success("✅ ¡Ticket subido y enviado con éxito!")
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
