import os
from pypdf import PdfReader, PdfWriter


async def compressPDF(input_item, output_path) -> str:
    reader = PdfReader(input_item)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(reader.metadata)

    for page in writer.pages:
        for img in page.images:
            img.replace(img.image, quality=60)

    for page in writer.pages:
        page.compress_content_streams(level=5)

    input_filename = os.path.basename(input_item)
    output_item = os.path.join(output_path, input_filename)

    with open(output_item, "wb") as output_file:
        writer.write(output_file)

    return output_item
