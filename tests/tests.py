# -*- coding: utf-8 -*-
import base64
import json
import logging
import os
import time
import unittest
from glob import iglob
from tempfile import NamedTemporaryFile
from unittest import TestCase

import docker
import eyed3
import requests
from disclosure_extractor import display_table


class DockerTestBase(TestCase):
    """Base class for docker testing."""

    BTE_HOST = "http://localhost:5051"
    root = os.path.dirname(os.path.realpath(__file__))
    assets_dir = os.path.join(root, "test_assets")
    answer_path = os.path.join(root, "test_assets", "test_answers.json")
    doc_answers = {}
    with open(answer_path, "r") as f:
        doc_json = json.load(f)
    for k, v in doc_json.items():
        doc_answers[k] = v

    BTE_URLS = {
        # Testing
        "heartbeat": f"{BTE_HOST}",
        "large-heartbeat": f"{BTE_HOST}/large_file_test",
        # Audio Processing
        # this should change but currently in a PR so will alter later
        "convert-audio": f"{BTE_HOST}/convert/audio",
        "audio-to-mp3": f"{BTE_HOST}/audio/convert_to_mp3",
        "audio-length": f"{BTE_HOST}/audio/length",
        # Document processing
        "pdf-to-text": f"{BTE_HOST}/document/pdf_to_text",
        "document-extract": f"{BTE_HOST}/document/extract_text",
        "page-count": f"{BTE_HOST}/document/page_count",
        "thumbnail": f"{BTE_HOST}/document/thumbnail",
        "mime-type": f"{BTE_HOST}/document/mime_type",
        # Financial Disclosures
        # Image conversion and extraction
        "images-to-pdf": f"{BTE_HOST}/financial_disclosure/images_to_pdf",
        # Disclosure Extractor
        "extract-disclosure": f"{BTE_HOST}/financial_disclosure/extract_record",
        "extract-disclosure-jw": f"{BTE_HOST}/financial_disclosure/extract_jw",
        "extract-disclosure-jef": f"{BTE_HOST}/financial_disclosure/extract_jef",
        "extract-disclosure-pdf": f"{BTE_HOST}/financial_disclosure/extract_pdf",
        # Deprecated APIs
    }

    def setUp(self):
        """Setup containers

        Start seal-rookery docker image and set volume binding. Then link
        seal rookery to BTE python site packages.

        :return:
        """
        client = docker.from_env()
        client.containers.run(
            "freelawproject/seal-rookery:latest",
            name="bte-seal-rookery",
            detach=True,
            auto_remove=True,
            volumes={
                "seal-rookery": {
                    "bind": "/usr/local/lib/python3.8/site-packages/seal_rookery",
                    "mode": "ro",
                }
            },
        )
        client.containers.run(
            "freelawproject/binary-transformers-and-extractors:latest",
            ports={"5050/tcp": ("0.0.0.0", 5051)},
            cpuset_cpus="0-7",
            detach=True,
            auto_remove=True,
            volumes={
                "seal-rookery": {
                    "bind": "/usr/local/lib/python3.8/site-packages/seal_rookery",
                    "mode": "ro",
                }
            },
        )
        time.sleep(2)
        client.close()

    def tearDown(self):
        """Tear down containers"""
        client = docker.from_env()
        for container in client.containers.list():
            container.stop()
        client.close()

    def send_file_to_bte(self, filepath, do_ocr=False):
        """Send file to extract doc content method.

        :param filepath:
        :param do_ocr:
        :return:
        """
        with open(filepath, "rb") as file:
            f = file.read()
        return requests.post(
            self.BTE_URLS["document-extract"],
            files={"file": (os.path.basename(filepath), f)},
            params={"do_ocr": do_ocr},
        ).json()

    def send_file_to_pdftotext(self, filepath):
        """Send file to pdftotext method.

        :param filepath:
        :return:
        """
        with open(filepath, "rb") as file:
            f = file.read()
        return requests.post(
            self.BTE_URLS["pdf-to-text"],
            files={"file": (os.path.basename(filepath), f)},
        ).json()

    def send_file_to_convert_audio(self, filepath):
        """This is a helper function to post to audio conversion.

        :param filepath:
        :return:
        """
        with open(filepath, "rb") as file:
            f = file.read()
        return requests.post(
            self.BTE_URLS["convert-audio"],
            files={"file": (os.path.basename(filepath), f)},
        )

    def send_file_to_thumbnail_generation(self, filepath, max_dimension=350):
        """Send file to extract doc content

        :param filepath:
        :param max_dimension:
        :return:
        """
        with open(filepath, "rb") as file:
            f = file.read()
        return requests.post(
            self.BTE_URLS["thumbnail"],
            files={"file": (os.path.basename(filepath), f)},
            params={"max_dimension": max_dimension},
        )


class DocumentConversionTests(DockerTestBase):
    """Test document conversion"""

    def test_convert_pdf_to_txt(self):
        """Can we convert an image pdf to txt?"""
        for filepath in iglob(
            os.path.join(self.assets_dir, "opinion_pdf_image_based.pdf")
        ):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract content from image pdf.",
            )
            print("Extracted content from .pdf successfully")

    def test_convert_docx_to_txt(self):
        """Can we convert docx file to txt?"""
        for filepath in iglob(os.path.join(self.assets_dir, "*.docx")):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract from .docx file.",
            )
            print("Extracted content from .docx successfully")

    def test_convert_wpd_to_txt(self):
        """Can we convert word perfect document to txt?"""
        for filepath in iglob(os.path.join(self.assets_dir, "*.wpd")):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract word perfect document.",
            )
            print("Extracted content from .wpd successfully")

    def test_convert_doc_to_txt(self):
        """Can we convert doc file to txt?"""
        for filepath in iglob(os.path.join(self.assets_dir, "*.doc")):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract .doc document.",
            )
            print("Extracted content from .doc successfully")

    def test_convert_html_to_txt(self):
        """Can we convert HTML to txt?"""
        for filepath in iglob(os.path.join(self.assets_dir, "*.html")):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract content from HTML.",
            )
            print("Extracted content from .html successfully")

    def test_convert_txt_to_txt(self):
        """Can we extract text from a txt document?"""
        for filepath in iglob(os.path.join(self.assets_dir, "opinion*.txt")):
            response = self.send_file_to_bte(filepath, do_ocr=True)
            answer = self.doc_answers[filepath.split("/")[-1]]
            self.assertEqual(
                answer,
                response["content"],
                msg="Failed to extract content from txt file.",
            )
            print("Extracted content from .txt successfully")

    def test_bad_txt_extraction(self):
        """Can we extract text from a txt document with bad encoding?"""
        for filepath in iglob(
            os.path.join(self.assets_dir, "txt_file_with_no_encoding*.txt")
        ):
            response = self.send_file_to_bte(filepath)
            success = int(response["error_code"])
            self.assertFalse(
                success,
                "Error reported while extracting text from %s" % filepath,
            )
            self.assertIn(
                "¶  1.  DOOLEY, J.   Plaintiffs",
                response["content"],
                "Issue extracting/encoding text from file at: %s" % filepath,
            )


class AudioConversionTests(DockerTestBase):
    """Test Audio Conversion"""

    def test_wma_to_mp3(self):
        """Can we convert to mp3 with metadata"""

        wma_path = os.path.join(self.assets_dir, "1.wma")
        with open(wma_path, "rb") as wma_file:
            w = wma_file.read()

        audio_details = {
            "court_full_name": "Testing Supreme Court",
            "court_short_name": "Testing Supreme Court",
            "court_pk": "test",
            "court_url": "http://www.example.com/",
            "docket_number": "docket number 1 005",
            "date_argued": "2020-01-01",
            "date_argued_year": "2020",
            "case_name": "SEC v. Frank J. Custable, Jr.",
            "case_name_full": "case name full",
            "case_name_short": "short",
            "download_url": "http://media.ca7.uscourts.gov/sound/external/gw.15-1442.15-1442_07_08_2015.mp3",
        }

        audio_resp = requests.post(
            self.BTE_URLS["convert-audio"],
            params={"audio_data": json.dumps(audio_details)},
            files={
                "audio_file": (os.path.basename(wma_path), w),
            },
        )

        # Check test returns 200.
        self.assertEqual(
            audio_resp.status_code,
            200,
            msg=f"Status code not 200; {audio_resp.json()['msg']}",
        )

        # Validate some metadata in the MP3.
        with NamedTemporaryFile(suffix="mp3") as tmp:
            with open(tmp.name, "wb") as mp3_data:
                mp3_data.write(
                    base64.b64decode(audio_resp.json()["audio_b64"])
                )
                mp3_file = eyed3.load(tmp.name)

            self.assertEqual(
                mp3_file.tag.publisher,
                "Free Law Project",
                msg="Publisher metadata failed.",
            )
            self.assertEqual(
                mp3_file.tag.title,
                "SEC v. Frank J. Custable, Jr.",
                msg="Title metadata failed.",
            )

            self.assertEqual(
                mp3_file.type,
                eyed3.core.AUDIO_MP3,
                msg="Audio conversion to mp3 failed.",
            )

    def test_failing_audio_conversion(self):
        """Can we convert wma to mp3 and add metadata?"""

        filepath = os.path.join(
            self.assets_dir, "..", "fixtures", "test_audio_object.json"
        )
        wma_path = os.path.join(self.assets_dir, "opinion_text.txt")
        with open(filepath, "r") as file:
            audio_obj = json.load(file)
        with open(wma_path, "rb") as wma_file:
            w = wma_file.read()
        audio_resp = requests.post(
            self.BTE_URLS["convert-audio"],
            params={
                "audio_obj": json.dumps(audio_obj),
            },
            files={
                "file": (os.path.basename(wma_path), w),
            },
        )

        self.assertEqual(
            audio_resp.status_code, 422, msg="Status code not 422"
        )


class ThumbnailGenerationTests(DockerTestBase):
    """Can we generate thumbnail images from PDF files"""

    def test_convert_pdf_to_thumbnail_png(self):
        """Can we generate a pdf to thumbnail?"""
        for thumb_path in iglob(os.path.join(self.assets_dir, "*thumbnail*")):
            filepath = thumb_path.replace("_thumbnail.png", ".pdf")
            with open(thumb_path, "rb") as f:
                test_thumbnail = f.read()
            bte_response = self.send_file_to_thumbnail_generation(filepath)
            self.assertEqual(
                bte_response.content,
                test_thumbnail,
                msg="Thumbnail failed.",
            )
        print("Generated thumbnails from .pdf successfully")


class UtilityTests(DockerTestBase):
    """Can we do basic operations?"""

    def test_heartbeat(self):
        """Check heartbeat?"""
        t1 = time.time()
        response = requests.get(
            self.BTE_URLS["heartbeat"], timeout=7200
        ).json()
        t2 = time.time()
        print(t2 - t1)
        self.assertTrue(response["success"], msg="Failed heartbeat test.")

    def send_file_to_pg_count(self, filepath):
        """Send file to extract page count.

        :param filepath:
        :return:
        """
        with open(filepath, "rb") as file:
            f = file.read()
        url = "https://com-courtlistener-storage.s3.amazonaws.com/us/federal/judicial/financial-disclosures/189/maryanne-trump-barry-disclosure.2010.pdf"
        f = requests.get(url).content
        return requests.post(
            self.BTE_URLS["page-count"],
            files={"file": (os.path.basename(filepath), f)},
        )

    def test_pdf_page_count_extractor(self):
        """Can we extract page counts properly?"""

        counts = [2, 30, 1, 6]
        for count, filepath in zip(
            counts, sorted(iglob(os.path.join(self.assets_dir, "*.pdf")))
        ):
            with open(filepath, "rb") as file:
                f = file.read()

            pg_count_response = requests.post(
                self.BTE_URLS["page-count"],
                files={"file": (os.path.basename(filepath), f)},
            )
            self.assertEqual(
                int(pg_count_response.content), count, msg="Failed page count"
            )
        print("Successfully returned page count √")

    def test_post_pdf_data(self):
        """Can we send pdf as a file and get a response?"""
        pdf_path = os.path.join(self.assets_dir, "fd", "tiff_to_pdf.pdf")
        with open(pdf_path, "rb") as file:
            f = file.read()
        response = requests.post(
            url=self.BTE_URLS["page-count"],
            files={"file": (os.path.basename(pdf_path), f)},
            timeout=60,
        )
        self.assertEqual(200, response.status_code, msg="Failed to post data")

    def test_file_type(self):
        """Test Mime Type extraction"""
        pdf_path = os.path.join(self.assets_dir, "fd", "tiff_to_pdf.pdf")
        with open(pdf_path, "rb") as file:
            f = file.read()
        response = requests.post(
            url=self.BTE_URLS["mime-type"],
            params={"mime": True},
            files={"file": (os.path.basename(pdf_path), f)},
            timeout=60,
        ).json()
        self.assertEqual(response["mimetype"], "application/pdf")


class FinancialDisclosureTests(DockerTestBase):
    """Test financial disclosure extraction"""

    def test_financial_disclosure_extractor(self):
        """Test financial disclosure extraction"""

        pdf_path = os.path.join(self.assets_dir, "fd", "tiff_to_pdf.pdf")

        with open(pdf_path, "rb") as file:
            extractor_response = requests.post(
                self.BTE_URLS["extract-disclosure"],
                files={"pdf_document": ("file.pdf", file)},
                timeout=60 * 60,
            )

        self.assertTrue(
            extractor_response.json()["success"],
            msg="Disclosure extraction failed.",
        )

    def test_judicial_watch_document(self):
        """Can we extract data from a judicial watch document?"""
        pdf_path = os.path.join(
            self.root, "test_assets", "fd", "2003-judicial-watch.pdf"
        )
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()
        extractor_response = requests.post(
            self.BTE_URLS["extract-disclosure-jw"],
            files={"file": (os.path.basename(pdf_path), pdf_bytes)},
            timeout=60 * 60,
        )
        self.assertTrue(
            extractor_response.json()["success"],
            msg="Financial disclosure document parsing failed.",
        )

        display_table(extractor_response.json())

    def test_pdf_document(self):
        """Can we extract data from a normal PDF document?"""
        pdf_path = os.path.join(
            self.root, "test_assets", "fd", "Alquist-NV-18.pdf"
        )
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()

        logging.info(f"Extracting financial disclosure from {pdf_path}")
        extractor_response = requests.post(
            self.BTE_URLS["extract-disclosure-pdf"],
            files={"file": (os.path.basename(pdf_path), pdf_bytes)},
            timeout=60 * 5,
        ).json()
        self.assertTrue(extractor_response["success"], msg="Extraction Failed")
        self.assertEqual(
            extractor_response["sections"]["Investments and Trusts"]["rows"][
                43
            ]["A"]["text"],
            "BLACKROCK STRATEGIC INCOME OPPTYS INSTL CL REINVESTMENTS BSIIX",
            msg="Wrong Company Name",
        )

    def test_jef_document(self):
        """Can we extract data from a judicial watch document?"""
        pdf_path = os.path.join(
            self.root, "test_assets", "fd", "JEF_format.pdf"
        )
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()

        extractor_response = requests.post(
            self.BTE_URLS["extract-disclosure-jef"],
            files={"file": (os.path.basename(pdf_path), pdf_bytes)},
            timeout=60 * 60,
        )
        self.assertTrue(
            extractor_response.json()["success"],
            msg="Financial disclosure document parsing failed.",
        )
        self.assertFalse(
            extractor_response.json()[
                "Additional Information or Explanations"
            ]["is_redacted"]
        )
        self.assertFalse(
            extractor_response.json()["sections"]["Investments and Trusts"][
                "rows"
            ][0]["A"]["inferred_value"]
        )


# These tests aren't automatically triggered by github actions because I
# have not properly mocked them to avoid hitting AWS and
# testing properly. They do work when called though.
class AWSFinancialDisclosureTests(DockerTestBase):
    """Convert Images to PDFs"""

    aws_url = "https://com-courtlistener-storage.s3-us-west-2.amazonaws.com"

    def test_images_to_pdf(self):
        """Test image conversion from multiple image urls to PDF"""

        pdf_path = os.path.join(self.assets_dir, "fd", "test_url.pdf")
        with open(pdf_path, "rb") as f:
            answer = f.read()

        test_fd = {
            "paths": [
                "Armstrong-SB J3. 09. CAN_R_11_Page_1.tiff",
                "Armstrong-SB J3. 09. CAN_R_11_Page_2.tiff",
                "Armstrong-SB J3. 09. CAN_R_11_Page_3.tiff",
                "Armstrong-SB J3. 09. CAN_R_11_Page_4.tiff",
                "Armstrong-SB J3. 09. CAN_R_11_Page_5.tiff",
                "Armstrong-SB J3. 09. CAN_R_11_Page_6.tiff",
            ],
            "key": "2011/A-E/Armstrong-SB J3. 09. CAN_R_11",
        }
        urls = []
        for page in test_fd["paths"]:
            urls.append(
                f"{self.aws_url}/financial-disclosures/{test_fd['key']}/{page}"
            )

        bte_response = requests.post(
            self.BTE_URLS["images-to-pdf"],
            json=json.dumps({"urls": urls}),
            timeout=60 * 60,
        )
        self.assertEqual(200, bte_response.status_code, msg="Server failed")
        self.assertEqual(bte_response.content, answer, msg="Conversion failed")
        self.assertEqual(413342, len(bte_response.content))

    def test_image_to_pdf(self):
        """Test image conversion from a single image url to PDF"""
        pdf_path = os.path.join(self.assets_dir, "fd", "tiff_to_pdf.pdf")
        with open(pdf_path, "rb") as f:
            answer = f.read()

        path_AE_2011 = "financial-disclosures/2011/A-E"
        judge = "Abel-MR.%20M.%2006.%20OHS"
        urls = [f"{self.aws_url}/{path_AE_2011}/{judge}.tiff"]

        bte_response = requests.post(
            self.BTE_URLS["images-to-pdf"],
            json=json.dumps({"urls": urls}),
            timeout=60 * 60,
        )
        self.assertEqual(200, bte_response.status_code, msg="Server failed")
        self.assertEqual(bte_response.content, answer, msg="Conversion failed")


if __name__ == "__main__":
    unittest.main()
