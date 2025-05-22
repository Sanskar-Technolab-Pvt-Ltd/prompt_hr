import frappe, requests
import json
import os,re
import subprocess
from frappe.utils.password import get_decrypted_password


@frappe.whitelist()
def parse_resume(file_url):
    """
    Parse the resume file (public or private) using the Affinda API.
   
    """
    try:           
        doc = frappe.get_doc("OpenAI Settings","OpenAI Settings")
        
        if doc.enable:
            files_url = f"{doc.file_url}"
            request_url = f"{doc.request_url}"
            model = f"{doc.model}"
            api_key = get_decrypted_password("OpenAI Settings","OpenAI Settings","api_key")
            
            
            
            if file_url.startswith("/private/files/"):
                relative_path = file_url.replace("/private/files/", "")
                file_path = frappe.get_site_path("private", "files", relative_path)
            elif file_url.startswith("/files/"):
                relative_path = file_url.replace("/files/", "")
                file_path = frappe.get_site_path("public", "files", relative_path)
            else:
                frappe.throw("Invalid file path format")

            if not os.path.exists(file_path):
                frappe.throw(f"File not found on server: {file_path}")
                
            if file_path.lower().endswith(('.docx', '.doc')):
                try:
                    # Create temporary PDF path
                    pdf_path = os.path.splitext(file_path)[0] + '.pdf'
                    
                    # Convert using LibreOffice
                    subprocess.run([
                        'libreoffice',
                        '--headless',
                        '--convert-to', 
                        'pdf',
                        '--outdir',
                        os.path.dirname(file_path),
                        file_path
                    ], check=True, timeout=30)
                    
                    if os.path.exists(pdf_path):
                        file_path = pdf_path 
                    else:
                        frappe.throw("PDF conversion failed - output file not created")
                except Exception as e:
                    frappe.log_error(message=f"Failed to convert file into PDF:  {e}", title="Failed to convert file into PDF")    
                    frappe.throw(f"DOCX to PDF conversion failed: {str(e)}")    
                
            file_headers = {
                "Authorization": f"Bearer {api_key}"
            }    

            with open(file_path, "rb") as f:        
    
                files = {
                    "file": (file_path, f), 
                    "purpose": (None, "assistants")
                }
                
                file_response = requests.post(files_url, headers=file_headers, files=files)
                
            
            if file_response.status_code == 200:
                file_data = file_response.json()
                file_id = file_data.get("id")
                # return file_data,file_id
            
            else:
                frappe.log_error(message=f"Failed to parse resume File API:  {file_response.status_code} - {file_response.text}", title="Error While Calling Resume File API")
                frappe.throw(f"File: An error occurred while parsing the resume.")     
                
            request_headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            resume_json_prompt = '''
                Parse the attached resume file and return the data using this JSON structure and give full accurate data in this json as per resume:

                {
                "data": {
                    "current_salary" : "30,00,000", 
                    "expected_salary" : "40,00,000", 
                    "dateOfBirth": "1987-12-22",
                    "education": [
                    {
                        "id: 1,
                        "organization": "University of Columbia",
                        "accreditation": {
                        "education": "Masters' Degree in International Business",
                        "educationLevel": "masters", #should be masters/bachelors/school not apart from it
                        "inputStr": "Masters' Degree in International Business",
                        "matchStr": ""
                        },
                        "grade": {
                        "raw": "(GPA 3.9)",
                        "value": "3.9",
                        "metric": "GPA"
                        },
                        "location": null,
                        "dates": {
                        "startDate": null,
                        "completionDate": "2009-01-01",
                        "isCurrent": false,
                        "rawText": "2009"
                        }
                    },
                    {
                        "id: 2,
                        "organization": "Newtown Square University",
                        "accreditation": {
                        "education": "Bachelor of Science in Industrial Engineering",
                        "educationLevel": "bachelors",
                        "inputStr": "Bachelor of Science in Industrial Engineering",
                        "matchStr": ""
                        },
                        "grade": {
                        "raw": "(GPA 4.9)",
                        "value": "4.9",
                        "metric": "GPA"
                        },
                        "location": null,
                        "dates": {
                        "startDate": null,
                        "completionDate": "2007-01-01",
                        "isCurrent": false,
                        "rawText": "2007"
                        }
                    }
                    ],
                    "emails": ["firstname@resumetemplate.org"],
                    "location": {
                    "formatted": "Indian Trail, NC, USA",
                    "streetNumber": null,
                    "street": null,
                    "apartmentNumber": null,
                    "city": "Indian Trail",
                    "postalCode": null,
                    "state": "North Carolina",
                    "stateCode": "NC",
                    "country": "United States",
                    "rawInput": "Indian, Trail, North Carolina",
                    "countryCode": "US"
                    },
                    "name": {
                    "raw": "MS LISA SHAW",
                    "last": "Shaw",
                    "first": "Lisa",
                    "title": "Ms",
                    "middle": ""
                    },
                    "objective": "",
                    "phoneNumbers": ["105 563"],
                    "phoneNumberDetails": [
                    {
                        "rawText": "105 563",
                        "formattedNumber": null,
                        "countryCode": null,
                        "internationalCountryCode": null,
                        "nationalNumber": null
                    }
                    ],
                    "referees": [],
                    "gender": ["Male/Female"],
                    "languages": ["Spanish", "English"],
                    "skills": ["coding", "analysis"],
                    "summary": "A pro - active and innovative Senior Sales Management Professional...",
                    "totalYearsExperience": 15,
                    "profession": "Recruitment Manager",
                    "workExperience": [
                    {
                        "id": 186753196,
                        "jobTitle": "Recruitment Team Manager",
                        "organization": "ABC",
                        "location": null,
                        "dates": {
                        "startDate": "2012-11-01",
                        "endDate": "2025-05-19",
                        "monthsInPosition": 151,
                        "isCurrent": true,
                        "rawText": "November 2012 - Current"
                        },
                        "jobDescription": "Team Manager + Strategic & Operational Management...",
                        "occupation": {
                        "jobTitle": "Recruitment Team Manager",
                        "jobTitleNormalized": "Recruitment Team Lead",
                        "classification": {
                            "socCode": 3571,
                            "title": "Human resources and industrial relations officers",
                            "minorGroup": "HR, Training and Other Vocational Associate Guidance Professionals",
                            "subMajorGroup": "BUSINESS AND PUBLIC SERVICE ASSOCIATE PROFESSIONALS",
                            "majorGroup": "ASSOCIATE PROFESSIONAL OCCUPATIONS",
                            "minorGroupCode": 357,
                            "subMajorGroupCode": 35,
                            "majorGroupCode": 3
                        },
                        "managementLevel": "Low",
                        "emsiId": "ET84C9998EE93124F0"
                        }
                    }
                    ]
                }
                }
            '''    
            
            request_payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a resume parser. Read the uploaded resume file and return same json value with accurate data as per resume."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": resume_json_prompt
                            },
                            {
                                "type": "file",
                                "file": {
                                "file_id": file_id
                            }
                                
                            }
                        ]
                    }
                ],
                "temperature": 0
            }
            
            request_response = requests.post(request_url, headers=request_headers, json=request_payload)
            if request_response.status_code == 200:
                response_content = request_response.json()["choices"][0]["message"]["content"]
                # response_json = json.loads(response_content)
                # if response_content.startswith("```json"):
                #     response_content = response_content.strip("```")  
                #     response_content = re.sub(r"^json\s*", "", response_content.strip())
                # Extract JSON from markdown block
                match = re.search(r"```json\s*(\{.*?\})\s*```", response_content, re.DOTALL)
                if match:
                    response_content = match.group(1)
                else:
                    frappe.log_error(f"Unexpected response format: {response_content}", "Resume Parsing Error")
                    frappe.throw("Unable to extract valid resume data. Please make sure the resume is a readable document and not a scanned image.")


                print(response_content)
                lists = []
                parsed_data = json.loads(response_content)
                data = parsed_data.get("data", {})
                raw_name = data.get("name", {}).get("raw")
                
                
                profession = data.get("profession")
                date_of_birth = data.get("dateOfBirth") 
                
                emails = data.get("emails", [])
                email = emails[0] if emails else None
                
                genders = data.get("gender", [])
                gender = genders[0] if genders else None
                
                phone_numbers = data.get("phoneNumbers", [])
                phone_number = phone_numbers[0] if phone_numbers else None
                
                skill = data.get("skills", [])
                skills = skill if skill else None

                date_of_birth = data.get("dateOfBirth") 
                total_years_experience = data.get("totalYearsExperience")
                current_salary = data.get("current_salary")
                expected_salary = data.get('expected_salary')
                                            
                country = (data.get("location") or {}).get("country")
                address = (data.get("location") or {}).get("rawInput")
                

                        
                education_details = []
                for edu in data.get("education", []):
                    accreditation = edu.get("accreditation", {}) or {}
                    organization_name = edu.get("organization")
                    education_level = accreditation.get("educationLevel")
                    university = None  
                    school = None
                    level = None
                    if organization_name:
                        name_lower = organization_name.lower()
                        if "university" in name_lower or "board" in name_lower:
                            university = organization_name
                        elif "school" in name_lower or "institute" in name_lower:
                            school = organization_name
                            level = "Under Graduate"
                          
                            
                    if education_level and level != "Under Graduate":
                        level_lower = education_level.lower()
                        if "masters" in level_lower:
                            level = "Post Graduate"
                        elif "bachelors" in level_lower or "certificate" in level_lower:
                            level = "Graduate"  
                                 
                    
                    dates = edu.get("dates", {}) or {}
                    grade = edu.get("grade", {}) or {}
                    
                    education_details.append({
                        "organization": edu.get("organization"),
                        "education": accreditation.get("education"),
                        "dates_rawText": dates.get("rawText"),
                        "university": university,
                        "school": school,
                        "level": level,
                        "grade_raw": grade.get("raw"),
                        "matchStr": accreditation.get("matchStr")
                    }) 
                        
                
                work_experience_details = []
                total_years_experience = 0.0
                for work in data.get("workExperience", []):
                    location = work.get("location", {}) or {}
                    dates = work.get("dates", {}) or {}
                    months_in_position = dates.get("monthsInPosition")
                    years_in_position = round(months_in_position / 12, 1) if months_in_position is not None else None
                    if years_in_position is not None:
                        total_years_experience += years_in_position
                    work_experience_details.append({
                        "organization": work.get("organization"),
                        "job_title": work.get("jobTitle"),
                        # "location_formatted": location,
                        "months_in_position": years_in_position,
                        "dates_rawText": dates.get("rawText")

                    })
                    
                
                lists.append({
                    "raw_name": raw_name,
                    "profession": profession,
                    "date_of_birth": date_of_birth,
                    "phone_number": phone_number,
                    "email": email,
                    'address':address,
                    "country": country,
                    "gender": gender,
                    "education": education_details,
                    "work_experience": work_experience_details,
                    "total_years_experience": total_years_experience,
                    "skills": skills,
                    "current_salary": current_salary,
                    "expected_salary":expected_salary
                })
                
                print(lists)
                return lists
                # print(response_json)
                # return response_json
                
            
            else:
                frappe.log_error(message=f"Failed to parse resume Request API:  {request_response.status_code} - {request_response.text}", title="Error While Calling Resume Request API")
                frappe.throw(f"Request: An error occurred while parsing the resume.") 
            
            
    except Exception as e:
        frappe.log_error(message=f"Error Parsing Resume : {e}", title="Resume Parsing Function Failed")
        frappe.throw(f"An error occurred while parsing the resume. ")        
