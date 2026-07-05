import pdfplumber
def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts all text from a PDF file using pdfplumber.
    
    Args:
        pdf_file: A Streamlit uploaded file-like object.
        
    Returns:
        A string containing all the text extracted from the PDF, 
        or an empty string if extraction fails.
    """
    if pdf_file is None:
        return ""
    
    try:
        text_pages = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_pages.append(page_text)
        
        return "\n".join(text_pages)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
