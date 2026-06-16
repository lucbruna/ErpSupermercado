import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.models import ConfigGeral


def get_mail_config():
    def g(chave, padrao=''):
        c = ConfigGeral.query.filter_by(modulo='email', chave=chave).first()
        return c.valor if c else padrao
    return {
        'smtp_host': g('smtp_host', 'smtp.gmail.com'),
        'smtp_port': int(g('smtp_port', '587')),
        'smtp_user': g('smtp_user', ''),
        'smtp_pass': g('smtp_pass', ''),
        'smtp_tls': g('smtp_tls', '1') == '1',
        'from_email': g('from_email', ''),
        'from_name': g('from_name', 'ERP Supermercado'),
    }


def send_email(to_addr, subject, html_body):
    cfg = get_mail_config()
    if not cfg['smtp_user'] or not cfg['smtp_pass']:
        return False, 'SMTP não configurado. Configure em Configurações > Email.'
    msg = MIMEMultipart('alternative')
    msg['From'] = f"{cfg['from_name']} <{cfg['from_email'] or cfg['smtp_user']}>"
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(cfg['smtp_host'], cfg['smtp_port'], timeout=30) as server:
            if cfg['smtp_tls']:
                server.starttls(context=ctx)
            server.login(cfg['smtp_user'], cfg['smtp_pass'])
            server.sendmail(msg['From'], [to_addr], msg.as_string())
        return True, 'Email enviado!'
    except Exception as e:
        return False, str(e)