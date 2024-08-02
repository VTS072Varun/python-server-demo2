from flask import Flask, request, jsonify
import openai
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load the OpenAI API key from environment variables
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/fitment_analysis', methods=['POST'])
def fitment_analysis():
    data = request.get_json()
    job_description = data.get('job_description')
    candidate_info = data.get('candidate_info')
    
    if not job_description or not candidate_info:
        return jsonify({"error": "Job description and candidate information are required"}), 400
    
    # Perform fitment analysis
    fitment_result = analyze_fitment(candidate_info, job_description)
    
    return jsonify(fitment_result)

def analyze_fitment(candidate_info, job_description):
    # Create a prompt for OpenAI
    prompt = f"""
    Given the following candidate information and job description, provide a detailed fitment analysis. 
    Highlight key matches and gaps across the following factors: skills, experience, education, certifications, responsibilities, location. 
    Additionally, provide a job matching percentage.

    Candidate Information:
    {json.dumps(candidate_info, indent=2)}

    Job Description:
    {json.dumps(job_description, indent=2)}

    The analysis should end with: 
    ### Job Matching Percentage: [percentage]
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    
    analysis = response.choices[0].message['content'].strip()
    
    # Extract fitment summary and matching score
    lines = analysis.split('\n')
    summary = "\n".join(line for line in lines if "### Job Matching Percentage:" not in line).strip()
    matching_score = None
    for line in lines:
        if "### Job Matching Percentage:" in line:
            matching_score = line.split("### Job Matching Percentage:")[-1].strip()
            break
    
    return {
        "fitment_summary": summary,
        "matching_score": matching_score
    }

if __name__ == '__main__':
    app.run(debug=True)
