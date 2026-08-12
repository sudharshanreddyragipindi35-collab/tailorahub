from .integrations import email_service


def send_email(to_email: str, subject: str, body: str) -> dict:
    return email_service().send(to_email, subject, body)
