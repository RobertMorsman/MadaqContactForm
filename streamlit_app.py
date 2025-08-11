import streamlit as st
import smtplib, ssl, re, html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="Contact Information Form", 
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #412119 0%, #6B4226 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #f0f0f0;
        text-align: center;
        margin: 0;
    }
    .stForm {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
    }
    .signature-preview {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #412119;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🍫 Madaq Signature Generator</h1>
</div>
""", unsafe_allow_html=True)

# ------------------ Enhanced Validation ------------------
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_E164_RE = re.compile(r'^\+?[1-9]\d{7,14}$')
# Dutch phone number patterns
DUTCH_MOBILE_RE = re.compile(r'^(\+31|0031|0)6[0-9]{8}$')
DUTCH_LANDLINE_RE = re.compile(r'^(\+31|0031|0)[1-9][0-9]{7,8}$')

def is_valid_email(email: str) -> bool:
    """Enhanced email validation with common domain checks."""
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return False
    
    # Check for common typos in domains
    common_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'live.com']
    domain = email.split('@')[1]
    
    # Basic domain validation
    return '.' in domain and len(domain.split('.')[1]) >= 2

def is_valid_phone(phone: str) -> bool:
    """Enhanced phone validation with Dutch number support."""
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check Dutch patterns first
    if DUTCH_MOBILE_RE.match(clean) or DUTCH_LANDLINE_RE.match(clean):
        return True
    
    # Check international E.164 format
    return PHONE_E164_RE.match(clean) is not None

def normalize_phone(phone: str) -> str:
    """Normalize phone number to international format."""
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Dutch mobile numbers
    if clean.startswith('06') and len(clean) == 10:
        return '+31' + clean[1:]
    elif clean.startswith('0') and not clean.startswith('06'):
        return '+31' + clean[1:]
    elif not clean.startswith('+'):
        return '+' + clean
    
    return clean

def build_tel_link(phone: str) -> str:
    """Create a tel: link in E.164 format."""
    normalized = normalize_phone(phone)
    return f"tel:{normalized}"

def validate_name(name: str) -> Tuple[bool, str]:
    """Validate name fields."""
    name = name.strip()
    if not name:
        return False, "Name cannot be empty"
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"
    if not re.match(r'^[a-zA-ZÀ-ÿ\s\-\'\.]+$', name):
        return False, "Name contains invalid characters"
    return True, ""

def validate_job_title(title: str) -> Tuple[bool, str]:
    """Validate job title."""
    title = title.strip()
    if not title:
        return False, "Job title cannot be empty"
    if len(title) < 2:
        return False, "Job title must be at least 2 characters long"
    return True, ""

# ------------------ Company Email Generation ------------------
def generate_company_email(first_name: str, last_name: str) -> str:
    """Generate company email with format: {first letter}.{surname}@madaq.com"""
    first = first_name.strip()
    last = last_name.strip()
    if not first or not last:
        return ""
    
    first_letter = first[0].lower()
    # Handle compound last names and special characters - keep only alphanumeric
    clean_last = re.sub(r'[^\w]', '', last).lower()
    
    return f"{first_letter}.{clean_last}@madaq.com"

# ------------------ Enhanced HTML Signature ------------------
def render_signature_html(name: str, surname: str, job_title: str, phone: str, favourite_bonbon: str) -> str:
    """Render HTML email signature with company email in correct format."""
    full_name = f"{name.strip()} {surname.strip()}".strip()
    full_name_html = html.escape(full_name)
    job_title_html = html.escape(job_title.strip())
    fav_bonbon_html = html.escape(favourite_bonbon.strip())
    phone_text_html = html.escape(phone.strip())
    tel_href = build_tel_link(phone.strip())

    # Generate company email in the required format
    company_email = generate_company_email(name, surname)
    email_text_html = html.escape(company_email)
    mailto_href = f"mailto:{company_email}"
    
    first_name = name.strip().split()[0] if name.strip() else ""
    fav_title = f"{first_name}'s favourite" if first_name else "Favoriet"
    fav_title_html = html.escape(fav_title)

    signature_html = f"""
<div style="font-family: Avenir, Arial, Helvetica, sans-serif;">
    <p style="font-size: 11pt; margin: 0 0 10px 0;">Kind regards,</p>
    
    <table style="width: 800px; font-size: 11pt; font-family: Avenir, Arial, Helvetica, sans-serif;" cellpadding="0" cellspacing="0" border="0">
    <tbody>
     <tr>
        <td style="width:82px;" width="82">
            <p style="margin: 0px; padding: 0px;">
                <a href="https://madaq.com/" target="_blank" rel="noopener">
                    <img border="0" alt="Madaq Logo" width="80" style="width:80px; height:auto; border:0;" 
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/Madaq-logo-donkerbruin-zwart.png?v=1684943708">
                </a>
            </p>
        </td>
        <td style="width: 15px;"></td>
        <td style="min-width: 200px; vertical-align: top;">
            <div style="font-weight: bold; font-size: 14pt; line-height: 16pt; color:#000000; margin-bottom: 5px;">
                {full_name_html}
            </div>
            <div style="color:#333333; font-size: 10pt; line-height: 14pt; margin-bottom: 10px;">
                {job_title_html}
            </div>
            
            <div style="margin-top: 10px;">
                <a href="https://www.facebook.com/madak.chocolatier/" target="_blank" rel="noopener" style="margin-right: 5px;">
                    <img border="0" alt="Facebook" style="border:0; height:25px; width:25px;" 
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/facebook.png?v=1684920878">
                </a>
                <a href="https://nl.linkedin.com/company/madak" target="_blank" rel="noopener" style="margin-right: 5px;">
                    <img border="0" alt="LinkedIn" style="border:0; height:25px; width:25px;" 
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/linkedin.png?v=1684920878">
                </a>
                <a href="https://www.instagram.com/madaqchocolates/" target="_blank" rel="noopener">
                    <img border="0" alt="Instagram" style="border:0; height:25px; width:25px;" 
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/instagram.png?v=1684920878">
                </a>
            </div>
        </td>
        <td style="width: 2px; border-right: 2px solid #412119; height: 80px;"></td>
        <td style="width: 15px;"></td>
        <td style="min-width: 175px; vertical-align: top;">
            <div style="font-size: 10pt; line-height: 14pt;">
                <div style="margin-bottom: 3px;">
                    <a href="{tel_href}" style="text-decoration:none; color:#333333;">{phone_text_html}</a>
                </div>
                <div style="margin-bottom: 3px;">
                    <a href="{mailto_href}" style="text-decoration: none; color:#333333;">{email_text_html}</a>
                </div>
                <div style="margin-bottom: 3px;">
                    <a href="https://www.madaq.com" style="text-decoration: none; color:#333333;">www.madaq.com</a>
                </div>
                <div style="color:#333333;">
                    Florijnweg 23B<br>
                    6883 JN Velp
                </div>
            </div>
        </td>
        <td style="width: 2px; border-right: 2px solid #412119; height: 80px;"></td>
        <td style="width: 15px;"></td>
        <td style="width:67px;" width="67">
            <p style="margin: 0px; padding: 0px;">
                <a href="https://madaq.com/collections/bonbons-bestellen/products/moroccan-coffee-2" target="_blank" rel="noopener">
                    <img border="0" alt="Favorite Bonbon" width="67" style="width:67px; height:auto; border:0;" 
                         src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/Madak_yuzu_caramel_04d2bbd8-5ff9-47b6-8c58-9658179651a8.png?v=1688635076">
                </a>
            </p>
        </td>
        <td style="width: 15px;"></td>
        <td style="width: 160px; vertical-align: top;">
            <div style="color:#412119; font-weight: bold; font-size: 14pt; line-height: 16pt; margin-bottom: 5px;">
                {fav_title_html}
            </div>
            <div style="color:#412119; font-size: 10pt; line-height: 14pt; margin-bottom: 8px;">
                {fav_bonbon_html}
            </div>
            <div style="color:#412119; font-size: 10pt; line-height: 14pt;">
                What's yours?
            </div>
        </td>
     </tr>
    </tbody>
    </table>
</div>
"""
    return signature_html

# ------------------ Email Sending with Retry Logic ------------------
def send_email_with_signature(name: str, surname: str, email: str, phone: str, 
                             job_title: str, favourite_bonbon: str) -> bool:
    """Send email with signature attachment and retry logic."""
    cfg = init_email_config()
    if not all([cfg.get("smtp_server"), cfg.get("smtp_port"), 
                cfg.get("sender_email"), cfg.get("sender_password"), 
                cfg.get("recipient_email")]):
        return False

    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Email sending attempt {attempt + 1}")
            
            # Create message
            msg = MIMEMultipart("mixed")
            msg["From"] = cfg["sender_email"]
            msg["To"] = cfg["recipient_email"]
            msg["Subject"] = f"New Employee Contact Info - {name} {surname}"
            msg["Reply-To"] = email
            
            # Enhanced email body
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            normalized_phone = normalize_phone(phone)
            company_email = generate_company_email(name, surname)
            
            body = f"""New Employee Contact Form Submission

Submission Details:
==================
Date & Time: {timestamp}
Personal Email: {email}

Employee Information:
====================
Full Name: {name} {surname}
Personal Email: {email}
Phone Number: {phone} (normalized: {normalized_phone})
Job Title: {job_title}
Favourite Bonbon: {favourite_bonbon}

Generated Company Email: {company_email}

Next Steps for r.morsman@madaq.com:
==================================
1. Create company email account: {company_email}
2. Set up employee access and accounts  
3. Send signature file to employee (attached HTML file is ready to use)
4. Add to company directory

The attached HTML signature file contains the correctly formatted 
company email address and is ready for use.

Best regards,
Madaq Contact Form System
"""
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Generate and attach signature with company email
            signature_html = render_signature_html(name, surname, job_title, phone, favourite_bonbon)
            attachment_part = MIMEText(signature_html, "html", "utf-8")

            # Safe filename generation
            safe_name = re.sub(r'[^a-zA-Z0-9]', '', f"{name}{surname}")
            if not safe_name:
                safe_name = "signature"
            
            attachment_part.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"{safe_name}_signature.html"
            )
            msg.attach(attachment_part)

            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(cfg["sender_email"], cfg["sender_password"])
                server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())

            logger.info("Email sent successfully")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            st.error("❌ Email authentication failed. Please check credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                st.error(f"❌ Email sending failed after {max_retries} attempts: {e}")
                return False
            st.warning(f"⚠️ Attempt {attempt + 1} failed, retrying...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            st.error(f"❌ Unexpected error: {e}")
            return False
    
    return False

# ------------------ Main Form ------------------
# Create tabs for better organization
tab1, tab2 = st.tabs(["📝 Contact Form", "👀 Preview Signature"])

with tab1:
    with st.form("contact_form", clear_on_submit=False):
        st.markdown("### 📋 Employee Information")
        st.markdown("*All fields are required*")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                "First Name *", 
                placeholder="Enter your first name",
                help="Your first name as it should appear in the signature"
            )
            email = st.text_input(
                "Personal Email *", 
                placeholder="your.email@example.com",
                help="Your personal email address"
            )
            job_title = st.text_input(
                "Job Title *", 
                placeholder="e.g., Chocolate Artisan, Sales Manager",
                help="Your official job title at Madaq"
            )
        
        with col2:
            surname = st.text_input(
                "Last Name *", 
                placeholder="Enter your last name",
                help="Your last name as it should appear in the signature"
            )
            phone = st.text_input(
                "Phone Number *", 
                placeholder="+31 6 12345678 or 06 12345678",
                help="Dutch mobile: 06 xxxxxxxx, International: +XX XXX XXX XXXX"
            )
            favourite_bonbon = st.text_input(
                "Favourite Bonbon *", 
                placeholder="e.g., Moroccan Coffee, Dark Sea Salt Caramel",
                help="Your favorite Madaq bonbon flavor"
            )

        # Remove company email preview since it's handled by r.morsman@madaq.com
        # if name.strip() and surname.strip():
        #     company_email = generate_company_email(name, surname)
        #     st.info(f"🏢 **Your company email will be:** {company_email}")

        submitted = st.form_submit_button("🚀 Submit & Generate Signature", use_container_width=True)

        if submitted:
            # Comprehensive validation
            errors = []
            
            # Name validation
            name_valid, name_error = validate_name(name)
            if not name_valid:
                errors.append(f"First Name: {name_error}")
            
            surname_valid, surname_error = validate_name(surname)
            if not surname_valid:
                errors.append(f"Last Name: {surname_error}")
            
            # Email validation
            if not email.strip():
                errors.append("Personal email is required")
            elif not is_valid_email(email):
                errors.append("Please enter a valid email address")
            
            # Phone validation
            if not phone.strip():
                errors.append("Phone number is required")
            elif not is_valid_phone(phone):
                errors.append("Please enter a valid phone number (Dutch: 06 xxxxxxxx or International: +XX XXX XXX XXXX)")
            
            # Job title validation
            job_valid, job_error = validate_job_title(job_title)
            if not job_valid:
                errors.append(f"Job Title: {job_error}")
            
            # Bonbon validation
            if not favourite_bonbon.strip():
                errors.append("Favourite bonbon is required")

            if errors:
                st.error("**Please fix the following errors:**")
                for error in errors:
                    st.error(f"• {error}")
            else:
                # Store form data in session state for preview
                st.session_state.form_data = {
                    'name': name,
                    'surname': surname,
                    'email': email,
                    'phone': phone,
                    'job_title': job_title,
                    'favourite_bonbon': favourite_bonbon
                }
                
                with st.spinner("📤 Sending your information and generating signature..."):
                    success = send_email_with_signature(
                        name, surname, email, phone, job_title, favourite_bonbon
                    )
                
                if success:
                    st.success("✅ **Success!** Your information has been submitted!")
                    st.balloons()
                    st.info("💼 **Next Steps:** r.morsman@madaq.com will create your company email account and send you the signature file.")
                else:
                    st.error("❌ There was an error sending your information. Please try again or contact IT support.")

with tab2:
    st.markdown("### 👀 Signature Preview")
    
    if 'form_data' in st.session_state:
        data = st.session_state.form_data
        st.success("📧 **Preview of your email signature:**")
        st.info("ℹ️ **Company email format:** {first letter}.{surname}@madaq.com")
        
        signature_html = render_signature_html(
            data['name'], data['surname'], data['job_title'], 
            data['phone'], data['favourite_bonbon']
        )
        
        st.markdown('<div class="signature-preview">', unsafe_allow_html=True)
        st.markdown(signature_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Download button for signature
        st.download_button(
            label="📥 Download Signature HTML",
            data=signature_html,
            file_name=f"{data['name']}{data['surname']}_signature.html",
            mime="text/html",
            use_container_width=True
        )
    else:
        st.info("👆 **Fill out the form first** to see your signature preview here.")
        st.markdown("""
        **What happens after you submit:**
        1. 📧 r.morsman@madaq.com receives your information and signature file
        2. 🏢 Company email account is created: {first letter}.{surname}@madaq.com
        3. 📨 You receive the signature file via email (ready to use!)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8em;">
    <p>🍫 Made with love by Madaq Digital Team | Need help? Contact IT support</p>
</div>
""", unsafe_allow_html=True)
