from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import sys

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
    password = os.environ.get('ENV_PASSPHRASE')
    if not password:
        if len(sys.argv) > 1:
            password = sys.argv[1]
        else:
            # Fallback for local dev if needed, or raise error
            print("Error: ENV_PASSPHRASE environment variable or argument required.")
            sys.exit(1)
            
    file_path = 'infra/.env.encrypted'
    # Allow overriding file path via second arg or just assume default relative to root
    # Adjust for running from different directories if needed, but let's stick to root execution
    if not os.path.exists(file_path):
        # Try finding it relative to current script if run from elsewhere
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, '.env.encrypted')
        
    decrypt_file(file_path, password)
