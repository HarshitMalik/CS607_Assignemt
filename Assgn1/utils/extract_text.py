import os
import sys
import threading
import pdfplumber

# Directory where text extraction outputs are saved
text_output_dir = 'Resourses/text_extraction_output/'
# Directory where pdf of the books are stored
books_dir = 'Resourses/Books/'

# Books
books_name = [
              'Gita.pdf',
              'Quran.pdf',
              'Taoist.pdf',
              'GuruGranth.pdf',
              'Bible.pdf',
             ]

# First page where actual book text starts excluding cover page, about author, preface, contents, introduction,  etc
start_page = [20,4,0,0,12]

# Check if books directory exists
if not os.path.isdir(books_dir):
    raise 'Books directory' + '\''+ books_dir + '\''+'not found !'
    sys.exit()

# Check if output directory exists otherwise create it
if not os.path.isdir(text_output_dir):
    os.mkdir(text_output_dir)

# Extract text from PDFs
def extract_text(bookNumber):
    pdf = pdfplumber.open(books_dir + books_name[bookNumber])
    totalPages = len(pdf.pages)

    print("Extracting text from", books_name[bookNumber][:-4])
    print("Total pages found :", totalPages)

    files = os.listdir(text_output_dir)
    for i in range(start_page[bookNumber],totalPages):
        filename = books_name[bookNumber][:-4] + '_page_' + str(i) + '.txt'
        if filename in files:
            continue
        if i%50 == 0:
            print('.',end='')
            sys.stdout.flush()
        text = pdf.pages[i].extract_text(x_tolerance=2)
        if text is not None:
            file = open(text_output_dir + filename, "w")
            file.write(text)
            file.close()

    print("Text extraction completed")
