import os
import sys
import smtplib
import pandas as pd
from dotenv import load_dotenv
from src.exception import CustomException
from langchain_core.tools import tool
from ddgs import DDGS
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from langchain_groq import ChatGroq

load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "Dravin Kumar Sharma")
RESUME_PATH = "data/Dravin_AI_Resume.pdf"

EMAIL_TEMPLATE = """\
Subject: AI/Agentic AI Engineer — Interested in {company_name}

Hi {first_name},

I've been following {company_name} and noticed you are currently working on {company_product_or_ai_feature}.

In my experience, as these systems scale, engineering teams often hit bottlenecks with {company_pain_points}.

I specialize in solving exactly this. I build production-grade Agentic AI systems using Python, FastAPI, and LangGraph. Recently, I built DataFoundry—an autonomous AI data engineer—where I designed the architecture from scratch, focusing heavily on robust state management, guardrails, and asynchronous processing to keep multi-agent workflows reliable.

I am currently looking for a full-time, fully remote/full time role where I can build and optimize these types of agentic pipelines for your team.

Are you open to a quick chat to discuss how my background aligns with your current roadmap? I have attached my resume, and you can view my architecture work on GitHub here:- https://github.com/Str1nX03.

Best regards,

{sender_name}
"""

def get_llm():

    try:

        groq_api_key = os.getenv("GROQ_API_KEY")

        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.1,
            groq_api_key=groq_api_key
        )
        
        return llm

    except Exception as e:
        raise CustomException(e, sys)

def get_data(file_path: str = "data/HR_Contacts_List.xlsx") -> dict[str, list[str]]:
    """
    Reads the HR contacts Excel sheet and extracts three parallel lists.
    Args:
        file_path: Path to the Excel file containing HR contact data.
    Returns:
        A dictionary with keys "hr_names", "company_names", and "emails",
        each mapping to a list of strings.
    """
    try:

        data = {"hr_names": [], "company_names": [], "emails": []}
        df = pd.read_excel(file_path).fillna('')

        for index, row in df.iterrows():

            data["hr_names"].append(str(row["HR Name"]))
            data["company_names"].append(str(row["Company Name"]))
            data["emails"].append(str(row["Email"]))
        
        return data

    except Exception as e:
        raise CustomException(e, sys)

@tool
def research_company(company_name: str) -> list[list[str]]:
    """
    Researches a company's recent news, AI initiatives, products, or engineering challenges latest to 2026.
    Args:
        company_name: The name of the company to research.
    Returns:
        A list of lists of strings containing the research results.
    """
    try:

        query = f"{company_name} recent news about their AI initiatives and product based company latest to 2026"
        results = DDGS().text(query, max_results = 3)
        formatted_result = []

        for i in range(len(results)):
            formatted_result.append([results[i]["title"], results[i]["body"]])

        return formatted_result

    except Exception as e:
        raise CustomException(e, sys)

@tool
def send_email(
    recipient_email: str,
    hr_name: str,
    company_name: str,
    company_product_or_ai_feature:str,
    company_pain_points: str
) -> str:
    """
    Sends a personalized cold email with a resume attachment via Gmail SMTP.
    Args:
        recipient_email: The email address of the HR contact.
        hr_name: The name of the HR contact.
        company_name: The name of the company.
        company_product_or_ai_feature: A specific product or AI feature the company is scaling (e.g., 'their customer service LLM agent').
        company_pain_points: Specific engineering pain points (e.g., 'latency issues in high-throughput RAG pipelines').
    Returns:
        A string indicating success or failure.
    """

    try:

        first_name = hr_name.split()[0] if hr_name else "there"
        email_content = EMAIL_TEMPLATE.format(
            first_name=first_name,
            company_name=company_name,
            company_product_or_ai_feature=company_product_or_ai_feature,
            company_pain_points=company_pain_points,
            sender_name=SENDER_NAME
        )

        lines = email_content.split("\n", 1)
        subject = lines[0].replace("Subject: ", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        recipient_email = recipient_email.strip()
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if not os.path.exists(RESUME_PATH):
            return f"Error: Resume not found at {RESUME_PATH}"
            
        with open(RESUME_PATH, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        filename = os.path.basename(RESUME_PATH)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}",
        )
        msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())

        return f"Successfully sent email to {recipient_email}"

    except Exception as e:
        raise CustomException(e, sys)

def send_final_email(recipient_email: str, subject: str, body: str) -> str:
    """
    Sends a manually approved or edited email with the resume attachment.
    """
    try:
        recipient_email = recipient_email.strip()
        
        msg = MIMEMultipart()
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if not os.path.exists(RESUME_PATH):
            return f"Error: Resume not found at {RESUME_PATH}"
            
        with open(RESUME_PATH, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        filename = os.path.basename(RESUME_PATH)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}",
        )
        msg.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipient_email, msg.as_string())

        return f"Successfully sent email to {recipient_email}"

    except Exception as e:
        raise CustomException(e, sys)