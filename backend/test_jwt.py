import jwt

anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2cG1qYnF3c2VnbHZudWd3bXlrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODgxOTIwNzcsImV4cCI6MjEwMzc2ODA3N30.QI553iNY-ZM7GcHo4_Zq1PbLh9MTNi-S8pD4fAJhFI4"
secret = "+nA6znPgb6X34UCnESvPG5rN+PlHP+QvrHVASOLpdn80HZAEZbtsXL4rPVk6DeI+N9rz9wpKIkDuB+Pew1OPRA=="

try:
    payload = jwt.decode(anon_key, secret, algorithms=["HS256"], options={"verify_aud": False})
    print("Success:", payload)
except Exception as e:
    print("Error:", e)
