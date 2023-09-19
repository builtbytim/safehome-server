from libs.config.settings import get_settings

settings = get_settings()

EMAIL_DEFS = {
    'verify_email': {
        'subject': "Verify Your Email",
        'mail_from': settings.mail_from,
        'template_name': "verify_email.html",
    },


}
