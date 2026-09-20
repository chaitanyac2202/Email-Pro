import smtplib
import mimetypes
from email.message import EmailMessage
from config import Config
from datetime import datetime
import os

def send_campaign(recipient_list, subject, body, attachment_path=None):
    results = []
    
    if not Config.EMAIL_USER or not Config.EMAIL_PASS:
        return [{"email": email, "status": "Failed: Email credentials not configured", "timestamp": datetime.now().isoformat()} for email in recipient_list]

    try:
        # Connect to SMTP server
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            # Google App Passwords often contain spaces for readability, but they must be removed for login
            clean_password = Config.EMAIL_PASS.replace(' ', '')
            server.login(Config.EMAIL_USER, clean_password)
            
            for recipient in recipient_list:
                msg = EmailMessage()
                msg['Subject'] = subject
                msg['From'] = Config.EMAIL_USER
                msg['To'] = recipient
                
                # We can set both plain and html, but for simplicity assuming html/text body input
                msg.set_content(body) 
                
                if attachment_path and os.path.exists(attachment_path):
                    ctype, encoding = mimetypes.guess_type(attachment_path)
                    if ctype is None or encoding is not None:
                        ctype = 'application/octet-stream'
                    maintype, subtype = ctype.split('/', 1)
                    
                    with open(attachment_path, 'rb') as f:
                        msg.add_attachment(f.read(),
                                           maintype=maintype,
                                           subtype=subtype,
                                           filename=os.path.basename(attachment_path))
                
                try:
                    server.send_message(msg)
                    results.append({
                        "email": recipient, 
                        "status": "Delivered",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    results.append({
                        "email": recipient, 
                        "status": f"Failed: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
    except Exception as e:
        # SMTP connection failure
        for recipient in recipient_list:
            results.append({
                "email": recipient, 
                "status": f"Failed: Server connection error - {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            
    return results
