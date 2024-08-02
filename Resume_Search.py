import json
from flask import request, jsonify
import openai
import os

# Load OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

# Function to process job request and rank candidates
def process_job_request(job_request):
    job_title = job_request.get('title', '')
    job_description = job_request.get('description', '')
    job_skills = set(job_request.get('skills', []))
    job_experience = job_request.get('experience', '')
    job_location = job_request.get('location', '')

    # Ensure job_location is a string and convert to lower case
    job_location = job_location.lower() if isinstance(job_location, str) else ''

    # Construct the prompt for OpenAI to summarize job description and skills
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"""
        Summarize the job description and extract key skills:
        Job Title: {job_title}
        Job Description: {job_description}
        Key Skills: {', '.join(job_skills)}
        Experience Required: {job_experience}
        Location: {job_location}
        """}
    ]

    # Call OpenAI to process job request using the chat completion endpoint
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500
    )

    summary = response.choices[0].message['content'].strip()

    def calculate_match(candidate):
        # Safely extract and default values
        candidate_skills = set(candidate.get('skills', []))
        candidate_experience = candidate.get('experience', '')
        candidate_locations = [work.get('location', '') for work in candidate.get('work_experience', [])] or []
        candidate_country = candidate.get('country', '')

        # Ensure all candidate fields are strings
        candidate_country = candidate_country.lower() if isinstance(candidate_country, str) else ''
        candidate_experience = candidate_experience.lower() if isinstance(candidate_experience, str) else ''

        # Calculate skill match
        skill_match = len(job_skills.intersection(candidate_skills)) / len(job_skills) if job_skills else 0

        # Calculate experience match
        experience_match = 1 if job_experience and candidate_experience and job_experience.lower() in candidate_experience else 0

        # Calculate location match
        location_match = 0
        if job_location:
            # Ensure that candidate_locations are all strings
            candidate_locations = [loc.lower() if isinstance(loc, str) else '' for loc in candidate_locations]
            if candidate_country and job_location in candidate_country:
                location_match = 1
            elif any(job_location in loc for loc in candidate_locations):
                location_match = 0.5

        # Aggregate match score
        match_score = skill_match * 0.4 + experience_match * 0.3 + location_match * 0.3
        return match_score * 100

    # Get candidates from the 'users' field in the request
    candidates = job_request.get('users', [])

    # Rank candidates
    candidates_with_scores = [
        {
            **candidate,
            'match_percentage': calculate_match(candidate),
            'rank': 0  # Placeholder for rank
        }
        for candidate in candidates if candidate.get('email') and candidate.get('name')  # Ensure email and name are present
    ]

    # Remove duplicates based on email
    seen_emails = set()
    unique_candidates = []
    for candidate in candidates_with_scores:
        if candidate['email'] not in seen_emails:
            unique_candidates.append(candidate)
            seen_emails.add(candidate['email'])

    # Sort candidates by match percentage in descending order
    unique_candidates.sort(key=lambda x: x['match_percentage'], reverse=True)

    # Assign ranks
    for i, candidate in enumerate(unique_candidates):
        candidate['rank'] = i + 1

    # Return the top 20 candidates with required fields
    top_candidates = [
        {
            '_id': candidate.get('_id', {}),
            'name': candidate.get('name', 'Unknown'),
            'email': candidate.get('email', 'Not provided'),
            'phone_number': candidate.get('phone_number', 'Not provided'),
            'country': candidate.get('country', 'Not provided'),
            'state': candidate.get('state', 'Not provided'),
            'resume': candidate.get('resume', 'Not provided'),
            'experience': candidate.get('experience', 'Not provided'),
            'jobTitle': candidate.get('jobTitle', 'Not provided'),
            'linkedin_url': candidate.get('linkedin_url', 'Not provided'),
            'technical_expertise_in_skills': candidate.get('technical_expertise_in_skills', []),
            'Experience_level': candidate.get('Experience_level', 'Not provided'),
            'skills': candidate.get('skills', []),
            'Education': candidate.get('Education', []),
            'work_experience': candidate.get('work_experience', []),
            'matching_percentage': candidate['match_percentage'],
            'rank': candidate['rank']
        }
        for candidate in unique_candidates[:20]
    ]

    return summary, top_candidates

if __name__ == '__main__':
    app.run(debug=True, port=3000)
