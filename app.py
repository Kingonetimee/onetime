import os
import uuid
import re

from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    JpegImagePlugin,
    PdfImagePlugin
)

from pillow_heif import register_heif_opener

from flask import (
    Flask,
    render_template,
    request,
    send_from_directory
)

# Enable HEIC / HEIF support
register_heif_opener()

# Load Pillow plugins
Image.init()

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# =========================
# CLEAN FILE NAME
# =========================

def clean_filename(name):
    if not name:
        return "onetime_document"

    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")

    return name or "onetime_document"


# =========================
# IMAGE PROCESSING
# =========================

def scan_image(image_path):
    image = Image.open(image_path).convert("RGB")

    # Resize large phone images to reduce memory and speed up PDF creation
    image.thumbnail((1800, 1800))

    # Light scan enhancement
    image = image.filter(ImageFilter.SHARPEN)

    contrast = ImageEnhance.Contrast(image)
    image = contrast.enhance(1.45)

    brightness = ImageEnhance.Brightness(image)
    image = brightness.enhance(1.08)

    return image.convert("RGB")


# =========================
# MAIN ROUTE
# =========================

@app.route("/", methods=["GET", "POST"])
def index():
    pdf_file = None
    error = None

    if request.method == "POST":
        files = request.files.getlist("images")
        pdf_name = request.form.get("pdf_name", "onetime-document")

        if not files or files[0].filename == "":
            error = "Please upload at least one image."

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

                for file in files:
                    original_filename = file.filename.lower()

                    if original_filename.endswith(allowed_formats):
                        image_path = os.path.join(
                            UPLOAD_FOLDER,
                            f"{uuid.uuid4()}_{file.filename}"
                        )

                        file.save(image_path)

                        scanned_image = scan_image(image_path)

                        scanned_images.append(scanned_image)

                        # Delete uploaded image after processing to save space
                        try:
                            os.remove(image_path)
                        except Exception:
                            pass

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
                        format="PDF",
                        save_all=True,
                        append_images=other_images,
                        resolution=100.0,
                        quality=85,
                        optimize=True
                    )

                    pdf_file = pdf_filename

                    # Release memory
                    for image in scanned_images:
                        image.close()

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


# =========================
# DOWNLOAD ROUTE
# =========================

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(
        OUTPUT_FOLDER,
        filename,
        as_attachment=True
    )


# =========================
# RUN APP LOCALLY
# =========================

if __name__ == "__main__":
    app.run(debug=True)