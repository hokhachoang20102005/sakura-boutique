import os

thu_muc_goc = os.path.abspath(os.path.dirname(__file__))

# Local: SQL Server | Deploy: DATABASE_URL env var hoặc SQLite fallback
_db_url_mac_dinh = 'mssql+pyodbc://@localhost/SakuraBoutique?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes'
_db_url = os.environ.get('DATABASE_URL', _db_url_mac_dinh)
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

class CauHinh:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sakura-boutique-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(thu_muc_goc, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    NGAN_HANG = 'TPB'
    SO_TAI_KHOAN = '88820102005'
    TEN_TAI_KHOAN = 'HO KHAC HOANG'

    SEPAY_API_KEY = os.environ.get('SEPAY_API_KEY', '')
