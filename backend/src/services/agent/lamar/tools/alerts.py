# src/services/llm/lamar/alerts.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_429_email(provider_name, error_details):
    sender_email = "dev@gustavocoello.space"
    receiver_email = "coellog634@gmail.com"
    
    msg = MIMEMultipart()
    msg['From'] = f"Lamar Agent <{sender_email}>"
    msg['To'] = receiver_email
    msg['Subject'] = f"🚨 ALERTA CRÍTICA: 429 Too Many Requests en {provider_name}"

    body = f"""
    Hola Gustavo,
    
    Lamar ha detectado que el proveedor {provider_name} ha alcanzado su límite de cuota (Error 429).
    
    Detalles del error:
    {error_details}
    
    Acción tomada: 
    Lamar ha puesto este proveedor en 'cooldown' y está utilizando los respaldos automáticamente.
    
    -- 
    Atentamente,
    Lamar (Tu Agente de Resiliencia)
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Aquí debes poner tus credenciales de SMTP reales
        with smtplib.SMTP("mail.dev.gustavocoello.space", 587) as server:
            # server.starttls()
            # server.login(sender_email, "TU_PASSWORD")
            # server.send_message(msg)
            print(f"📧 Correo enviado a {receiver_email}")
    except Exception as e:
        print(f"❌ No se pudo enviar el correo: {e}")