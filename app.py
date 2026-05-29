import os
import re
import uuid

from PIL import Image
from pillow_heif import register_heif_opener

from flask import Flask, render_template, request, send_from_directory

# Enable HEIC and HEIF support
register_heif_opener()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

MAX_IMAGES = 20
MAX_IMAGE_SIZE = (1000, 1000)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def clean_filename(name):
    if not name:
        return "onetime_document"

    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")

    return name or "onetime_document"


def scan_image(image_path):
    image = Image.open(image_path)

    if image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail(MAX_IMAGE_SIZE)

    return image


@app.route("/", methods=["GET", "POST"])
def index():
    pdf_file = None
    error = None

    if request.method == "POST":
        files = request.files.getlist("images")
        pdf_name = request.form.get("pdf_name", "onetime-document")

        if not files or files[0].filename == "":
            error = "Please upload at least one image."

        elif len(files) > MAX_IMAGES:
            error = f"Maximum {MAX_IMAGES} images allowed for one PDF."

        else:
            try:
                allowed_formats = (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".heic",
                    ".heif"
                )

                scanned_images = []
                saved_files = []

                for file in files:
                    original_filename = file.filename.lower()

                    if original_filename.endswith(allowed_formats):
                        image_path = os.path.join(
                            UPLOAD_FOLDER,
                            f"{uuid.uuid4()}_{file.filename}"
                        )

                        file.save(image_path)
                        saved_files.append(image_path)

                        scanned_image = scan_image(image_path)
                        scanned_images.append(scanned_image)

                if not scanned_images:
                    error = "Only PNG, JPG, JPEG, HEIC, and HEIF files are allowed."

                else:
                    document_id = str(uuid.uuid4())
                    safe_name = clean_filename(pdf_name)

                    pdf_filename = f"{safe_name}_{document_id}.pdf"
                    pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)

                    first_image = scanned_images[0]
                    other_images = scanned_images[1:]

                    first_image.save(
                        pdf_path,
                        "PDF",
                        resolution=70.0,
                        save_all=True,
                        append_images=other_images
                    )

                    pdf_file = pdf_filename

                    for image in scanned_images:
                        image.close()

                for saved_file in saved_files:
                    try:
                        os.remove(saved_file)
                    except Exception:
                        pass

            except Exception as e:
                print("ERROR:")
                print(type(e))
                print(e)

                error = "Something went wrong while creating your PDF."

    return render_template(
        "index.html",
        pdf_file=pdf_file,
        error=error
    )


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(
        OUTPUT_FOLDER,
        filename,
        as_attachment=True,
        mimetype="application/octet-stream",
        download_name=filename
    )

if __name__ == "__main__":
    app.run(debug=True)