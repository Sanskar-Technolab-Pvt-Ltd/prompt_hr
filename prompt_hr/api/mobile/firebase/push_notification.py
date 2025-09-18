
import firebase_admin
from firebase_admin import credentials

# ? PATH TO THE FIREBASE CERTIFICATION JSON FILE
PATH_TO_CERTIFICATE = "apps/prompt_hr/prompt_hr/api/mobile/firebase/firebase_certification.json"


def initialize_firebase():
    """
    INITIALIZES FIREBASE ADMIN SDK WITH THE CERTIFICATION DATA.
    
    :RETURN: NONE
    """
    try:
        cred = credentials.Certificate(PATH_TO_CERTIFICATE)
        return firebase_admin.initialize_app(cred)

    except Exception as e:
        raise RuntimeError(f"Error initializing Firebase: {e}")
