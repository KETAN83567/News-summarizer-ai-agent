from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from memory import load_memory, record_feedback


class MemoryTests(unittest.TestCase):
    def test_feedback_accumulates_and_is_bounded(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            for _ in range(8):
                record_feedback("like_topic", "AI agents", path)
            memory = load_memory(path)
            self.assertEqual(memory["topics"]["AI agents"], 5.0)

    def test_negative_source_feedback(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            record_feedback("mute_source", "Noise Daily", path)
            memory = load_memory(path)
            self.assertEqual(memory["sources"]["Noise Daily"], -1.0)


if __name__ == "__main__":
    unittest.main()
