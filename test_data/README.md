# Test data

Six sample resumes in `resumes/`, plus a requirements template called **"Data Scientist (Test)"** saved in `templates.json`.

## How to test

1. In the app sidebar, choose **Load template → Data Scientist (Test)**. Leave the shortlist threshold at 70.
2. Upload every file in `test_data/resumes/` and click **Screen resumes**.

**Requirements in the template**
- **Must-have:** Python, SQL, Machine Learning, AWS, 3+ years of experience, a relevant Bachelor's degree, and at least one model deployed to production
- **Nice-to-have:** PyTorch, Docker, LLMs

## Expected results

Scores move by a few points between runs. The shortlisted/rejected outcome should not.

| Resume | Format | Designed to test | Expected | Verified run |
|---|---|---|---|---|
| Ananya Iyer | PDF | Meets everything, including nice-to-haves | 🟢 Shortlisted | 94, Strong fit |
| Karthik Reddy | DOCX | Meets all must-haves but few nice-to-haves (stats degree) | 🟢 Shortlisted | 82, Good fit |
| Mohammed Faisal | PDF | Borderline: only basic AWS use, and another team deployed the model | 🔴 Rejected | 58, AWS and deployment Partial |
| Sneha Patel | PDF | Strong ML engineer, but uses GCP rather than AWS (a must-have) | 🔴 Rejected | 55, AWS Not met |
| Arjun Mehta | TXT | Fresh graduate with 1 year of experience | 🔴 Rejected | 40, experience Not met |
| Divya Nair | DOCX | Keyword stuffing: lists ML skills but has no evidence of using them | 🔴 Rejected | 15, every skill Not met |

To regenerate the files, run `.venv\Scripts\python.exe test_data\generate_test_data.py` from the `resume_screener` folder. This needs `fpdf2`.
