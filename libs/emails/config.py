from libs.config.settings import get_settings

settings = get_settings()

EMAIL_DEFS = {
    'verify_email': {
        'subject': "Verify Your Email",
        'mail_from': settings.mail_from,
        'template_name': "verify_email.html",
    },

    'verify_email_done': {
        'subject': "Email Confirmed",
        'mail_from': settings.mail_from,
        'template_name': "verify_email_done.html",
    },

    "kyc_approved": {
        "subject": "KYC Approved",
        "mail_from": settings.mail_from,
        "template_name": "kyc_approved.html",

    },

    "kyc_rejected": {
        "subject": "KYC Rejected",
        "mail_from": settings.mail_from,
        "template_name": "kyc_rejected.html",

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

    },


    "password_changed": {
        "subject": "Your Password Was Changed",
        "mail_from": settings.mail_from,
        "template_name": "password_changed.html",

    },


    "sign_in_notification": {
        "subject": "Sign In Notification",
        "mail_from": settings.mail_from,
        "template_name": "sign_in_notification.html",

    },

    "joined_waitlist": {
        "subject": "Application Received",
        "mail_from": settings.mail_from,
        "template_name": "joined_waitlist.html",

    }






}
