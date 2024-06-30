import smtplib
from pydantic import EmailStr
from libs.config.settings import get_settings
from .config import EMAIL_DEFS
from email.message import EmailMessage
from email.headerregistry import Address
from .render_template import render_to_string
from libs.logging import Logger


settings = get_settings()

logger = Logger(f"{__package__}.{__name__}")


def dispatch_email(email_to: list[EmailStr] | EmailStr, email_type: str, email_data: dict):

    if not email_type in EMAIL_DEFS:
        raise ValueError("Invalid email type")

    conf = EMAIL_DEFS[email_type]

    try:

        with smtplib.SMTP_SSL(settings.mail_server, settings.mail_port) as smtp:
            # smtp.starttls()
            smtp.login(settings.mail_username, settings.mail_password)
            email_content = render_to_string(
                conf['template_name'], **email_data)

            msg = EmailMessage()
            msg['Subject'] = conf['subject']
            msg['From'] = Address(
                settings.mail_display_name, settings.mail_domain_username, settings.mail_domain)
            msg['To'] = email_to if isinstance(
                email_to, str) else ",".join(email_to)

            msg.set_content(email_content, subtype="html")

            smtp.sendmail(conf['mail_from'], email_to, msg.as_string())

    except Exception as e:

        if isinstance(email_to, list):
            logger.error(
                f"Email {conf['template_name']} failed to send to {email_to}")

        else:
            logger.error(
                f"Email {conf['template_name']} failed to send to {email_to}")

        logger.error(str(e))

        raise Exception("Email failed to send")

    else:
        logger.info(
            f"Email {conf['template_name']} sent to {email_to} successfully")
