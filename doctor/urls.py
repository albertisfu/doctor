from django.urls import path

from . import views

urlpatterns = [
    # Server
    path("", views.heartbeat, name="heartbeat"),
    path("extract/pdf/text/", views.extract_pdf, name="extract-pdf-to-text"),
    path("extract/doc/text/", views.extract_doc_content, name="convert-doc-to-text"),
    path("convert/image/pdf/", views.image_to_pdf, name="image-to-pdf"),
    path("convert/images/pdf/", views.images_to_pdf, name="images-to-pdf"),
    path("convert/pdf/thumbnail/", views.make_png_thumbnail, name="thumbnail"),
    path("convert/audio/mp3/", views.convert_audio, name="convert-audio"),
    path("utils/page-count/pdf/", views.page_count, name="page_count"),
    path("utils/mime-type/", views.extract_mime_type, name="mime_type"),
    path("utils/file/extension/", views.extract_extension, name="file-extension"),
    path(
        "utils/file/mime/",
        views.extract_mime_from_buffer,
        name="mime_type_from_buffer",
    ),
    path("utils/audio/duration/", views.fetch_audio_duration, name="audio-duration"),
    path("utils/add/text/pdf/", views.embed_text, name="add-text-to-pdf"),
    # Extractors
    path("text/", views.extract_pdf, name="text"),
    path("extract-doc-content/", views.extract_doc_content, name="extract-doc-content"),
    # Utils
    path("pg-count/", views.page_count, name="page_count"),
    path("mime-type/", views.extract_mime_type, name="mime_type"),
    # Converters
    path("image-to-pdf/", views.image_to_pdf, name="image-to-pdf"),
    path("thumbnail/", views.make_png_thumbnail, name="thumbnail"),
    path("images-to-pdf/", views.images_to_pdf, name="images-to-pdf"),
    # Audio files
    path("convert-audio/", views.convert_audio, name="convert-audio"),
    # Legacy URLs
    path("document/page_count", views.page_count, name="page_count"),
    path("document/thumbnail", views.make_png_thumbnail, name="thumbnail"),
    # Unsupported - to retire
    path("document/pdf-to-text/", views.pdf_to_text, name="pdf-to-text"),
]
