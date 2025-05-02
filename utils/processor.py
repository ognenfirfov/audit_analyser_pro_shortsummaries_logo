from openai import OpenAI
import fitz
import os
from tenacity import retry, wait_random_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError, APIError

# Initialize OpenAI client with environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@retry(
    wait=wait_random_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
def ask_openai(prompt):
    """Send a prompt to OpenAI with retry logic for robustness."""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

def extract_text(pdf_path):
    """Extracts full text from a PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)

def summarize_audit(text, filename):
    """Generate a structured and concise summary of the audit."""
    prompt = f"""
You are a senior auditor. Analyze the following audit report and summarize it in a clear and concise format. The response must not exceed 1 page, and should follow this structure:

### Audit of {filename}

1. Audit Topic
- [Short name or subject of the audit]

2. Main Findings
- 2–4 bullet points summarizing key issues or risks identified

3. Measures Proposed
- 2–4 actionable responses or mitigation steps

4. Future Steps
- 2–3 bullets outlining next steps or follow-up actions

AUDIT TEXT:
{text[:8000]}
"""
    return ask_openai(prompt)

def compare_audits(summaries):
    """Compare audits to identify patterns and differences."""
    joined = "\n\n".join(summaries)
    prompt = (
        "Compare the following audit summaries. Provide a structured comparison that includes:\n"
        "- Common audit themes or topics\n"
        "- Differences in findings or audit responses\n"
        "- Areas of improvement shared between audits\n\n"
        f"{joined}"
    )
    return ask_openai(prompt)

def extract_learnings(summaries):
    """Derive cross-audit insights for future audit planning."""
    joined = "\n\n".join(summaries)
    prompt = (
        "From these structured audit summaries, extract 3–5 key audit learnings or best practices "
        "that can be applied to future audits.\n\n"
        f"{joined}"
    )
    return ask_openai(prompt)

def analyze_audits(paths, filenames):
    """Main processing function to analyze all uploaded audits."""
    summaries = []
    for path, name in zip(paths, filenames):
        text = extract_text(path)
        summary = summarize_audit(text, name)
        summaries.append(summary)

    comparison = compare_audits(summaries)
    learnings = extract_learnings(summaries)

    full_text = "=== AUDIT SUMMARIES ===\n\n" + "\n\n".join(summaries)
    full_text += "\n\n=== COMPARISON ===\n\n" + comparison
    full_text += "\n\n=== LEARNINGS ===\n\n" + learnings

    return summaries, comparison, learnings, full_text
