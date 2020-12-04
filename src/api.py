import json
import os
import uuid
from tempfile import NamedTemporaryFile

import magic
import requests
from PIL import Image
from disclosure_extractor import (
    process_financial_document,
    process_judicial_watch,
)
from flask import Flask, request, jsonify, send_file

from src.utils.audio import (
    set_mp3_meta_data,
    convert_to_mp3,
    convert_to_base64,
)
from src.utils.financial_disclosures import (
    find_and_sort_image_urls,
    download_images,
)
from src.utils.image_processing import convert_tiff_to_pdf_bytes
from src.utils.tasks import (
    extract_from_docx,
    extract_from_doc,
    extract_from_wpd,
    extract_from_html,
    extract_from_txt,
    make_pdftotext_process,
    extract_from_pdf,
    rasterize_pdf,
    make_png_thumbnail_for_instance,
    get_page_count,
    pdf_bytes_from_image_array,
    strip_metadata_from_bytes,
)

app = Flask(__name__)


@app.route("/")
def heartbeat():
    """Heartbeat

    :return: success response
    :type: dict
    """
    return jsonify({"success": True, "msg": "Docker container running."})


@app.route("/document/extract_text", methods=["POST"])
def extract_content():
    """Extract txt from different document types.

    :return: The content of a document/error message.
    :type: json object
    """

    f = request.files["file"]
    do_ocr = request.args.get("do_ocr", default=False)
    if do_ocr == "True":
        do_ocr = True

    extension = f.filename.split(".")[-1]
    with NamedTemporaryFile(suffix=".%s" % extension) as tmp:
        f.save(tmp.name)
        if extension == "pdf":
            content, err, returncode = make_pdftotext_process(tmp.name)
            if do_ocr and len(content.strip()) == 0:
                with NamedTemporaryFile(suffix=".tiff") as tmp_tiff:
                    _, _, _ = rasterize_pdf(tmp.name, tmp_tiff.name)
                    content, err, returncode = extract_from_pdf(tmp_tiff)
                    if content == "":
                        content, err, returncode = (
                            "",
                            "Unable to extract document content",
                            1,
                        )
            else:
                if len(content.strip()) == 0:
                    content, err, returncode = "", "No content detected", 1
        elif extension == "doc":
            content, err, returncode = extract_from_doc(tmp.name)
        elif extension == "docx":
            content, err, returncode = extract_from_docx(tmp.name)
        elif extension == "html":
            content, err, returncode = extract_from_html(tmp.name)
        elif extension == "txt":
            content, err, returncode = extract_from_txt(tmp.name)
        elif extension == "wpd":
            content, err, returncode = extract_from_wpd(tmp.name)
        else:
            content = ""
            err = "Unable to extract content due to unknown extension"
            returncode = 1
        return jsonify(
            {
                "content": content,
                "err": str(err),
                "error_code": str(returncode),
            }
        )


@app.route("/document/thumbnail", methods=["POST"])
def make_png_thumbnail():
    """Make a thumbail of the first page of a PDF and return it.

    :return: A response containing our file and any errors
    :type: HTTPS response
    """
    pdf_file = request.files["file"]
    max_dimension = int(request.args.get("max_dimension"))
    with NamedTemporaryFile(suffix=".%s" % "pdf") as tmp:
        pdf_file.save(tmp.name)
        thumbnail, _, _ = make_png_thumbnail_for_instance(
            tmp.name, max_dimension
        )
        return thumbnail


@app.route("/document/page_count", methods=["POST"])
def page_count():
    """Get page count form PDF

    :return: Page count
    """
    file = request.files["file"]
    extension = file.filename.split(".")[-1]
    with NamedTemporaryFile(suffix=".%s" % extension) as tmp:
        file.save(tmp.name)
        pg_count = get_page_count(tmp.name, extension)
        return jsonify({"pg_count": pg_count}), 200


@app.route("/document/pdf_to_text", methods=["POST"])
def pdf_to_text():
    """Extract text from text based PDFs immediately.

    :return:
    """
    f = request.files["file"]
    extension = f.filename.split(".")[-1]
    with NamedTemporaryFile(suffix=".%s" % extension) as tmp:
        f.save(tmp.name)
        content, err = make_pdftotext_process(tmp.name)
        return jsonify({"content": content, "err": err})


@app.route("/document/mime_type", methods=["GET", "POST"])
def extract_mime_type():
    """Identify the mime type of a document

    :return: Mime type
    """

    file = request.files["file"]
    mime = request.args.get("mime")
    try:
        if mime == "False":
            mime = False
        with NamedTemporaryFile() as tmp:
            file.save(tmp.name)
            mimetype = magic.from_file(tmp.name, mime=mime)
        return jsonify({"mimetype": mimetype})
    except Exception as e:
        return jsonify({"error": str(e)}), 422


# ------- Financial Disclosure Microservice requests ------- #
@app.route("/financial_disclosure/tiff_to_pdf", methods=["POST"])
def split_single_tiff_into_pdf_from_url():
    """Convert financial disclosure image url to PDF

    :return: PDF content
    """
    aws_url = request.args.get("tiff_url")
    try:
        tiff_bytes = Image.open(
            requests.get(aws_url, stream=True, timeout=5 * 60).raw
        )
    except TimeoutError:
        return jsonify({"aws_error": "aws timeout"}), 408

    pdf_bytes = convert_tiff_to_pdf_bytes(tiff_bytes)
    cleaned_pdf_bytes = strip_metadata_from_bytes(pdf_bytes)
    return cleaned_pdf_bytes, 200


@app.route("/financial_disclosure/tiffs_to_pdf", methods=["POST"])
def make_pdf_from_images():
    """Convert split financial disclosure images into single PDF

    Using a single image url find other pages and combine into a single PDF

    :return: PDF content
    """
    try:
        aws_path = request.args.get("aws_path")
        sorted_urls = find_and_sort_image_urls(aws_path)
        image_list = download_images(sorted_urls)
        pdf_bytes = pdf_bytes_from_image_array(image_list)
        cleaned_pdf_bytes = strip_metadata_from_bytes(pdf_bytes)
        return cleaned_pdf_bytes, 200
    except:
        return 422


@app.route("/financial_disclosure/urls_to_pdf", methods=["POST"])
def make_pdf_from_urls():
    """Create PDF from multiple image URLs.

    :return: PDF content
    """
    try:
        sorted_urls = json.loads(request.get_json())["urls"]
        image_list = download_images(sorted_urls)
        pdf_bytes = pdf_bytes_from_image_array(image_list)
        cleaned_pdf_bytes = strip_metadata_from_bytes(pdf_bytes)
        return cleaned_pdf_bytes, 200
    except:
        return 422


@app.route("/financial_disclosure/extract", methods=["POST"])
def financial_disclosure_extract():
    """Extract contents from a judicial financial disclosure.

    :return: Extracted financial records
    """
    financial_record_data = process_financial_document(
        pdf_bytes=request.files.get("file", None).read()
    )
    return jsonify(financial_record_data)


@app.route("/financial_disclosure/extract_jw", methods=["POST"])
def judical_watch_extract():
    """Extract content from a judicial watch financial disclosure.

    Technically this works on non-judicial watch PDFs but it is much slower.
    Can/should be used if financial_disclosure_extract fails

    :return: Disclosure information
    """
    financial_record_data = process_judicial_watch(
        pdf_bytes=request.files.get("file", None).read()
    )
    return jsonify(financial_record_data)


# ------- Process Audio Files ------- #
@app.route("/convert/audio", methods=["GET", "POST"])
def audio_conversion():
    """Convert audio file to MP3 and update metadata on mp3.

    :return: Converted audio
    """
    # For whatever reason temporary file was workable with subprocess.
    tmp_path = os.path.join("/tmp", "audio_" + uuid.uuid4().hex + ".mp3")
    try:
        audio_bytes = request.files["audio_file"].read()
        audio_data = json.loads(request.args.get("audio_data"))
        convert_to_mp3(audio_bytes, tmp_path)
        audio_file = set_mp3_meta_data(audio_data, tmp_path)
        audio_b64 = convert_to_base64(tmp_path)
        os.remove(tmp_path)

        return jsonify(
            {
                "audio_b64": audio_b64,
                "duration": audio_file.info.time_secs,
                "msg": "Success",
            }
        )
    except Exception as e:
        # Handle file cleanup and return a 422
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return jsonify({"msg": str(e)}), 422
