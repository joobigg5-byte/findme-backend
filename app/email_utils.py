"""
Email sending.

send_email() below is a STUB — it logs the email instead of sending it.
That's the honest state of things: sending real email needs a real
provider account (SendGrid, AWS SES, Postmark, etc.) with real API
credentials, which this environment doesn't have and can't create for you.

Wiring a real provider is a small, isolated change — swap the body of
send_email() for that provider's SDK call, add the API key as an
environment variable, and every caller (password reset, and any future
"invite a teammate" or "notify on signup" flow) picks it up automatically
without changes anywhere else.
"""
import logging

logger = logging.getLogger("findme.email")


def send_email(to: str, subject: str, body: str) -> None:
    """
    STUB: logs the email instead of sending it. Replace this function body
    with a real provider call before relying on this in production —
    e.g. for SendGrid:

        import sendgrid
        from sendgrid.helpers.mail import Mail
        sg = sendgrid.SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        sg.send(Mail(from_email="noreply@yourdomain.com", to_emails=to,
                      subject=subject, plain_text_content=body))
    """
    logger.info("=== EMAIL WOULD BE SENT (no provider configured) ===")
    logger.info("To: %s", to)
    logger.info("Subject: %s", subject)
    logger.info("Body:\n%s", body)
    logger.info("=== END EMAIL ===")
