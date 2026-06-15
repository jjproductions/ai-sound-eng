import os
import json
import numpy as np
import librosa
from pydantic import BaseModel, Field
from typing import Optional

try:
    import pyloudnorm as pyln
    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False

class AudioFeatures(BaseModel):
    lufs_integrated: float = Field(..., description="Integrated perceived loudness in LUFS")
    rms_mean: float = Field(..., description="Mean Root-Mean-Square value of amplitude")
    spectral_centroid_mean_hz: float = Field(..., description="Mean spectral centroid in Hertz")
    peak_amplitude_dbfs: float = Field(..., description="Peak amplitude in dB relative to full scale (dBFS)")
    crest_factor: float = Field(..., description="Crest factor (Peak to RMS ratio)")
    stereo_correlation_mean: Optional[float] = Field(None, description="Mean stereo phase correlation (-1.0 to 1.0), null if mono")

class AnalysisResponse(BaseModel):
    file_name: str = Field(..., description="Name of the analyzed WAV file")
    duration_seconds: float = Field(..., description="Duration of the audio file in seconds")
    features: Optional[AudioFeatures] = Field(None, description="Extracted audio features (null on error)")
    status: str = Field(..., description="Status of the analysis ('success' or 'error')")
    error_message: Optional[str] = Field(None, description="Detailed error message if status is 'error'")

class ClashFeatures(BaseModel):
    overall_cross_correlation: float = Field(..., description="Normalized cross-correlation of envelopes")
    low_freq_masking_index: float = Field(..., description="Frequency masking index in the low band (20-250 Hz)")
    spectral_overlap_index: float = Field(..., description="Overall spectral overlap index (0.0 to 1.0)")
    clash_detected: bool = Field(..., description="True if potential frequency masking clash is detected")

class ClashAnalysisResponse(BaseModel):
    file_name_1: str = Field(..., description="Name of the first audio file (e.g. Kick)")
    file_name_2: str = Field(..., description="Name of the second audio file (e.g. Bass)")
    clash_features: Optional[ClashFeatures] = Field(None, description="Extracted clash features (null on error)")
    status: str = Field(..., description="Status of the analysis ('success' or 'error')")
    error_message: Optional[str] = Field(None, description="Detailed error message if status is 'error'")

def analyze_stem_features(file_path: str) -> str:
    """Loads a .wav file, extracts acoustic features using librosa, 
    and returns a strictly formatted JSON string for the Hermes agent.
    
    Args:
        file_path (str): Absolute path to the source audio file.
        
    Returns:
        str: A validated JSON string matching the output schema.
    """
    file_name = os.path.basename(file_path)
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at: {file_path}")
        
        # Load audio file (mono=False preserves channels for multi-channel analysis)
        y, sr = librosa.load(file_path, sr=None, mono=False)
        
        # Calculate duration
        duration = float(librosa.get_duration(y=y, sr=sr))
        
        # Extract RMS mean
        rms = librosa.feature.rms(y=y)
        rms_mean = float(np.mean(rms))
        
        # Extract Spectral Centroid mean
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        spectral_centroid_mean = float(np.mean(centroid))
        
        # Compute peak amplitude in dBFS
        peak_amp = float(np.max(np.abs(y)))
        if peak_amp > 0:
            peak_dbfs = float(20 * np.log10(peak_amp))
        else:
            peak_dbfs = -100.0
            
        # Compute crest factor
        crest_factor = float(peak_amp / rms_mean) if rms_mean > 1e-10 else 1.0
            
        # Compute stereo correlation
        stereo_corr = None
        if y.ndim > 1 and y.shape[0] >= 2:
            frame_length = 2048
            hop_length = 512
            if y.shape[1] >= frame_length:
                frames_L = librosa.util.frame(y[0], frame_length=frame_length, hop_length=hop_length)
                frames_R = librosa.util.frame(y[1], frame_length=frame_length, hop_length=hop_length)
                
                num = np.sum(frames_L * frames_R, axis=0)
                den = np.sqrt(np.sum(frames_L**2, axis=0) * np.sum(frames_R**2, axis=0))
                
                eps = 1e-10
                valid_mask = den > eps
                if np.any(valid_mask):
                    stereo_corr = float(np.mean(num[valid_mask] / den[valid_mask]))
                else:
                    stereo_corr = 1.0
            else:
                num = np.sum(y[0] * y[1])
                den = np.sqrt(np.sum(y[0]**2) * np.sum(y[1]**2))
                stereo_corr = float(num / den) if den > 1e-10 else 1.0
        else:
            stereo_corr = 1.0
            
        # Compute perceived loudness (LUFS) using pyloudnorm
        lufs_integrated = None
        if HAS_PYLOUDNORM:
            try:
                # pyloudnorm expects sr >= 16000. If not, resample.
                if sr < 16000 or sr > 192000:
                    target_sr = 44100
                    y_loudness = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
                    sr_loudness = target_sr
                else:
                    y_loudness = y
                    sr_loudness = sr
                    
                if y_loudness.ndim > 1:
                    y_loudness = y_loudness.T
                    
                meter = pyln.Meter(sr_loudness)
                lufs_integrated = float(meter.integrated_loudness(y_loudness))
            except Exception:
                pass
                
        if lufs_integrated is None:
            # Fallback approximation: K-weighted RMS to LUFS approximation
            rms_dbfs = 20 * np.log10(rms_mean) if rms_mean > 0 else -100.0
            lufs_integrated = float(rms_dbfs - 0.6)
            
        # Build features model
        features = AudioFeatures(
            lufs_integrated=lufs_integrated,
            rms_mean=rms_mean,
            spectral_centroid_mean_hz=spectral_centroid_mean,
            peak_amplitude_dbfs=peak_dbfs,
            crest_factor=crest_factor,
            stereo_correlation_mean=stereo_corr
        )
        
        # Build response
        response = AnalysisResponse(
            file_name=file_name,
            duration_seconds=duration,
            features=features,
            status="success",
            error_message=None
        )
        
    except Exception as e:
        # Build error response
        response = AnalysisResponse(
            file_name=file_name,
            duration_seconds=0.0,
            features=None,
            status="error",
            error_message=str(e)
        )
        
    return response.model_dump_json()

def analyze_stem_clash(file_path_1: str, file_path_2: str, corr_thresh: float = 0.3, mask_thresh: float = 0.15) -> str:
    """Loads two .wav files, computes cross-correlation and frequency masking
    (especially in low frequencies), and returns a validated JSON string.
    
    Args:
        file_path_1 (str): Absolute path to the first audio file.
        file_path_2 (str): Absolute path to the second audio file.
        corr_thresh (float): Threshold for envelope correlation.
        mask_thresh (float): Threshold for low frequency masking.
        
    Returns:
        str: A validated JSON string matching the clash response schema.
    """
    file_name_1 = os.path.basename(file_path_1)
    file_name_2 = os.path.basename(file_path_2)
    
    try:
        if not os.path.exists(file_path_1):
            raise FileNotFoundError(f"File not found at: {file_path_1}")
        if not os.path.exists(file_path_2):
            raise FileNotFoundError(f"File not found at: {file_path_2}")
            
        # Load audio files as mono at a consistent sample rate for comparison (e.g. 22050 Hz)
        target_sr = 22050
        y1, sr1 = librosa.load(file_path_1, sr=target_sr, mono=True)
        y2, sr2 = librosa.load(file_path_2, sr=target_sr, mono=True)
        
        # Align lengths
        min_len = min(len(y1), len(y2))
        if min_len == 0:
            raise ValueError("One of the audio files is empty.")
        y1 = y1[:min_len]
        y2 = y2[:min_len]
        
        # 1. Envelope Cross-Correlation
        frame_length = 2048
        hop_length = 512
        rms1 = librosa.feature.rms(y=y1, frame_length=frame_length, hop_length=hop_length)[0]
        rms2 = librosa.feature.rms(y=y2, frame_length=frame_length, hop_length=hop_length)[0]
        
        rms1_std = np.std(rms1)
        rms2_std = np.std(rms2)
        if rms1_std > 1e-10 and rms2_std > 1e-10:
            envelope_corr = float(np.corrcoef(rms1, rms2)[0, 1])
        else:
            envelope_corr = 0.0
            
        if np.isnan(envelope_corr):
            envelope_corr = 0.0
            
        # 2. Spectral Overlap & Low-Frequency Masking
        stft1 = np.abs(librosa.stft(y1, n_fft=frame_length, hop_length=hop_length))
        stft2 = np.abs(librosa.stft(y2, n_fft=frame_length, hop_length=hop_length))
        
        max1 = np.max(stft1)
        max2 = np.max(stft2)
        stft1_norm = stft1 / max1 if max1 > 1e-10 else stft1
        stft2_norm = stft2 / max2 if max2 > 1e-10 else stft2
        
        overlap = np.minimum(stft1_norm, stft2_norm)
        spectral_overlap_index = float(np.mean(overlap))
        
        # Low Frequency Masking (20-250 Hz)
        freqs = librosa.fft_frequencies(sr=target_sr, n_fft=frame_length)
        low_indices = np.where((freqs >= 20) & (freqs <= 250))[0]
        
        if len(low_indices) > 0:
            # Sum energy in low frequency band for each frame
            low_energy_1 = np.sum(stft1[low_indices, :], axis=0)
            low_energy_2 = np.sum(stft2[low_indices, :], axis=0)
            
            # Normalize to [0, 1]
            max_low_1 = np.max(low_energy_1)
            max_low_2 = np.max(low_energy_2)
            
            low_energy_1_norm = low_energy_1 / max_low_1 if max_low_1 > 1e-10 else low_energy_1
            low_energy_2_norm = low_energy_2 / max_low_2 if max_low_2 > 1e-10 else low_energy_2
            
            low_masking = np.minimum(low_energy_1_norm, low_energy_2_norm)
            low_freq_masking_index = float(np.mean(low_masking))
        else:
            low_freq_masking_index = 0.0
            
        if np.isnan(spectral_overlap_index):
            spectral_overlap_index = 0.0
        if np.isnan(low_freq_masking_index):
            low_freq_masking_index = 0.0
            
        # 3. Clash Detection Logic
        clash_detected = envelope_corr > corr_thresh and low_freq_masking_index > mask_thresh
        
        clash_features = ClashFeatures(
            overall_cross_correlation=envelope_corr,
            low_freq_masking_index=low_freq_masking_index,
            spectral_overlap_index=spectral_overlap_index,
            clash_detected=bool(clash_detected)
        )
        
        response = ClashAnalysisResponse(
            file_name_1=file_name_1,
            file_name_2=file_name_2,
            clash_features=clash_features,
            status="success",
            error_message=None
        )
        
    except Exception as e:
        response = ClashAnalysisResponse(
            file_name_1=file_name_1,
            file_name_2=file_name_2,
            clash_features=None,
            status="error",
            error_message=str(e)
        )
        
    return response.model_dump_json()
