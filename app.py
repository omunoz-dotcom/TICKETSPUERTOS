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

st.set_page_config(page_title="Carga de Tickets de Peso", page_icon="🚛", layout="centered")

st.title("🚛 1 Registro de Tickets de Peso")
st.write("Sube la foto del ticket de peso para registrarlo en el sistema.")

with st.form("ticket_form", clear_on_submit=True):
    nombre_conductor = st.text_input("Nombre del Conductor / Placa del Vehículo")
    numero_ticket = st.text_input("Número de Ticket (Opcional)")
    
    archivo = st.file_uploader(
        "Toma una foto o selecciona el ticket", 
        type=["jpg", "jpeg", "png", "pdf"]
    )
    
    submit_button = st.form_submit_button("📤 Enviar Ticket", use_container_width=True)

def get_drive_service():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    creds = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def upload_to_drive(file_bytes, filename, mimetype):
    service = get_drive_service()
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
    user_email = st.secrets["SENDER_EMAIL"]
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=False)
    
    # 1. Crear el archivo en la carpeta
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    
    file_id = uploaded_file.get('id')
    
    # 2. Transferir el permiso/propiedad a tu cuenta de Gmail personal
    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': user_email
    }
    try:
        service.permissions().create(
            fileId=file_id,
            body=permission,
            supportsAllDrives=True
        ).execute()
    except Exception:
        pass
        
    return uploaded_file.get('webViewLink')

def send_email(filename, drive_url, conductor, num_ticket, file_bytes):
    sender_email = st.secrets["SENDER_EMAIL"]
    sender_password = st.secrets["SENDER_PASSWORD"]
    mailing_list = [e.strip() for e in st.secrets["MAILING_LIST"].split(",") if e.strip()]

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

    part = MIMEBase("application", "octet-stream")
    part.set_payload(file_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename= {filename}")
    msg.attach(part)

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, mailing_list, msg.as_string())
    server.close()

if submit_button:
    if not archivo:
        st.error("Por favor adjunta la foto del ticket antes de enviar.")
    else:
        with st.spinner("Subiendo ticket y notificando..."):
            try:
                bytes_data = archivo.read()
                tag_conductor = nombre_conductor.replace(" ", "_") if nombre_conductor else "Ticket"
                clean_filename = f"{tag_conductor}_{archivo.name}"
                
                drive_link = upload_to_drive(bytes_data, clean_filename, archivo.type)
                send_email(clean_filename, drive_link, nombre_conductor, numero_ticket, bytes_data)
                
                st.success("✅ ¡Ticket subido y enviado con éxito!")
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
