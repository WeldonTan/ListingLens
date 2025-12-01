from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

def encrypt_file(file_path, password):
    # Generate a key from the password
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    f = Fernet(key)

    # Read the file content
    with open(file_path, 'rb') as file:
        file_data = file.read()

    # Encrypt the file content
    encrypted_data = f.encrypt(file_data)

    # Write the encrypted data to a new file
    with open(file_path + '.encrypted', 'wb') as file:
        file.write(salt + encrypted_data)

if __name__ == '__main__':
    encrypt_file('infra/.env', 'listinglens')
