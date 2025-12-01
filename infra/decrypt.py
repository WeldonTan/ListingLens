from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

def decrypt_file(file_path, password):
    # Read the salt and encrypted data
    with open(file_path, 'rb') as file:
        salt = file.read(16)
        encrypted_data = file.read()

    # Generate the key from the password and salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    f = Fernet(key)

    # Decrypt the data
    decrypted_data = f.decrypt(encrypted_data)

    # Write the decrypted data to a new file
    with open(file_path.replace('.encrypted', ''), 'wb') as file:
        file.write(decrypted_data)

if __name__ == '__main__':
    decrypt_file('infra/.env.encrypted', 'listinglens')
