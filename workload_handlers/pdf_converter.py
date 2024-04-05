import os
import subprocess

async def convertToPDF(input_item, output_path) -> int:
    input_filename = os.path.basename(input_item)
    
    sts = subprocess.call(['libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', output_path, input_item])
    
    return sts