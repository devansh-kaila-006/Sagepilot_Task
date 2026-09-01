from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import ChatGoogleGenerativeAI

for model_name in ["gemini-1.5-pro", "gemini-3.6-flash", "gemini-1.0-pro"]:
    try:
        llm = ChatGoogleGenerativeAI(model=model_name)
        res = llm.invoke("Hi")
        print(f"Success with {model_name}: {res.content[:20]}")
    except Exception as e:
        print(f"Error with {model_name}: {e}")
