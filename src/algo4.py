"""
"Text steganography: enhanced character-level embedding algorithm using font attribute with increased resilience to statistical attacks"
Shreya Narasimhan KL, Bala Krishnan R (2024 / 2025).
Multimedia Tools and Applications, 84:9367–9392. https://doi.org/10.1007/s11042-024-19272-y
The article is located at articles/4/s11042-024-19272-y.pdf
"""

import os
from typing import Dict, Any, Tuple, Optional, Union
import docx
from docx.document import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PyQt5.QtWidgets import QMessageBox, QLabel, QSplitter, QPushButton, QFileDialog
from templates import TabTemplate

#Character and String Mapping (CSM)
CSM_INITIAL = {
    "A": "WRZFOIN",
    "B": "F CWQXP",
    "C": "JMFXY Z",
    "D": "XA.MNTU",
    "E": "YCHIJOS",
    "F": "KUX ZJC",
    "G": " .BCPQX",
    "H": "BLOSWMI",
    "I": "PJGALHO",
    "J": "NSVOBGH",
    "K": "UWY.TSL",
    "L": "DIREFCQ",
    "M": "GHTR.WB",
    "N": "ZBADEFG",
    "O": "MNSLAB.",
    "P": "TVIZM.A",
    "Q": "SGKPHEM",
    "R": "HEUVIYJ",
    "S": "IYLNUAK",
    "T": "OFJGCDE",
    "U": "VDEHKLY",
    "V": "LONQSUR",
    "W": "QP KXRV",
    "X": "EZDYGPT",
    "Y": ".KQUVZ ",
    "Z": "AXMTRVD",
    " ": "RTWBDNF",
    ".": "CQPJ KW"
}

#Group 1: Perform LCS (left circular shift)
GROUP1 = [" ", "A", "S", "N", "R", "U", "M", "F", "B", "C", "V", "Z", "X", "Q"]
#Group 2: Perform RCS
GROUP2 = ["E", "T", "O", "I", "H", "D", "L", "W", "G", "Y", ".", "K", "P", "J"]

#Character spacing modifications based on position
POS_TO_TWIPS = {
    0: -2,  # Condense by 0.1 pt
    1: -4,  # Condense by 0.2 pt
    2: -6,  # Condense by 0.3 pt
    3: 2,   # Expand by 0.1 pt
    4: 4,   # Expand by 0.2 pt
    5: 6,   # Expand by 0.3 pt
    6: 8    # Expand by 0.4 pt
}
TWIPS_TO_POS= {v: k for k, v in POS_TO_TWIPS.items()}

# End-of-Secret pattern
EOS = ". . ."

def shift_csm(csm: Dict[str, str], char: str) -> Dict[str, str]:
    """
    Shifts all strings in CSM based on the embedded/extracted secret character:
    Perform left circular shift if char in Group 1
    Perform right circular shift if char in Group 2
    """
    new_csm: Dict[str, str] = {}
    if char in GROUP1:
        for k, v in csm.items():
            new_csm[k] = v[1:] + v[:1] #shift left
    else:
        for k, v in csm.items():
            new_csm[k] = v[-1:] + v[:-1] #shift right
    return new_csm

def embed(cover_text: str, secret_message: str) -> Tuple[Document, Dict[str, Any]]:
    if not cover_text or not cover_text.strip():
        raise ValueError("Cover text cannot be empty.")
    if not secret_message or not secret_message.strip():
        raise ValueError("Secret message cannot be empty.")

    #convert secret message to uppercase
    clean_secret = secret_message.strip().upper()
    unsupported_chars = set(c for c in clean_secret if c not in CSM_INITIAL)
    if unsupported_chars:
        unsupported_str = ", ".join(repr(c) for c in sorted(list(unsupported_chars))) #repr returns canonic representation
        raise ValueError(
            f"Secret message contains unsupported character(s): [{unsupported_str}]. "
            "This algorithm only supports English letters (A-Z), spaces, and dots."
        )

    full_secret = clean_secret + EOS
    csm = CSM_INITIAL.copy()
    #create a new document and split text into paragraphs
    #docx requires you to split text into paragraphs
    doc = docx.Document()
    paragraphs = cover_text.splitlines()
    if not paragraphs:
        paragraphs = [cover_text]

    sec_idx = 0
    sec_len = len(full_secret)

    for paragraph in paragraphs:
        new_paragraph = doc.add_paragraph()
        unmod_buf = []
        for c in paragraph:
            if sec_idx < sec_len:
                target_char = full_secret[sec_idx]
                csm_string = csm[target_char]
                c_upper = c.upper()
                #find the first occurence of ANY of the characters in csm_string
                if c_upper in csm_string:
                    #write unmodified characters to file
                    if unmod_buf:
                        new_paragraph.add_run("".join(unmod_buf))
                        unmod_buf = []

                    #convert pos to twips (inter-character spacing)
                    pos = csm_string.index(c_upper)
                    twips = POS_TO_TWIPS[pos]

                    # Add the modified character as its own run with w:spacing
                    r = new_paragraph.add_run(c) #add c as a new run
                    rPr = r._r.get_or_add_rPr() #return the xml element that contains information about inter-character spacing
                    sp = OxmlElement('w:spacing') #creates a new xml element 'w:spacing'
                    #sets w:val to twips. qn() returns a fully qualified name for w:val
                    sp.set(qn('w:val'), str(twips)) 
                    rPr.append(sp) #appends the spacing element as a child of rPr
                    """
                    The final XML might look like this:
                    <w:r>
                    <w:rPr>
                        <w:spacing w:val="-2"/>
                    </w:rPr>
                    <w:t>A</w:t>
                    </w:r>
                    """
                    csm = shift_csm(csm, target_char)
                    sec_idx += 1
                    continue
            unmod_buf.append(c)

        #add whatever unchanged characters are left over
        if unmod_buf:
            new_paragraph.add_run("".join(unmod_buf))
            unmod_buf = []

    if sec_idx < sec_len:
        raise ValueError(
            f"Cover text is too short! Embedded {sec_idx}/{sec_len} characters "
            f"(Secret: {len(clean_secret)}, EoS: {len(EOS)}). "
            "Please provide a longer cover text."
        )

    info = {
        "secret_len": len(clean_secret),
        "total_paragraphs": len(paragraphs)
    }
    return doc, info

def extract(doc: Document) -> str:
    csm = CSM_INITIAL.copy()
    extracted = []
    eos_found = False

    for paragraph in doc.paragraphs:
        for r in paragraph.runs:
            twips = 0
            rPr = r._r.find(qn('w:rPr'))
            if rPr is not None:
                sp = rPr.find(qn('w:spacing'))
                if sp is not None:
                    try:
                        twips = int(sp.get(qn('w:val'), 0))
                    except ValueError:
                        twips = 0

            if twips != 0:
                pos = TWIPS_TO_POS.get(twips)
                if pos is not None:
                    c = r.text
                    c_upper = c.upper()
                    matched_char = None
                    for k, v in csm.items():
                        if v[pos] == c_upper:
                            matched_char = k
                            break
                    if matched_char is None:
                        raise ValueError(
                            f"Corrupted stego work: character {repr(c)} at position {pos} "
                            "could not be matched to any string in CSM."
                        )
                    extracted.append(matched_char)
                    csm = shift_csm(csm, matched_char)
                    if "".join(extracted).endswith(EOS):
                        eos_found = True
                        break
            if eos_found:
                break
        if eos_found:
            break

    if not eos_found:
        raise ValueError(
            "Corrupted stego work or invalid document: End-of-Secret marker was not found. "
            "Ensure the document is a valid stego document."
        )

    secret_message = "".join(extracted)[:-len(EOS)]
    return secret_message

class Algo4Tab(TabTemplate):
    def __init__(self):
        super().__init__()

        self.current_stego_doc: Optional[Document] = None

        # Add custom status label on the right side under the output text box
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #333; font-size: 14pt; padding: 6px; background: #f8f9fa; "
            "border: 1px solid #dee2e6; border-radius: 4px; margin-top: 6px;"
        )

        splitter = self.findChild(QSplitter)
        if splitter and splitter.count() > 1:
            right_widget = splitter.widget(1)
            right_widget.layout().addWidget(self.status_label)

        #Additional action buttons for DOCX handling
        self.save_docx_button = QPushButton("Save Stego DOCX")
        self.save_docx_button.setEnabled(False)
        self.load_cover_button = QPushButton("Load Cover DOCX")

        action_layout = self.action_group.layout()
        action_layout.addWidget(self.load_cover_button)
        action_layout.addWidget(self.save_docx_button)

        help_text = (
            "Algorithm 4: Enhanced Character-Level Embedding using Font Attributes\n\n"
            "This algorithm hides a secret message inside a Microsoft Word document "
            "by altering inter-character font spacing (-0.3 pt to +0.4 pt).\n"
            "It uses a Frequency Normalization Set (FNS) / Character & String Mapping (CSM), "
            "combined with an unbiased dual circular shift (Left for Group 1, Right for Group 2) "
            "to resist statistical frequency analysis attacks.\n\n"
            "SUPPORTED CHARACTERS:\n"
            "• Secret message: English letters (A-Z, case-insensitive), spaces, and dots ('.').\n"
            "• Cover text: Any text containing sufficient English letters, spaces, and dots.\n"
            "• Importantly, the secret MUST NOT contain the EOS phrase [. . .] (ignore the brackets)\n\n"
            "EMBEDDING:\n"
            "1. Enter/paste cover text into 'Cover Text' (or click 'Load Cover DOCX').\n"
            "2. Enter secret message into 'Secret Message'.\n"
            "3. Click 'Embed Secret Message'.\n"
            "4. Click 'Save Stego DOCX' to save the generated stego Word document.\n\n"
            "EXTRACTION:\n"
            "1. Click 'Extract from DOCX File' and select the stego .docx document.\n"
            "2. The decoded secret message will appear in 'Extracted Text'."
        )

        self.customize_ui(
            cover_lbl="Cover Text",
            secret_lbl="Secret Message",
            key_lbl="Key (N/A)",
            embed_btn="Embed Secret Message",
            extract_btn="Extract from DOCX File",
            output_grp="Extracted Text",
            tab_help_text=help_text
        )

        self.key_input.setText("N/A")
        self.key_input.setEnabled(False)

        # Connect button triggers
        self.embed_button.clicked.connect(self.do_embed)
        self.extract_button.clicked.connect(self.do_extract)
        self.save_docx_button.clicked.connect(self.do_save_docx)
        self.load_cover_button.clicked.connect(self.do_load_cover_docx)

    def do_load_cover_docx(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Cover DOCX Document", "", "Word Documents (*.docx)"
        )
        if not file_path:
            return
        try:
            doc = docx.Document(file_path)
            full_text = "\n".join(new_paragraph.text for new_paragraph in doc.paragraphs)
            self.covertext_input.setPlainText(full_text)
            self.status_label.setText(
                f"<b>Loaded Cover Document:</b> <code>{os.path.basename(file_path)}</code> "
                f"({len(full_text)} characters, {len(doc.paragraphs)} paragraphs)"
            )
        except Exception as e:
            QMessageBox.critical(self, "File Load Error", f"Failed to load DOCX: {e}")

    def do_embed(self):
        cover = self.covertext_input.toPlainText()
        secret = self.secret_input.toPlainText()

        if not cover.strip():
            QMessageBox.warning(self, "Error", "Cover text cannot be empty.")
            return
        if not secret.strip():
            QMessageBox.warning(self, "Error", "Secret message cannot be empty.")
            return
        try:
            doc, info = embed(cover, secret)
            #enable the saving of the created docx
            self.current_stego_doc = doc
            self.save_docx_button.setEnabled(True)

            summary = (
                f"Embedding successful!\n\n"
                f"Secret message of {info['secret_len']} characters successfully embedded!\n"
                f"Total font spacing modifications: {info['secret_len']+len(EOS)} characters (including EOS).\n"
                f"Click 'Save Stego DOCX' to save the generated document to your computer."
            )
            self.result_output.setPlainText(summary)

            self.status_label.setText(
                f"<b>Embedding Successful!</b><br>"
                f"• <b>Secret Length:</b> {info['secret_len']} characters (+ 5 EoS markers)<br>"
                f"• <b>Modified Characters:</b> {info['secret_len']+len(EOS)} characters spaced (-0.3 pt to +0.4 pt)<br>"
                f"• <b>Status:</b> Ready to save the stego docx. <br>Click <b>'Save Stego DOCX'</b> to export."
            )

        except Exception as e:
            QMessageBox.critical(self, "Embedding Error", str(e))

    def do_save_docx(self):
        if self.current_stego_doc is None:
            QMessageBox.warning(self, "Warning", "No stego document has been created yet.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Stego Word Document", "stego_output.docx", "Word Documents (*.docx)"
        )
        if not file_path:
            return
        try:
            self.current_stego_doc.save(file_path)
            QMessageBox.information(
                self, "Saved Successfully", f"Stego document saved to:\n{file_path}"
            )
            self.status_label.setText(
                f"<b>Stego DOCX Saved:</b> <code>{os.path.basename(file_path)}</code>"
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save DOCX: {e}")

    def do_extract(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Stego Word Document", "", "Word Documents (*.docx)"
        )
        if not file_path:
            return
        try:
            secret = extract(docx.Document(file_path))
            self.result_output.setPlainText(secret)

            self.status_label.setText(
                f"<b>Extraction Successful!</b><br>"
                f"• <b>Extracted Secret Length:</b> {len(secret)} characters<br>"
                f"• <b>Modified Characters Decoded:</b> {len(secret)+len(EOS)} characters<br>"
                f"• <b>Source File:</b> <code>{os.path.basename(file_path)}</code>"
            )
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", str(e))
