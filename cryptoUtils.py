# Copyright 2018 Morningstar Inc. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64, logging, os

from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from flask import session

class Cryptor(object):

  def encrypt(self, data):
    BLOCK_SIZE = 32
    # the character used for padding
    # used to ensure that your value is always a multiple of BLOCK_SIZE
    PADDING = '{'
    encoded = ''
    try:
        pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * PADDING
        EncodeAES = lambda c, s: base64.b64encode(c.encrypt(pad(s)))
        secret = os.urandom(BLOCK_SIZE)
        secretToken = b64encode(secret).decode('utf-8')
        logging.debug("Secret Key: %s for user %s generated",secretToken, session.get('_user'))
        cipher = AES.new(secret, AES.MODE_ECB)
        encoded = EncodeAES(cipher, data)
        logging.debug('Encrypted string:%s', encoded)
        session['_eUser'] = encoded
        session['_eUserK'] = secretToken
    except Exception as e:
        logging.error('Cryptor.encrypt:Error while encrypting:' + data + ' :\n\n' + 
            repr(e), exc_info=True)
    return encoded

  def decrypt(self, encryptedString):
    PADDING = '{'
    decoded = ''
    try:
        DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
        secretToken = session.get('_eUserK')
        secret = b64decode(secretToken.encode('utf-8'))
        cipher = AES.new(secret, AES.MODE_ECB)
        decoded = DecodeAES(cipher, encryptedString)
    except Exception as e:
        logging.error('Cryptor.decrypt:Error while decrypting:' + str(encryptedString) + ' :\n\n' + 
            repr(e), exc_info=True)
    return decoded
