import os
import json
import unittest
import numpy as np
import soundfile as sf
from interface_layer.ears import analyze_stem_features, analyze_stem_clash

class TestAudioAnalysis(unittest.TestCase):
    def setUp(self):
        self.temp_files = []
        self.sr = 44100
        self.duration = 1.0
        
        # Default mono file
        self.test_file = "test_sine.wav"
        t = np.linspace(0, self.duration, int(self.sr * self.duration), endpoint=False)
        self.y = 0.5 * np.sin(2 * np.pi * 440.0 * t)
        sf.write(self.test_file, self.y, self.sr)
        self.temp_files.append(self.test_file)

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def test_successful_analysis(self):
        json_output = analyze_stem_features(self.test_file)
        data = json.loads(json_output)
        
        self.assertEqual(data["file_name"], self.test_file)
        self.assertAlmostEqual(data["duration_seconds"], self.duration, places=2)
        self.assertEqual(data["status"], "success")
        self.assertIsNone(data["error_message"])
        
        features = data["features"]
        self.assertIsNotNone(features)
        self.assertIn("lufs_integrated", features)
        self.assertIn("rms_mean", features)
        self.assertIn("spectral_centroid_mean_hz", features)
        self.assertIn("peak_amplitude_dbfs", features)
        self.assertIn("stereo_correlation_mean", features)
        
        # Verify peak amplitude is close to -6.02 dBFS (20 * log10(0.5))
        self.assertAlmostEqual(features["peak_amplitude_dbfs"], -6.02, places=1)
        
        # Verify RMS is close to 0.5 / sqrt(2) = 0.3535
        self.assertAlmostEqual(features["rms_mean"], 0.3535, places=2)

        # Verify stereo correlation for mono is 1.0
        self.assertEqual(features["stereo_correlation_mean"], 1.0)

    def test_error_handling(self):
        # Pass a non-existent file
        json_output = analyze_stem_features("non_existent_file.wav")
        data = json.loads(json_output)
        
        self.assertEqual(data["file_name"], "non_existent_file.wav")
        self.assertEqual(data["duration_seconds"], 0.0)
        self.assertEqual(data["status"], "error")
        self.assertIsNotNone(data["error_message"])
        self.assertIsNone(data["features"])

    def test_stereo_phase_correlation(self):
        # 1. In-phase stereo
        stereo_in_file = "test_stereo_in.wav"
        self.temp_files.append(stereo_in_file)
        y_stereo_in = np.vstack([self.y, self.y]).T
        sf.write(stereo_in_file, y_stereo_in, self.sr)
        
        json_output = analyze_stem_features(stereo_in_file)
        data = json.loads(json_output)
        self.assertEqual(data["status"], "success")
        self.assertAlmostEqual(data["features"]["stereo_correlation_mean"], 1.0, places=4)
        
        # 2. Out-of-phase stereo
        stereo_out_file = "test_stereo_out.wav"
        self.temp_files.append(stereo_out_file)
        y_stereo_out = np.vstack([self.y, -self.y]).T
        sf.write(stereo_out_file, y_stereo_out, self.sr)
        
        json_output = analyze_stem_features(stereo_out_file)
        data = json.loads(json_output)
        self.assertEqual(data["status"], "success")
        self.assertAlmostEqual(data["features"]["stereo_correlation_mean"], -1.0, places=4)

    def test_clash_detection_overlapping(self):
        kick_file = "test_kick.wav"
        bass_file = "test_bass.wav"
        self.temp_files.extend([kick_file, bass_file])
        
        # Overlapping 50Hz (Kick) and 60Hz (Bass) signals
        t = np.linspace(0, self.duration, int(self.sr * self.duration), endpoint=False)
        y_kick = 0.5 * np.sin(2 * np.pi * 50.0 * t)
        y_bass = 0.5 * np.sin(2 * np.pi * 60.0 * t)
        
        sf.write(kick_file, y_kick, self.sr)
        sf.write(bass_file, y_bass, self.sr)
        
        json_output = analyze_stem_clash(kick_file, bass_file)
        data = json.loads(json_output)
        
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["file_name_1"], kick_file)
        self.assertEqual(data["file_name_2"], bass_file)
        self.assertIsNotNone(data["clash_features"])
        
        features = data["clash_features"]
        # Since they are playing simultaneously, envelope correlation should be high
        self.assertGreater(features["overall_cross_correlation"], 0.9)
        # Since they both have low-frequency content in the 20-250 Hz range, low_freq_masking_index should be high
        self.assertGreater(features["low_freq_masking_index"], 0.1)
        self.assertTrue(features["clash_detected"])

    def test_clash_detection_non_overlapping(self):
        kick_file = "test_kick_non_overlap.wav"
        bass_file = "test_bass_non_overlap.wav"
        self.temp_files.extend([kick_file, bass_file])
        
        # Non-overlapping in time:
        # Kick plays in first half (0 to 0.5s), Bass in second half (0.5 to 1.0s)
        t = np.linspace(0, self.duration, int(self.sr * self.duration), endpoint=False)
        half_samples = len(t) // 2
        
        y_kick = np.zeros_like(t)
        y_kick[:half_samples] = 0.5 * np.sin(2 * np.pi * 50.0 * t[:half_samples])
        
        y_bass = np.zeros_like(t)
        y_bass[half_samples:] = 0.5 * np.sin(2 * np.pi * 60.0 * t[half_samples:])
        
        sf.write(kick_file, y_kick, self.sr)
        sf.write(bass_file, y_bass, self.sr)
        
        json_output = analyze_stem_clash(kick_file, bass_file)
        data = json.loads(json_output)
        
        self.assertEqual(data["status"], "success")
        features = data["clash_features"]
        
        # Since they do not play at the same time, envelope correlation should be low
        self.assertLess(features["overall_cross_correlation"], 0.2)
        self.assertFalse(features["clash_detected"])

    def test_clash_error_handling(self):
        # Pass non-existent files
        json_output = analyze_stem_clash("non_existent_1.wav", "non_existent_2.wav")
        data = json.loads(json_output)
        
        self.assertEqual(data["status"], "error")
        self.assertIsNotNone(data["error_message"])
        self.assertIsNone(data["clash_features"])

if __name__ == "__main__":
    unittest.main()
