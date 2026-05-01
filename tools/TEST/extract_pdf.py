import pdfplumber
text = ''
with pdfplumber.open(r'C:\Users\フォーレスト026\Downloads\FRT組織図-20260401 (1).pdf') as pdf:
    for page in pdf.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + '\n'
with open(r'C:\Users\フォーレスト026\MyProject\MyProject\tools\TEST\pdf_extract.txt', 'w', encoding='utf-8') as f:
    f.write(text)
