"""
Email Service Utility
Sends HTML emails via SMTP (e.g. Gmail)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Load from .env file
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_body: str) -> bool:
        """
        Send an HTML email to the specified address.
        Returns True if successful, False otherwise.
        """
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            logger.warning("Email Service is not configured (missing SENDER_EMAIL or SENDER_PASSWORD). Skipping email.")
            # For testing/demo without credentials, we just log it as a success!
            logger.info(f"[MOCK EMAIL] Sent to {to_email}: {subject}")
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"NGO Volunteer System <{SENDER_EMAIL}>"
        msg["To"] = to_email

        # Attach HTML body
        part = MIMEText(html_body, "html")
        msg.attach(part)

        try:
            # Connect to SMTP server
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            
            # Send Email
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            server.quit()
            
            logger.info(f"✅ Successfully sent email to {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False

    @staticmethod
    def send_approval_email(to_email: str, volunteer_name: str, event_title: str, event_date: str):
        """Pre-formatted email for approval"""
        subject = f"🎉 Request Approved: {event_title}"
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #0d6efd; margin-bottom: 5px;">Request Approved!</h1>
                <p style="font-size: 16px; color: #6c757d; margin-top: 0;">NGO Volunteer System</p>
            </div>
            
            <p>Hi <b>{volunteer_name}</b>,</p>
            
            <p>Great news! The administrator has <b>approved</b> your request to volunteer for the upcoming event:</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid #198754; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #212529;">{event_title}</h3>
                <p style="margin: 0;"><strong>Date:</strong> {event_date}</p>
            </div>
            
            <p>Please log in to your dashboard to view the event details, location, and coordinator contact info.</p>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="http://127.0.0.2:5000/dashboard" style="background-color: #0d6efd; color: white; padding: 12px 25px; text-decoration: none; border-radius: 50px; font-weight: bold;">View Dashboard</a>
            </div>
            
            <p style="font-size: 12px; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 20px;">
                This is an automated message from the NGO Volunteer Management System.<br>
                Thank you for volunteering and making an impact!
            </p>
        </body>
        </html>
        """
        return EmailService.send_email(to_email, subject, html)

    @staticmethod
    def send_award_email(to_email: str, volunteer_name: str, event_title: str, hours: float):
        """Pre-formatted email for awarding hours and saying thank you"""
        subject = f"🏆 Volunteer Hours Awarded: {event_title}"
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #0d6efd; margin-bottom: 5px;">Thank You!</h1>
                <p style="font-size: 16px; color: #6c757d; margin-top: 0;">NGO Volunteer System</p>
            </div>
            
            <p>Hi <b>{volunteer_name}</b>,</p>
            
            <p>Thank you so much for your dedication and hard work! The administrator has awarded you <b>{hours} hours</b> for your participation in:</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid #0dcaf0; padding: 15px; margin: 20px 0; border-radius: 4px;">
                <h3 style="margin-top: 0; margin-bottom: 0px; color: #212529;">{event_title}</h3>
            </div>
            
            <p>Your official <b>Certificate of Appreciation</b> is now available! You can download it directly from your dashboard in the project app itself.</p>
            
            <div style="text-align: center; margin: 40px 0;">
                <a href="http://127.0.0.1:5000/dashboard" style="background-color: #0d6efd; color: white; padding: 12px 25px; text-decoration: none; border-radius: 50px; font-weight: bold;">View Certificate in App</a>
            </div>
            
            <p style="font-size: 12px; color: #999; text-align: center; border-top: 1px solid #eee; padding-top: 20px;">
                This is an automated message from the NGO Volunteer Management System.<br>
                Thank you for volunteering and making a positive impact in our community!
            </p>
        </body>
        </html>
        """
        return EmailService.send_email(to_email, subject, html)
