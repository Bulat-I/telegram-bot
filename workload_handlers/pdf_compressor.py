import os
import subprocess

async def compressPDF(input_item, output_path) -> int:
    input_filename = os.path.basename(input_item)
    output_item = os.path.join(output_path, input_filename)
    
    sts = subprocess.call(['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
                    '-sOutputFile=' + output_item, input_item])
    
    return sts