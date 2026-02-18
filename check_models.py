import google.generativeai as genai
import os

api_key = "AIzaSyBgsSPDtJZz9RxcAihqJWwzw2GUU7vY0I4"
genai.configure(api_key=api_key)

with open("models_list.txt", "w") as f:
    try:
        for m in genai.list_models():
            f.write(f"Name: {m.name}, Methods: {m.supported_generation_methods}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
