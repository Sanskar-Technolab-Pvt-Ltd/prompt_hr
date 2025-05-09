import frappe, requests
import os

@frappe.whitelist()
def parse_resume(file_url):
    """
    Parse the resume file (public or private) using the Affinda API.
   
    """
    try:   
        Male = ["Male", "male", "M", "m"]
        Female = ["Female", "female", "F", "f"]
        
        api_url = "https://api.affinda.com/v2/resumes"
        
        headers = {
            "Authorization": "Bearer aff_93b5994c8ea65b1f27596b3301f434750cc02951"
        }

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

        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(api_url, headers=headers, files=files)

        if response.status_code == 200:
            response_data = response.json()
            lists = []
            data = response_data.get("data", {})
            raw_name = data.get("name", {}).get("raw")
            profession = data.get("profession")
            date_of_birth = data.get("dateOfBirth") 
            emails = data.get("emails", [])
            email = emails[0] if emails else None
            phone_numbers = data.get("phoneNumbers", [])
            phone_number = phone_numbers[0] if phone_numbers else None

            date_of_birth = data.get("dateOfBirth") 
            total_years_experience = data.get("totalYearsExperience")
            
            
            country = None
            gender = None
            
            for section in data.get("sections", []):
                if section.get("sectionType") == "PersonalDetails":
                    text = section.get("text", "")
                    
                    # Check for gender (looking for "Male" or "Female" in the text)
                    for male_rep in Male:
                        if f" {male_rep} " in f" {text} ": 
                            gender = "Male"
                            break
                    
                    if not gender:
                        for female_rep in Female:
                            if f" {female_rep} " in f" {text} ":
                                gender = "Female"
                                break
                        
            country = (data.get("location") or {}).get("country")

                    
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
                        
                if education_level:
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
                    "location_formatted": location.get("formatted"),
                    "months_in_position": years_in_position,
                    "dates_rawText": dates.get("rawText")

                })
                
            skills = None
            for section in data.get("sections", []):
                if section.get("sectionType") == "Skills/Interests/Languages":
                    skills = section.get("text", "")
                    break    
            
            
            lists.append({
                "raw_name": raw_name,
                "profession": profession,
                "date_of_birth": date_of_birth,
                "phone_number": phone_number,
                "email": email,
                "country": country,
                "gender": gender,
                "education": education_details,
                "work_experience": work_experience_details,
                "total_years_experience": total_years_experience,
                "skills": skills,
            })
            
            # print(lists)
            return lists
        
        else:
            frappe.log_error(message=f"Failed to parse resume API:  {response.status_code} - {response.text}", title="Error While Calling Resume API")
            frappe.throw(f"An error occurred while parsing the resume.")        
            
            
    except Exception as e:
        frappe.log_error(message=f"Error Parsing Resume : {e}", title="Resume Parsing Function Failed")
        # frappe.throw(f"An error occurred while parsing the resume. ")        

