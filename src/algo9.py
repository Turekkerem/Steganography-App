"""
"A robust data hiding scheme using modular key mapping and AES encryption"
Naman Beri, Vibha Gaur, Ravneet Kaur (2026)
Journal of Discrete Mathematical Sciences & Cryptography
ISSN 0972-0529 (Print), ISSN 2169-0065 (Online)
Vol. 29 (2026), No. 6, pp. 2349–2363
http://dx.doi.org/10.47974/JDMSC-2610
The article is located at articles/9/a-robust-data-hiding-scheme-using-modular-key-mapping-and-ae.pdf
"""
from Crypto.Cipher import AES
from Crypto.Util.number import bytes_to_long, long_to_bytes
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

#key must be 32 bits
def AES_encrypt(A, key, IV):
    cipher = AES.new(key,AES.MODE_CTR,nonce = IV)
    return cipher.encrypt(A)

def AES_decrypt(A, key, IV):
    cipher = AES.new(key,AES.MODE_CTR,nonce = IV)
    return cipher.decrypt(A)

def lcg(x, a, b, m):
    return (x*a + b) % m

def embed(covertext, secret, key):
    A = create_main_array(covertext)
    B = []
    #decide on a better way to pick these, dont hard code
    a, b = 1, 5
    x0 = bytes_to_long(os.urandom(64))
    for i in secret:
        x = lcg(x0, a, b, len(A[i]))
        x0 = x
        B.append(A[i][x])
    IV = os.urandom(12)
    return AES_encrypt(bytes(B), key, IV), IV

def extract(covertext, B_encrypted, key, IV):
    A = create_main_array(covertext)
    B = list(AES_decrypt(B_encrypted, key, IV))
    print(B)
    #for i in range(0, len())

covertext="cokolwiek chlopie"
secret="ch"
key = os.urandom(32)
encrypted_B, iv = embed(covertext, secret, key)
print(encrypted_B, iv, sep='\n')
extract(covertext,encrypted_B,key,iv)

