import sys
import json
from Crypto.Protocol.KDF import scrypt
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

MAX_LEN = 256

def pad(value):
    return value + ' ' * (MAX_LEN - len(value))

def unpad(value):
    return value.rstrip(' ')

def encrypt(masterPassword, plaintext):
    salt = get_random_bytes(16) # 16 random bytes so that same master produces different keys
    key = scrypt(masterPassword, salt, key_len=32, N=2**17, r=8, p=1) # KDF

    cipher = AES.new(key, AES.MODE_GCM) # galois counter mode, provides confidentiality and integrity, here 16 rv nonce provides randomness
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)

    return salt, cipher.nonce, tag, ciphertext


def decrypt(masterPassword, salt, nonce, tag, ciphertext):
    key = scrypt(masterPassword, salt, key_len=32, N=2**17, r=8, p=1) # key length in bytes, n is the cpu memory cost factor, r is the block size (128 * r), p is the parallelization
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    try:
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        print("Incorrect master password or data integrity compromised.")
        exit(1)

    return plaintext


def readFile(file):
    with open(file, 'rb') as f:
        data = f.read()
    salt = data[:16]
    nonce = data[16:32]
    tag = data[32:48]
    ciphertext = data[48:]

    return salt, nonce, tag, ciphertext


def writeFile(file, salt, nonce, tag, ciphertext):
    with open(file, 'wb') as f:
        f.write(salt + nonce + tag + ciphertext)


def init(masterPassword):
    salt, nonce, tag, ciphertext = encrypt(masterPassword, b'{}')
    writeFile('passwords.bin', salt, nonce, tag, ciphertext)
    print("Password manager initialized.")


def put(masterPassword, newAddress, newPassword):
    salt, nonce, tag, ciphertext = readFile('passwords.bin')
    plaintext = decrypt(masterPassword, salt, nonce, tag, ciphertext)

    addressPasswords = json.loads(plaintext.decode())
    addressPasswords[pad(newAddress)] = pad(newPassword) # adds or updates the addres password pair, with padding to obfuscate length

    newPlaintext = json.dumps(addressPasswords).encode()
    salt, nonce, tag, ciphertext = encrypt(masterPassword, newPlaintext)
    writeFile('passwords.bin', salt, nonce, tag, ciphertext)

    print(f"Password for {newAddress} added/updated.")


def get(masterPassword, address):
    salt, nonce, tag, ciphertext = readFile('passwords.bin')
    plaintext = decrypt(masterPassword, salt, nonce, tag, ciphertext)

    addressPasswords = json.loads(plaintext.decode())
    # print(addressPasswords) # for debugging
    paddedAddress = pad(address)
    if paddedAddress in addressPasswords:
        print(f"Password for {address} is: {unpad(addressPasswords[paddedAddress])}")
    else:
        print(f"No password or invalid address.")


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python3 PasswordManager.py init <master_password>")
        print("Usage: python3 PasswordManager.py put <master_password> <address> <password>")
        print("Usage: python3 PasswordManager.py get <master_password> <address>")
        exit(1)

    command = args[0]
    masterPassword = args[1]

    match command:
        case 'init':
            init(masterPassword)
        case 'put':
            if len(args) != 4:
                print("Usage: PasswordManager.py put <master_password> <address> <password>")
                exit(1)

            address = args[2]
            password = args[3]
            put(masterPassword, address, password)
        case 'get':
            if len(args) != 3:
                print("Usage: PasswordManager.py get <master_password> <address>")
                exit(1)

            address = args[2]
            get(masterPassword, address)
        case _:
            print(f'Unknown command: {command}')
            exit(1)


if __name__ == '__main__':
    main()