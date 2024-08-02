import os
import openai
import re
import logging
import json
import mammoth  
from flask import Flask, request, jsonify
import fitz  
import docx  
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key

app = Flask(__name__)

class ResumeParser():
    def __init__(self):
        # Ensure logs directory exists for logging
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # GPT-4 completion questions
        self.prompt_questions = """
            Summarize the text below into a JSON with exactly the following structure {
                basic_info: {
                    full_name, email, phone_number, City, Country, Province, linkedin_url, Experience_level, technical_expertise_in_skills, Experience_in_Years, Job_Title
                },
                work_experience: [{
                    job_title, company, location, duration, Start_year-End_Year, job_summary
                }],
                Education: [{
                    Institution_Name, Start_year-End_Year, Degree, Percentage
                }],
                skills: [skill_name]
            }
        """
        
        logging.basicConfig(filename='logs/parser.log', level=logging.DEBUG)
        self.logger = logging.getLogger()

    def pdf2string(self, pdf_path):
        """
        Extract the content of a pdf file to string using PyMuPDF.
        :param pdf_path: Path to the PDF file.
        :return: PDF content string.
        """
        pdf_text = ""
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pdf_text += page.get_text()
        doc.close()

        pdf_text = re.sub('\s[,.]', ',', pdf_text)
        pdf_text = re.sub('[\n]+', '\n', pdf_text)
        pdf_text = re.sub('[\s]+', ' ', pdf_text)
        pdf_text = re.sub('http[s]?(://)?', '', pdf_text)

        return pdf_text

    def docx2string(self, docx_path):
        """
        Extract the content of a docx file to string using python-docx.
        :param docx_path: Path to the DOCX file.
        :return: DOCX content string.
        """
        doc = docx.Document(docx_path)
        doc_text = '\n'.join([para.text for para in doc.paragraphs])

        doc_text = re.sub('\s[,.]', ',', doc_text)
        doc_text = re.sub('[\n]+', '\n', doc_text)
        doc_text = re.sub('[\s]+', ' ', doc_text)
        doc_text = re.sub('http[s]?(://)?', '', doc_text)

        return doc_text

    def doc2string(self, doc_path):
        """
        Extract the content of a .doc file using mammoth.
        :param doc_path: Path to the DOC file.
        :return: DOC content string.
        """
        with open(doc_path, "rb") as doc_file:
            result = mammoth.extract_raw_text(doc_file)
            doc_text = result.value

        doc_text = re.sub('\s[,.]', ',', doc_text)
        doc_text = re.sub('[\n]+', '\n', doc_text)
        doc_text = re.sub('[\s]+', ' ', doc_text)
        doc_text = re.sub('http[s]?(://)?', '', doc_text)

        return doc_text

    def query_completion(self, prompt):
        """
        Base function for querying OpenAI model.
        :param prompt: Prompt for the model.
        :return: Response from the model.
        """
        self.logger.info('query_completion: using gpt-4o-mini')

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response['choices'][0]['message']['content']
            self.logger.debug(f'OpenAI Response: {response_text}')
            return response_text
        except Exception as e:
            self.logger.error(f'Error querying OpenAI: {e}')
            return None

    def query_resume(self, file_path, file_type):
        """
        Query OpenAI model for the work experience and/or basic information from the resume at the file path.
        :param file_path: Path to the file.
        :param file_type: Type of the file (pdf, docx, or doc).
        :return: Dictionary of resume with keys (basic_info, work_experience, Education, skills).
        """
        resume = {}
        if file_type == 'pdf':
            file_str = self.pdf2string(file_path)
        elif file_type == 'docx':
            file_str = self.docx2string(file_path)
        elif file_type == 'doc':
            file_str = self.doc2string(file_path)
        else:
            raise ValueError("Unsupported file type")

        prompt = self.prompt_questions + '\n' + file_str

        response_text = self.query_completion(prompt)
        if response_text:
            try:
                # Clean up response text
                response_text = response_text.strip()
                
                # Remove backticks if present
                response_text = re.sub(r'^```json|```$', '', response_text).strip()
                
                # Load JSON
                resume = json.loads(response_text)
            except json.JSONDecodeError as e:
                self.logger.error(f'Error decoding JSON: {e}')
                self.logger.error(f'OpenAI Response: {response_text}')
                resume = {"error": "Invalid JSON response from OpenAI"}
        else:
            resume = {"error": "No response from OpenAI"}

        return resume

@app.route('/parse_resume', methods=['POST'])
def parse_resume():
    try:
        file = request.files['file']
        # Create uploads directory if it does not exist
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

if __name__ == "__main__":
    app.run(port=3000, host="0.0.0.0", debug=True)
