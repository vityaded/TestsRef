import os
import subprocess
import sys

def generate_self_signed_cert():
    cert_dir = os.path.join(os.getcwd(), 'cert')
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')

    print("Generating self-signed SSL certificate...")

    # Generate a self-signed certificate using OpenSSL
    subprocess.call([
        'openssl', 'req', '-new', '-x509', '-days', '365',
        '-nodes', '-out', cert_file, '-keyout', key_file,
        '-subj', '/CN=localhost'
    ])

    print(f"Certificate generated at: {cert_file}")
    print(f"Key generated at: {key_file}")
    print("SSL setup is complete.")

if __name__ == '__main__':
    # Check if OpenSSL is installed
    result = subprocess.run(['openssl', 'version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print("Error: OpenSSL is not installed or not found in system PATH.")
        sys.exit(1)

    generate_self_signed_cert()
