import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decouple import config
from email.mime.base import MIMEBase
from email import encoders
import os


def send_email(subject, body, receiver_email,attachment_path=None):
    # Cargar las variables de entorno desde el archivo .env
    smtp_server = config('SMTP_SERVER')
    smtp_port = config('SMTP_PORT', cast=int)
    sender_email = config('SENDER_EMAIL')
    sender_password = config('SENDER_PASSWORD')

    # Crear el mensaje
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))


    # Adjuntar archivo si se proporciona una ruta
    if attachment_path is not None:
        # Verificar si el archivo existe
        if not os.path.isfile(attachment_path):
            print(f"Error: el archivo '{attachment_path}' no existe.")

        
        # Leer el archivo en modo binario
        with open(attachment_path, 'rb') as attachment:
            mime_base = MIMEBase('application', 'octet-stream')
            mime_base.set_payload(attachment.read())
            encoders.encode_base64(mime_base)
            mime_base.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(mime_base)



    

    # Inicializar la variable de servidor
    server = None

    # Conectarse al servidor SMTP y enviar el correo
    try:
        # Conectarse al servidor SMTP
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.set_debuglevel(0)  # Habilitar el modo de depuración para obtener más información
        server.ehlo()  # Identificarse con el servidor SMTP
        server.starttls()  # Iniciar la conexión segura
        server.ehlo()  # Vuelve a identificarse como cliente TLS
        server.login(sender_email, sender_password)  # Iniciar sesión

        # Enviar el correo
        text = msg.as_string()  # Convertir el mensaje en una cadena
        server.sendmail(sender_email, receiver_email, text)  # Enviar el correo
        print(f'Correo enviado exitosamente a {receiver_email}')
    except smtplib.SMTPException as e:
        raise ConnectionAbortedError(e)
    except Exception as e:
        raise ConnectionError(e)
    finally:
        if server is not None:
            try:
                server.quit()  # Cerrar la conexión con el servidor SMTP
            except smtplib.SMTPServerDisconnected:
                pass  # Ignorar errores si la conexión ya está cerrada

# for i in range(0,20):
#     send_email(f"test{i**2}", f"perrita wellington{i}", "mateo2597@gmail.com",attachment_path=None)