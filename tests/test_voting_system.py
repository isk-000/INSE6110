import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from inse6110_voting_system import (
    hash_password, verify_password, sign_vote, 
    encrypt_data, decrypt_data, generate_hmac, verify_hmac,
    public_key, private_key
)

class TestVotingSystem(unittest.TestCase):

    def test_password_hashing(self):
        password = "securepassword"
        hashed = hash_password(password)
        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrongpassword", hashed))

    def test_vote_signing(self):
        vote = 1
        voter = "alice"
        signature = sign_vote(vote, voter)
        self.assertIsInstance(signature, bytes)

    def test_hmac_generation_and_verification(self):
        voter = "alice"
        candidate = "bob"
        nonce = "random_nonce_123"
        message = f"{voter}:{candidate}:{nonce}"
        mac = generate_hmac(message, candidate, nonce)

        self.assertTrue(verify_hmac(message, candidate, nonce, mac))
        self.assertFalse(verify_hmac("tampered_vote", candidate, nonce, mac))

    def test_aes_encryption(self):
        data = {"vote": 1, "signature": "abc123"}
        encrypted = encrypt_data(data)
        decrypted = decrypt_data(encrypted)
        self.assertEqual(data, decrypted)

    # def test_hmac_generation_and_verification(self):
    #     message = "encrypted_vote"
    #     mac = generate_hmac(message)
    #     self.assertTrue(verify_hmac(message, mac))
    #     self.assertFalse(verify_hmac("tampered_vote", mac))

    def test_homomorphic_encryption(self):
        vote1 = public_key.encrypt(1)
        vote2 = public_key.encrypt(2)
        encrypted_sum = vote1 + vote2
        decrypted_sum = private_key.decrypt(encrypted_sum)
        self.assertEqual(decrypted_sum, 3)

if __name__ == "__main__":
    unittest.main()
