import os
import sys
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.Hash import SHA512

args = sys.argv


def splitDataIntoPairs(data):
    # split the string by the delimiter
    filePairsWithoutNewLine = data.split(b"\n")

    # append the delimiter back to each element except the last one
    filePairs = [elem + b"\n" for elem in filePairsWithoutNewLine[:-1]]

    # add the last element without appending the delimiter
    filePairs.append(filePairsWithoutNewLine[-1])

    return filePairs


def decryptData(masterPassword):
    with open("db.bin", "rb") as f:
        salt = f.read(16)
        tag = f.read(16)
        nonce = f.read(15)
        ciphertext = f.read()

    keys = PBKDF2(masterPassword, salt, 64, count=1000000, hmac_hash_module=SHA512)
    key = keys[:32]

    cipher = AES.new(key, AES.MODE_OCB, nonce=nonce)

    try:
        message = cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        print("Couldn't find address or failed integrity check.")
        sys.exit(1)

    return message


# password manager initiation
if args[1] == "init":
    masterPassword = args[2]

    salt = get_random_bytes(16)
    keys = PBKDF2(masterPassword, salt, 64, count=1000000, hmac_hash_module=SHA512)
    key = keys[:32]
    cipher = AES.new(key, AES.MODE_OCB)

    ciphertext, tag = cipher.encrypt_and_digest(b"")

    with open("db.bin", "wb") as f:
        f.write(salt)  # 16 bytes
        f.write(tag)  # 16 bytes
        f.write(cipher.nonce)  # 15 bytes, IV - initialization vector

    print("Password manager initialized.")

if args[1] == "put":

    # is the password manager initialized?
    try:
        fileSize = os.stat("db.bin").st_size
    except:
        print("First initialize the password manager!")
        sys.exit(1)

    masterPassword = args[2]

    newAddress = args[3]
    newPassword = args[4]

    fileData = decryptData(masterPassword)

    newPair = f"{newAddress} {newPassword}\n".encode("ascii")

    salt = get_random_bytes(16)
    keys = PBKDF2(masterPassword, salt, 64, count=1000000, hmac_hash_module=SHA512)
    key = keys[:32]
    cipher = AES.new(key, AES.MODE_OCB)

    # will become true if the address already exists in the database
    sameAddress = False

    newFileData = b""

    filePairs = splitDataIntoPairs(fileData)

    # checking if the address already is stored in the database
    modifiedAddress = b""
    for i in range(len(filePairs)):
        if len(filePairs[i]) == 0:
            continue

        address, passwordWithNewline = filePairs[i].split(b" ")
        password = passwordWithNewline.replace(b"\n", b"")

        if newAddress.encode("ascii") == address:
            sameAddress = True

            newPair = f"{newAddress} {newPassword}\n".encode("ascii")
            filePairs[i] = newPair

            newFileData += newPair

            modifiedAddress = address

    for i in range(len(filePairs)):
        if len(filePairs[i]) == 0:
            continue

        address, passwordWithNewline = filePairs[i].split(b" ")
        password = passwordWithNewline.replace(b"\n", b"")

        if modifiedAddress != address:
            newFileData += filePairs[i]

    if not sameAddress:
        newPair = f"{newAddress} {newPassword}\n".encode("ascii")
        newFileData += newPair

    ciphertext, tag = cipher.encrypt_and_digest(newFileData)

    with open("db.bin", "wb") as f:
        f.write(salt)  # 16 bytes
        f.write(tag)  # 16 bytes
        f.write(cipher.nonce)  # 15 bytes, IV - initialization vector
        f.write(ciphertext)

    print(f"Stored password for {newAddress}.")

if args[1] == "get":

    # is the database initialized?
    try:
        fileSize = os.stat("db.bin").st_size
    except:
        print("First initialize the password manager!")
        sys.exit(1)

    foundAddress = False

    masterPassword = args[2].encode("ascii")

    wantedAddress = args[3]

    data = decryptData(masterPassword)

    filePairs = splitDataIntoPairs(data)

    if len(filePairs[0]) == 0:
        print("Couldn't find address or failed integrity check.")
        sys.exit(0)

    for p in filePairs:
        if len(p) == 0:
            continue

        address, passwordWithNewline = p.split(b" ")
        password = passwordWithNewline.replace(b"\n", b"")

        if wantedAddress.encode("ascii") == address:
            foundAddress = True
            print(f"Password for {address.decode()} is: {password.decode()}")
            sys.exit(0)

    if not foundAddress:
        print("Couldn't find address or failed integrity check.")

if args[1] == "getall":
    masterPassword = args[2]

    data = decryptData(masterPassword)
    filePairs = splitDataIntoPairs(data)

    if len(filePairs[0]) == 0:
        print("Empty.")
        sys.exit(0)

    print("address password")
    print("--------------------")

    for p in filePairs:
        if len(p) == 0:
            continue

        address, passwordWithNewline = p.split(b" ")
        password = passwordWithNewline.replace(b"\n", b"")

        print(f"{address.decode()} {password.decode()}")