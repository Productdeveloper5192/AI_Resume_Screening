"""Generate sample resumes (PDF/DOCX/TXT) and a matching requirements template.

Run from the resume_screener folder:
    .venv\\Scripts\\python.exe test_data\\generate_test_data.py
Needs fpdf2 (pip install fpdf2) for the PDF resumes.
"""

import json
from pathlib import Path

from docx import Document
from fpdf import FPDF

OUT = Path(__file__).parent / "resumes"
TEMPLATES_FILE = Path(__file__).parent.parent / "templates.json"

TEMPLATE_NAME = "Data Scientist (Test)"
TEMPLATE = {
    "role_title": "Data Scientist",
    "must_have": "Python, SQL, Machine Learning, AWS",
    "nice_to_have": "PyTorch, Docker, LLMs / Generative AI",
    "min_years": 3,
    "education": "Bachelor's degree in Computer Science, Statistics, Mathematics or related field",
    "other": "Must have deployed at least one ML model to production.",
    "job_description": (
        "We are hiring a Data Scientist to build and deploy machine learning models for "
        "customer analytics (churn, recommendations, forecasting). You will own models end to end: "
        "data extraction with SQL, feature engineering and modelling in Python, and deployment on AWS. "
        "Experience with deep learning (PyTorch), containerisation (Docker) and LLM-based features is a plus."
    ),
}

# Each resume: (filename, format, sections). Sections are (heading, [lines]).
RESUMES = [
    (
        "01_Ananya_Iyer.pdf",
        "pdf",
        "Ananya Iyer",
        "Senior Data Scientist | Bangalore | ananya.iyer@example.com",
        [
            ("Summary", [
                "Data scientist with 5+ years building and deploying ML models for e-commerce and fintech.",
            ]),
            ("Experience", [
                "Senior Data Scientist, Flipkart (2022 - Present)",
                "- Built a churn prediction model (XGBoost, Python) that cut monthly churn by 12%.",
                "- Deployed models on AWS SageMaker with Docker containers and CI/CD; serves 2M predictions/day.",
                "- Wrote complex SQL on Redshift for feature pipelines; built an LLM-based review summariser.",
                "Data Scientist, Razorpay (2020 - 2022)",
                "- Developed fraud-detection models in PyTorch; reduced false positives by 18%.",
                "- Built Airflow + SQL pipelines on AWS (S3, Lambda, Glue).",
            ]),
            ("Skills", [
                "Python, SQL, scikit-learn, XGBoost, PyTorch, AWS (SageMaker, S3, Lambda, Redshift), Docker, "
                "Airflow, LangChain, Git",
            ]),
            ("Education", ["B.Tech, Computer Science - IIT Madras, 2020"]),
        ],
    ),
    (
        "02_Karthik_Reddy.docx",
        "docx",
        "Karthik Reddy",
        "Data Scientist | Hyderabad | karthik.reddy@example.com",
        [
            ("Summary", ["Data scientist with 4 years in retail analytics and demand forecasting."]),
            ("Experience", [
                "Data Scientist, Walmart Global Tech (2021 - Present)",
                "- Built demand-forecasting models in Python (LightGBM, Prophet) for 3,000 stores.",
                "- Deployed forecasting service to production on AWS (EC2, S3) with scheduled retraining.",
                "- Wrote SQL (Snowflake) for all feature extraction; mentored 2 junior analysts.",
                "Junior Data Analyst, Mu Sigma (2020 - 2021)",
                "- SQL reporting and Python automation for a CPG client.",
            ]),
            ("Skills", ["Python, SQL, Pandas, scikit-learn, LightGBM, AWS (EC2, S3), Snowflake, Tableau, Git"]),
            ("Education", ["B.Sc Statistics - Osmania University, 2020"]),
        ],
    ),
    (
        "03_Sneha_Patel.pdf",
        "pdf",
        "Sneha Patel",
        "Machine Learning Engineer | Pune | sneha.patel@example.com",
        [
            ("Summary", ["ML engineer with 3.5 years in NLP and recommendation systems on Google Cloud."]),
            ("Experience", [
                "ML Engineer, Persistent Systems (2021 - Present)",
                "- Built recommendation models in PyTorch and deployed them on GCP Vertex AI with Docker.",
                "- Fine-tuned LLMs for a customer-support chatbot; SQL on BigQuery for training data.",
                "Software Engineer, Infosys (2020 - 2021)",
                "- Python backend services and data pipelines.",
            ]),
            ("Skills", ["Python, SQL (BigQuery), PyTorch, Hugging Face, Docker, Kubernetes, GCP (Vertex AI, GCS)"]),
            ("Education", ["B.E. Information Technology - Pune University, 2020"]),
        ],
    ),
    (
        "04_Arjun_Mehta.txt",
        "txt",
        "Arjun Mehta",
        "Aspiring Data Scientist | Delhi | arjun.mehta@example.com",
        [
            ("Summary", ["Recent graduate passionate about machine learning, looking for my first full-time role."]),
            ("Experience", [
                "Data Science Intern, small startup (Jan 2025 - Dec 2025)",
                "- Cleaned datasets in Python (Pandas) and built a logistic-regression model in a Jupyter notebook.",
                "- Wrote basic SQL queries for reports.",
            ]),
            ("Projects", [
                "- Titanic survival prediction (Kaggle), movie recommender (course project).",
                "- Completed AWS Cloud Practitioner course (not certified).",
            ]),
            ("Skills", ["Python, Pandas, NumPy, scikit-learn, SQL (basic), Matplotlib"]),
            ("Education", ["B.Tech Computer Science - Delhi Technological University, 2025"]),
        ],
    ),
    (
        "05_Divya_Nair.docx",
        "docx",
        "Divya Nair",
        "Marketing Analyst | Kochi | divya.nair@example.com",
        [
            ("Summary", [
                "Results-driven marketing analyst. Python SQL Machine Learning AWS PyTorch Docker LLMs AI "
                "Deep Learning Big Data Data Science expert.",
            ]),
            ("Experience", [
                "Marketing Analyst, regional FMCG company (2019 - Present)",
                "- Prepared weekly campaign performance reports in Excel and Google Analytics.",
                "- Coordinated with agencies on social-media campaigns and budgets.",
            ]),
            ("Skills", [
                "Python, SQL, Machine Learning, AWS, PyTorch, Docker, LLMs, Generative AI, Deep Learning, "
                "Excel, PowerPoint, Google Analytics",
            ]),
            ("Education", ["MBA Marketing - Kerala University, 2019; B.Com, 2017"]),
        ],
    ),
    (
        "06_Mohammed_Faisal.pdf",
        "pdf",
        "Mohammed Faisal",
        "Data Scientist | Chennai | mohammed.faisal@example.com",
        [
            ("Summary", ["Data scientist with 3 years in insurance analytics."]),
            ("Experience", [
                "Data Scientist, an insurance analytics firm (2022 - Present)",
                "- Built claim-risk scoring models in Python (scikit-learn) and SQL Server.",
                "- Model handed to the engineering team, who deployed it as an internal API.",
                "- Used AWS S3 to store datasets; exploring SageMaker.",
            ]),
            ("Skills", ["Python, SQL, scikit-learn, Pandas, Power BI, AWS S3 (basic)"]),
            ("Education", ["B.Sc Mathematics - Madras Christian College, 2021"]),
        ],
    ),
]


def write_pdf(path, name, headline, sections):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, name, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, headline, new_x="LMARGIN", new_y="NEXT")
    for heading, lines in sections:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, heading.upper(), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in lines:
            pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def write_docx(path, name, headline, sections):
    doc = Document()
    doc.add_heading(name, level=0)
    doc.add_paragraph(headline)
    for heading, lines in sections:
        doc.add_heading(heading, level=1)
        for line in lines:
            doc.add_paragraph(line)
    doc.save(str(path))


def write_txt(path, name, headline, sections):
    parts = [name, headline, ""]
    for heading, lines in sections:
        parts += [heading.upper(), *lines, ""]
    path.write_text("\n".join(parts), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    writers = {"pdf": write_pdf, "docx": write_docx, "txt": write_txt}
    for filename, fmt, name, headline, sections in RESUMES:
        writers[fmt](OUT / filename, name, headline, sections)
        print("wrote", OUT / filename)

    templates = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8")) if TEMPLATES_FILE.exists() else {}
    templates[TEMPLATE_NAME] = TEMPLATE
    TEMPLATES_FILE.write_text(json.dumps(templates, indent=2), encoding="utf-8")
    print(f"saved template '{TEMPLATE_NAME}' to", TEMPLATES_FILE)


if __name__ == "__main__":
    main()
