from flask import Flask, request, jsonify
import os
from Resume_Parser import ResumeParser
from fitment_analysis import analyze_fitment
from Resume_Search import process_job_request


app = Flask(__name__)

@app.route('/parse_resume', methods=['POST'])
def parse_resume():
    try:
        file = request.files['file']
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        file_path = f"uploads/{file.filename}"
        file.save(file_path)

        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in ['pdf', 'docx', 'doc']:
            return jsonify({"error": "Unsupported file type"}), 400

        parser = ResumeParser()
        parsed_resume = parser.query_resume(file_path, file_extension)

        return jsonify(parsed_resume)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/fitment_analysis', methods=['POST'])
def fitment_analysis():
    data = request.get_json()
    job_description = data.get('job_description')
    candidate_info = data.get('candidate_info')
    
    if not job_description or not candidate_info:
        return jsonify({"error": "Job description and candidate information are required"}), 400
    
    fitment_result = analyze_fitment(candidate_info, job_description)
    
    return jsonify(fitment_result)

@app.route('/search', methods=['POST'])
def search_candidates():
    job_request = request.json
    summary, top_candidates = process_job_request(job_request)
    return jsonify({'top_candidates': top_candidates})

# Health check route
@app.route('/health', methods=['GET'])
def health_check():
    version = "1.0"  # Replace with your actual version
    hostname = os.getenv('HOSTNAME', 'localhost')
    port = os.getenv('PORT', '3000')
    print(f'[Version {version}]: New request => http://{hostname}:{port}/health')
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(port=3000, host='0.0.0.0', debug=True)



