import os
import subprocess

async def compressPDF(input_filename, input_path, output_path) -> int:
    input_item = os.path.join(input_path, input_filename)
    output_item = os.path.join(output_path, input_filename + '_compressed')
    
    sts = subprocess.call(['gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dNOPAUSE', '-dQUIET', '-dBATCH',
                    '-sOutputFile=' + output_item, input_item])
    
    return sts