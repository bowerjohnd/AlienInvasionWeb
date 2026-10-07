import sys
import platform
import json
import base64
import hashlib
import asyncio
from pathlib import Path

class GameStats:
    """Track statistics for Alien Invasion."""

    SECRET_KEY = 72
    SECRET_HASH = b"MySuperSecretGameKeyDefinitelyNot72"
    SUBMIT_URL = "/highscores.php"

    def __init__(self, ai_game):
        """Initialize statistics."""
        self.settings = ai_game.settings
        self.reset_stats()

        # High score should never be reset.
        self.high_score = 0
        self.high_level = 1
        self.level = 1

        # Read in saved stats.
        #self.load_saved_stats()    # blocking during testing


    def reset_stats(self):
        """Initialize statistics that can change during the game."""
        self.ships_left = self.settings.ship_limit
        self.score = 0
        self.level = 1
    
    async def submit_stats_online(saved_stats_dict):
        if sys.platform != "emscripten":
            return

        # Dictionary to JSON
        json_string = json.dumps(saved_stats_dict)

        # Try submitting score
        try:
            response = await pyfetch(
                SUBMIT_URL,
                method="POST",
                headers={"Content-Type": "Application/json"},
                body=json_string
            )
            if response.status == 200:
                print("Secure stats submitted.")
        except Exception as e:
            print(f"Network error: {e}")

    def post_stats(self):
        """Encrypt stats and send to submit method"""

        hash_high_score = self._encrypt_number_value(self.high_score)
        hash_high_level = self._encrypt_number_value(self.high_level)

        self.stats_to_submit['high_score'] = hash_high_score
        self.stats_to_submit['high_level'] = hash_high_level

        self.submit_stats_online(self.stats_to_submit)

    async def get_stats_from_file(self):
        """Load stats from file and set in game high stats."""

        filename = 'saved_stats.json'

        # Load in saved stats file
        try:
            # Running on browser via pygbag or local
            if sys.platform == "emscripten":
                # Async load for web/WASM environment
                async with platform.fopen(filename, "r") as f:
                    content = await f.read()
            else:
                return {"high_score": 200, "high_level": 2}

            return json.load(content)
        
        except Exception as e:
            print("Error loading file:", e)
            return {"high_score": 999, "high_level": 3}

    def load_saved_stats(self):
        """Get high stats from file, set high stats in game."""

        self.loaded_in_dict = self.get_stats_from_file()

        # Set high score in game
        if 'high_score' in self.loaded_in_dict:
            self.saved_high_score = self._decrypt_number_value(self.loaded_in_dict['high_score'])
        else:
            self.saved_high_score = 0

        # Set high level in game
        if 'high_level' in self.loaded_in_dict:
            self.saved_high_level = self._decrypt_number_value(self.loaded_in_dict['high_level'])
        else:
            self.saved_high_level = 1

    def _encrypt_number_value(self, value: int) -> str:
        """Encrypt stat for tamper-proofing saved file."""

        # Scramble the value using SECRET KEY
        scrambled = value ^ self.SECRET_KEY
        value_bytes = scrambled.to_bytes((value.bit_length() + 7) // 8 or 1, "big")

        # Generate a "tamper-proof" signature
        hasher = hashlib.sha256(self.SECRET_HASH + value_bytes)
        signature_bytes = hasher.digest()[:4]

        # Return encoded scrambled and hash combined
        combined_bytes = value_bytes + signature_bytes
        return base64.b64encode(combined_bytes).decode('utf-8')

    def _decrypt_number_value(self, scrambled_value: str) -> int:
        """Decrypt stat and check for tampering of saved file."""

        try:
            # Decode text back to bytes            
            combined_bytes = base64.b64decode(scrambled_value.encode('utf-8'))

            # Separate the scrambled from signature
            value_bytes = combined_bytes[:-4]
            signature_bytes = combined_bytes[-4:]

            # Check the signature for tampering
            expected_signature = hashlib.sha256(self.SECRET_HASH + value_bytes).digest()[:4]

            if signature_bytes != expected_signature:
                raise ValueError("Save file may be corrupted, signatures don't match.")

            # Unscramble and return value
            scrambled = int.from_bytes(value_bytes, "big")
            return scrambled ^ self.SECRET_KEY

        except Exception as e:
            # saved stats may have been tampered with, return 0
            print("add to non-existant log:", e)
            return 0