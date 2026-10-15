"""
"A robust data hiding scheme using modular key mapping and AES encryption"
Naman Beri, Vibha Gaur, Ravneet Kaur (2026)
Journal of Discrete Mathematical Sciences & Cryptography
ISSN 0972-0529 (Print), ISSN 2169-0065 (Online)
Vol. 29 (2026), No. 6, pp. 2349–2363
http://dx.doi.org/10.47974/JDMSC-2610
"""
from Crypto.Cipher import AES
import os
#Covertext MUST contain every character in secret
def create_main_array(covertext):
    #assumes only lowercase latin characters
    A = {}
    for i in range(97, 123):
        A[chr(i)] = []
        for j in range(0, len(covertext)):
            if covertext[j] == chr(i):
                A[chr(i)].append(j)

    return A

def AES_encrypt(A, key, IV):
    cipher = AES.new(key,AES.MODE_CTR,nonce = IV)
    return cipher.encrypt(A)

def AES_decrypt(A, key, IV):
    cipher = AES.new(key,AES.MODE_CTR,nonce = IV)
    return cipher.decrypt(A)

