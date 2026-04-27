import os
import sys
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from tqdm import tqdm
from src.tools import get_data, get_llm, research_company, send_email, EMAIL_TEMPLATE, SENDER_NAME
from src.exception import CustomException

load_dotenv()

llm = get_llm()
tools = [research_company, send_email]
agent_executor = create_react_agent(llm, tools)

# For interactive mode: A dedicated research agent that doesn't send emails
research_agent = create_react_agent(llm, [research_company])

def get_email_draft(hr_name: str, company_name: str, email: str, company_cache: dict) -> dict:
    """
    Generates a draft for a single contact. Uses cache if available, otherwise researches using AI.
    """
    try:
        if company_name in company_cache:
            product = company_cache[company_name]["product"]
            pain_points = company_cache[company_name]["pain_points"]
            source = "cache"
        else:
            # Manually invoke the research tool instead of using an agent loop (more reliable for Groq)
            try:
                research_data = research_company.invoke({"company_name": company_name})
                research_context = str(research_data)
            except Exception:
                research_context = "No specific recent news found."

            prompt = (
                f"Research Context for {company_name}:\n{research_context}\n\n"
                f"Based on this, identify:\n"
                f"1. A specific technical product or AI feature {company_name} is scaling.\n"
                f"2. A likely engineering pain point they are facing.\n"
                f"Return ONLY a JSON-formatted string with keys 'product' and 'pain_points'.\n"
                f"Example: {{\"product\": \"customer support RAG pipeline\", \"pain_points\": \"high latency in vector retrieval\"}}"
            )
            response = llm.invoke([("user", prompt)])
            content = response.content
            
            # Simple JSON extraction
            import json
            import re
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                product = data.get("product", "[Company Product]")
                pain_points = data.get("pain_points", "[Company Pain Points]")
            else:
                product = "[Company Product]"
                pain_points = "[Company Pain Points]"
            
            # Update cache for the caller
            company_cache[company_name] = {"product": product, "pain_points": pain_points}
            source = "ai"

        first_name = hr_name.split()[0] if hr_name else "there"
        email_content = EMAIL_TEMPLATE.format(
            first_name=first_name,
            company_name=company_name,
            company_product_or_ai_feature=product,
            company_pain_points=pain_points,
            sender_name=SENDER_NAME
        )
        
        # Split into subject and body
        lines = email_content.split("\n", 1)
        subject = lines[0].replace("Subject: ", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        
        return {
            "hr_name": hr_name,
            "company": company_name,
            "email": email,
            "subject": subject,
            "body": body,
            "product": product,
            "pain_points": pain_points,
            "source": source
        }
    except Exception as e:
        raise CustomException(e, sys)

def run_agent(dry_run: bool = False, progress_callback: callable = None) -> dict:
    """
    Orchestrates the cold email campaign using a LangGraph ReAct agent to research and email HR contacts.

    Args:
        dry_run (bool, optional): If True, returns generated preview emails without invoking the AI or sending via SMTP.
        progress_callback (callable, optional): Callback for real-time stats (total, successful, failed, results).

    Returns:
        dict: Execution summary including status, counts (total_processed, successful, failed), and per-contact results.
    """
    try:
        data = get_data()
        hr_names = data["hr_names"]
        company_names = data["company_names"]
        emails = data["emails"]
        
        results = []
        successful_count = 0

        if dry_run:
            for hr_name, company_name, email in zip(hr_names, company_names, emails):
                first_name = hr_name.split()[0] if hr_name else "there"
                email_content = EMAIL_TEMPLATE.format(
                    first_name=first_name,
                    company_name=company_name,
                    company_product_or_ai_feature="[Company Product or AI Feature]",
                    company_pain_points="[Company Pain Points]",
                    sender_name=SENDER_NAME
                )
                results.append({
                    "hr_name": hr_name,
                    "company": company_name,
                    "email": email,
                    "status": "dry_run",
                    "error": None,
                    "final_message": email_content
                })
            return {"status": "completed", "total_processed": len(results), "successful": len(results), "failed": 0, "results": results}

        company_cache = {}

        pbar = tqdm(zip(hr_names, company_names, emails), total=len(hr_names), desc="Sending Emails")
        for hr_name, company_name, email in pbar:
            if company_name in company_cache:
                cached_data = company_cache[company_name]
                try:
                    
                    result_msg = send_email.invoke({
                        "recipient_email": email,
                        "hr_name": hr_name,
                        "company_name": company_name,
                        "company_product_or_ai_feature": cached_data["product"],
                        "company_pain_points": cached_data["pain_points"]
                    })
                    status = "sent" if "Successfully sent email" in result_msg else "failed"
                    error_msg = None if status == "sent" else result_msg
                    final_msg = f"[Cached Research Used]\n{result_msg}"
                except Exception as e:
                    status = "failed"
                    error_msg = str(e)
                    final_msg = error_msg
                
                if status == "sent":
                    successful_count += 1
            else:
                prompt = (
                    f"Your MISSION is to write a highly personalized and VERY CONVINCING cold email to {hr_name} at {company_name} ({email}).\n\n"
                    f"STEP 1: RESEARCH\n"
                    f"Use 'research_company' to find what {company_name} is working on recently.\n"
                    f"If the tool fails or returns no useful info, use your internal knowledge about the company.\n\n"
                    f"STEP 2: IDENTIFY CONVINCING REASONS\n"
                    f"- Pick a specific, high-impact product or AI feature they are scaling.\n"
                    f"- Deduce a TECHNICAL engineering pain point they might be facing.\n\n"
                    f"STEP 3: EXECUTE\n"
                    f"Call 'send_email' EXACTLY ONCE with these specific details.\n\n"
                    f"CRITICAL RULE: STOP immediately after receiving the success message."
                )
                
                response = agent_executor.invoke({
                    "messages": [("user", prompt)]
                })
                
                status = "failed"
                error_msg = "Agent did not call the send_email tool or it failed."
                final_msg = response["messages"][-1].content
                
                for msg in response["messages"]:
                    if msg.type == "tool":
                        if "Successfully sent email" in msg.content:
                            status = "sent"
                            successful_count += 1
                            error_msg = None
                        elif "Error:" in msg.content or "Failed to send email" in msg.content:
                            error_msg = msg.content
                    elif msg.type == "ai" and getattr(msg, "tool_calls", None):
                        for tc in msg.tool_calls:
                            if tc["name"] == "send_email":
                                args = tc["args"]
                                company_cache[company_name] = {
                                    "product": args.get("company_product_or_ai_feature", "[Product]"),
                                    "pain_points": args.get("company_pain_points", "[Pain Points]")
                                }
            
            results.append({
                "hr_name": hr_name,
                "company": company_name,
                "email": email,
                "status": status,
                "error": error_msg,
                "final_message": final_msg
            })
            
            pbar.set_postfix({"Sent": successful_count, "Failed": len(results) - successful_count})
            
            if progress_callback:
                progress_callback({
                    "total": len(hr_names),
                    "successful": successful_count,
                    "failed": len(results) - successful_count,
                    "results": results
                })

        return {
            "status": "completed", 
            "total_processed": len(results),
            "successful": successful_count,
            "failed": len(results) - successful_count,
            "results": results
        }

    except Exception as e:
        raise CustomException(e, sys)