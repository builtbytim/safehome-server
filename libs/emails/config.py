from libs.config.settings import get_settings

settings = get_settings()

EMAIL_DEFS = {
    'verify_email': {
        'subject': "Verify Your Email",
        'mail_from': settings.mail_from,
        'template_name': "verify_email.html",
    },

    "kyc_approved": {
        "subject": "KYC Approved",
        "mail_from": settings.mail_from,
        "template_name": "kyc_approved.html",

    },

    "reset_password": {
        "subject": "Reset Your Password",
        "mail_from": settings.mail_from,
        "template_name": "reset_password.html",

    },

    "reset_password_done": {
        "subject": "Your Password Was Reset",
        "mail_from": settings.mail_from,
        "template_name": "reset_password_done.html",

    }




}
