import streamlit as st
import smtplib, ssl, re, html, unicodedata
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(page_title="Contact Information Form", page_icon="✉️")
st.title("Contact Information Form")

# ------------------ Validatie ------------------
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_E164_RE = re.compile(r'^\+?[1-9]\d{7,14}$')

def is_valid_email(email: str) -> bool:
    return EMAIL_RE.match(email.strip()) is not None

def is_valid_phone(phone: str) -> bool:
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    return PHONE_E164_RE.match(clean) is not None

def build_tel_link(phone: str) -> str:
    clean = re.sub(r'[\s\-\(\)]', '', phone)
    if not clean.startswith('+') and clean.startswith('0'):
        if clean.startswith('06'):
            clean = '+31' + clean[1:]
        else:
            clean = '+' + clean.lstrip('0')
    if not clean.startswith('+'):
        clean = '+' + clean
    return f"tel:{clean}"

# ------------------ Afleiding e-mail ------------------
def generate_company_email(first_name: str, last_name: str) -> str:
    first = first_name.strip()
    last = last_name.strip()
    if not first or not last:
        return ""
    first_letter = first[0].lower()
    clean_last = re.sub(r'[\s\-]', '', last).lower()
    return f"{first_letter}.{clean_last}@madaq.com"

# ------------------ Config (uit secrets) ------------------
@st.cache_resource
def init_email_config():
    cfg = st.secrets.get("email", {})
    EMAIL_CONFIG = {
        "smtp_server": cfg.get("smtp_server", "smtp.gmail.com"),
        "smtp_port": int(cfg.get("smtp_port", 587)),
        "sender_email": cfg.get("sender_email", ""),
        "sender_password": cfg.get("sender_password", ""),
        "recipient_email": "r.morsman@madaq.com",
    }
    return EMAIL_CONFIG

# ------------------ HTML-handtekening renderer ------------------
def render_signature_html(name, surname, job_title, phone, favourite_bonbon):
    full_name = f"{name.strip()} {surname.strip()}".strip()
    full_name_html = html.escape(full_name)
    job_title_html = html.escape(job_title.strip())
    fav_bonbon_html = html.escape(favourite_bonbon.strip())
    phone_text_html = html.escape(phone.strip())
    tel_href = build_tel_link(phone.strip())

    derived_email = generate_company_email(name, surname)
    email_text_html = html.escape(derived_email)
    mailto_href = f"mailto:{derived_email}"
    fav_title = f"Favoriet van {name.strip().split()[0]}" if name.strip() else "Favoriet"

    signature_html = f"""
<span style="font-size: 11pt; font-family: Avenir, Arial, Helvetica, sans-serif;">Met vriendelijke groet,<span/>
	<br/>
	<br/>
<table style="width: 800px; font-size: 11pt; font-family: Avenir, Arial, Helvetica, sans-serif;" cellpadding="0" cellspacing="0" border="0">
<tbody>
 <tr>
    <td style="width:82px;" width="82">
        <p style="margin: 0px; padding: 0px;">
            <a href="https://madaq.com/" target="_blank"><img border="0" alt="Logo" width="80" style="width:80px; height:auto; border:0;" src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/Madaq-logo-donkerbruin-zwart.png?v=1684943708"></a>
        </p>
    </td>
    <td style="width: 15px;"></td>
    <td style="min-width: 200px;">
        <span style="font-family: Avenir, Arial, Helvetica, sans-serif; color:#000000; font-weight: bold; font-size: 14pt; line-height: 11pt;">{full_name_html}&nbsp;</span>
        <span style="font-family: Avenir, Arial, Helvetica, sans-serif; color:#333333; font-size: 10pt; line-height: 15pt;"><br>
        {job_title_html}</span>
        <p style="margin-bottom: 0px; margin-top: 10px; padding: 0px;">
            <span><a href="https://www.facebook.com/madak.chocolatier/" target="_blank" rel="noopener"><img border="0" width="16" alt="facebook icon" style="border:0; height:25px; width:25px" src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/facebook.png?v=1684920878"></a>&nbsp;</span><span><a href="https://nl.linkedin.com/company/madak" target="_blank" rel="noopener"><img border="0" width="16" alt="linkedin icon" style="border:0; height:25px; width:25px" src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/linkedin.png?v=1684920878"></a>&nbsp;</span><span><a href="https://www.instagram.com/madaqchocolates/" target="_blank" rel="noopener"><img border="0" width="16" alt="instagram icon" style="border:0; height:25px; width:25px" src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/instagram.png?v=1684920878"></a>&nbsp;</span>
        </p>
    </td>
    <td style="width: 0px; border-right: 2px solid #412119"></td>
    <td style="width: 15px;"></td>
    <td style="width: 15px;"></td>
    <td style="min-width: 175px;">
        <p style="FONT-FAMILY: Avenir, Arial, Helvetica, sans-serif; padding: 0px; font-size: 10pt; line-height: 14pt; margin-bottom: 0px;">
            <span>
                <a href="{tel_href}" style="text-decoration:none; font-size: 10pt; color:#333333;">{phone_text_html}</a>
                <span><br></span>
            </span>
             <span style="FONT-FAMILY: Avenir, Arial, Helvetica, sans-serif; font-size: 10pt; line-height: 14pt;">
                <a href="{mailto_href}" style="font-size: 10pt; color:#333333; text-decoration: none;"><span style="text-decoration: none; font-size: 10pt;  line-height: 14pt; color:#333333; FONT-FAMILY: Avenir, Arial, Helvetica, sans-serif;">{email_text_html}</span></a>
                <span><br></span>
            </span>
            <span>
                <a href="https://www.madaq.com" style="font-size: 10pt; color:#333333; text-decoration: none;"><span style="text-decoration: none; font-size: 10pt;  line-height: 14pt; color:#333333; FONT-FAMILY: Avenir, Arial, Helvetica, sans-serif;">www.madaq.com</span></a>
                <span><br></span>
            </span>
            <span>
                <span style="font-size: 10pt; color:#333333;"> <span>Florijnweg 23B <br>
                6883 JN Velp&nbsp; &nbsp; &nbsp;</span> </span>
            </span>
        </p>
    </td>
    <td style="width: 0px; border-right: 2px solid #412119"></td>
    <td style="width: 15px;"></td>
    <td style="width: 15px;"></td>
        <td style="width:82px;" width="82">
        <p style="margin: 0px; padding: 0px;">
            <a href="https://madaq.com/collections/bonbons-bestellen/products/moroccan-coffee-2"><img border="0" alt="Logo" width="67" style="width:67px; height:auto; border:0;" src="https://cdn.shopify.com/s/files/1/0729/8203/6780/files/Madak_yuzu_caramel_04d2bbd8-5ff9-47b6-8c58-9658179651a8.png?v=1688635076"></a>
        </p>
        </td>
        <td style="width: 15px;"></td>
        <td style="width: 160px;">
        <span style="font-family: Avenir, Arial, Helvetica, sans-serif; color:#412119; font-weight: bold; font-size: 14pt; line-height: 15pt;">{html.escape(fav_title)}</span>
        <span style="font-family: Avenir, Arial, Helvetica, sans-serif; color:#412119; font-style: sans-serif; font-size: 10pt; line-height: 15pt;">{fav_bonbon_html}</span>
            <br/>
        <span style="font-family: Avenir, Arial, Helvetica, sans-serif; color:#412119; font-style: sans-serif; font-size: 10pt; line-height: 20pt;">What's yours?</span>
    </td>
 </tr>
</tbody>
</table>
"""
    return signature_html

# ------------------ Mailen met bijlage ------------------
def send_email_with_signature(name, surname, email, phone, job_title, favourite_bonbon):
    cfg = init_email_config()
    if not all([cfg["smtp_server"], cfg["smtp_port"], cfg["sender_email"], cfg["sender_password"], cfg["recipient_email"]]):
        st.error("E-mailconfiguratie ontbreekt of is onvolledig. Vul .streamlit/secrets.toml in onder [email].")
        return False

    try:
        st.info("📧 Verbinden met SMTP-server…")
        context = ssl.create_default_context()

        msg = MIMEMultipart("mixed")
        msg["From"] = cfg["sender_email"]
        msg["To"] = cfg["recipient_email"]
        msg["Subject"] = f"Je moet weer aan het werk - {name} {surname}"

        body = f"""New contact form submission received:

Date & Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Contact Details:
================
Name: {name}
Surname: {surname}
Email: {email}
Phone Number: {phone}
Job Title: {job_title}
Favourite bonbon: {favourite_bonbon}

Best regards,
Je digitale maatje
"""
        msg.attach(MIMEText(body, "plain", "utf-8"))

        signature_html = render_signature_html(name, surname, job_title, phone, favourite_bonbon)
        attachment_part = MIMEText(signature_html, "html", "utf-8")

        # Accentverwijdering voor bestandsnaam
        def remove_accents(input_str):
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

        raw_name = f"{name}{surname}"
        normalized = remove_accents(raw_name)
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', normalized)
        if not safe_name:
            safe_name = "signature"

        attachment_part.add_header(
            "Content-Disposition",
            "attachment",
            filename=f"{safe_name}_signature.html"
        )

        msg.attach(attachment_part)

        with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            st.info("🔑 Inloggen…")
            server.login(cfg["sender_email"], cfg["sender_password"])
            st.info("📤 Verzenden…")
            server.sendmail(cfg["sender_email"], cfg["recipient_email"], msg.as_string())

        st.success("✅ E-mail verzonden met bijlage!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        st.error(f"❌ Gmail login failed: {e}")
        st.info("Controleer 2FA en je app password in secrets.")
        return False
    except smtplib.SMTPException as e:
        st.error(f"❌ SMTP Error: {e}")
        return False
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        return False

# ------------------ Formulier ------------------
with st.form("contact_form"):
    st.write("**Please fill in all required fields:**")

    name = st.text_input("Name *", placeholder="Enter your first name")
    surname = st.text_input("Surname *", placeholder="Enter your last name")
    email = st.text_input("Personal Email *", placeholder="your.email@example.com")
    phone = st.text_input("Phone Number *", placeholder="+31 6 12345678")
    job_title = st.text_input("Job Title *", placeholder="Your current job title")
    favourite_bonbon = st.text_input("Favourite bonbon *", placeholder="Your favourite bonbon flavour")

    submitted = st.form_submit_button("Submit Contact Information")

    if submitted:
        errors = []
        if not name.strip():
            errors.append("Name is required")
        if not surname.strip():
            errors.append("Surname is required")
        if not email.strip():
            errors.append("Email is required")
        elif not is_valid_email(email):
            errors.append("Please enter a valid email address")
        if not phone.strip():
            errors.append("Phone number is required")
        elif not is_valid_phone(phone):
            errors.append("Please enter a valid phone number (international format)")
        if not job_title.strip():
            errors.append("Job title is required")
        if not favourite_bonbon.strip():
            errors.append("Favourite bonbon is required")

        if errors:
            st.error("Please fix the following errors:")
            for error in errors:
                st.error(f"• {error}")
        else:
            with st.spinner("Sending your information and signature..."):
                ok = send_email_with_signature(name, surname, email, phone, job_title, favourite_bonbon)
            if ok:
                st.balloons()
            else:
                st.error("❌ There was an error sending your information. Please try again.")
